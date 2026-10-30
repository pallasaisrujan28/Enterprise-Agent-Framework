#!/usr/bin/env python3
"""
Audience Template Evaluation System
Provides collective feedback from entire audience segments based on evaluation templates
"""

import os
import json
import boto3
import psycopg2
import psycopg2.extras
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np


class AudienceTemplateEvaluator:
    """
    Evaluates products/campaigns using audience segments with custom templates
    Features:
    - Template-based evaluation (ROI, user experience, brand fit, etc.)
    - Collective audience feedback aggregation
    - Individual persona-level insights
    - Statistical analysis of responses
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.bedrock_client = None
        self.conn = None
        self.cursor = None
        self._initialize_bedrock()

    def _initialize_bedrock(self):
        """Initialize AWS Bedrock client"""
        try:
            self.bedrock_client = boto3.client(
                service_name='bedrock-runtime',
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-west-2'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            print("✅ AWS Bedrock client initialized for audience evaluation")
        except Exception as e:
            print(f"⚠️ Bedrock initialization failed: {e}")
            self.bedrock_client = None

    def connect_db(self):
        """Connect to database"""
        self.conn = psycopg2.connect(self.database_url)
        self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def get_evaluation_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get predefined evaluation templates"""
        return {
            'roi_analysis': {
                'name': 'Return on Investment Analysis',
                'description': 'Evaluate whether this product/service provides good value for money',
                'focus_areas': [
                    'Perceived value vs. cost',
                    'Long-term benefits',
                    'Comparison to alternatives',
                    'Budget fit',
                    'Expected ROI timeframe'
                ],
                'rating_scale': '1-10'
            },
            'user_experience': {
                'name': 'User Experience Evaluation',
                'description': 'Assess usability, convenience, and overall experience',
                'focus_areas': [
                    'Ease of use',
                    'Learning curve',
                    'Integration with daily routine',
                    'Time investment required',
                    'Satisfaction prediction'
                ],
                'rating_scale': '1-10'
            },
            'brand_alignment': {
                'name': 'Brand & Values Alignment',
                'description': 'Evaluate fit with personal values and lifestyle',
                'focus_areas': [
                    'Brand reputation perception',
                    'Values alignment',
                    'Social responsibility',
                    'Cultural fit',
                    'Community perception'
                ],
                'rating_scale': '1-10'
            },
            'purchase_intent': {
                'name': 'Purchase Intent Assessment',
                'description': 'Likelihood to purchase and motivating/deterring factors',
                'focus_areas': [
                    'Purchase likelihood (0-100%)',
                    'Key motivating factors',
                    'Major concerns/barriers',
                    'Timeline to purchase',
                    'Recommended improvements'
                ],
                'rating_scale': '0-100%'
            },
            'feature_importance': {
                'name': 'Feature Prioritization',
                'description': 'Rank features by importance and satisfaction',
                'focus_areas': [
                    'Most important features',
                    'Nice-to-have features',
                    'Unnecessary features',
                    'Missing features',
                    'Feature satisfaction ratings'
                ],
                'rating_scale': '1-10'
            },
            'competitive_analysis': {
                'name': 'Competitive Positioning',
                'description': 'Compare to alternatives in the market',
                'focus_areas': [
                    'Known competitors',
                    'Competitive advantages',
                    'Competitive disadvantages',
                    'Switching barriers',
                    'Differentiation strength'
                ],
                'rating_scale': '1-10'
            }
        }

    def evaluate_product_with_template(
        self,
        product_description: str,
        audience_segment: str,
        template_key: str,
        num_personas: int = 10,
        existing_generation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a product using a specific template with audience personas

        Args:
            product_description: Description of product/service
            audience_segment: Target audience segment name
            template_key: Template key from get_evaluation_templates()
            num_personas: Number of personas to evaluate with
            existing_generation_id: Use existing personas (optional)

        Returns:
            Comprehensive evaluation results with collective and individual feedback
        """
        print(f"\n{'='*80}")
        print(f"AUDIENCE TEMPLATE EVALUATION")
        print(f"{'='*80}")
        print(f"Product: {product_description}")
        print(f"Segment: {audience_segment}")
        print(f"Template: {template_key}")
        print(f"Personas: {num_personas}")

        # Get template
        templates = self.get_evaluation_templates()
        if template_key not in templates:
            return {'error': f'Template {template_key} not found'}

        template = templates[template_key]

        # Get personas for this segment
        personas = self._get_personas_for_segment(
            audience_segment,
            num_personas,
            existing_generation_id
        )

        if not personas:
            return {'error': 'No personas found for segment'}

        # Evaluate with each persona in parallel
        individual_evaluations = []
        if self.bedrock_client:
            individual_evaluations = self._parallel_persona_evaluations(
                personas,
                product_description,
                template
            )
        else:
            individual_evaluations = self._fallback_evaluations(personas, template)

        # Aggregate collective feedback
        collective_feedback = self._aggregate_collective_feedback(
            individual_evaluations,
            template
        )

        # Build comprehensive response
        result = {
            'evaluation_metadata': {
                'product_description': product_description,
                'audience_segment': audience_segment,
                'template_used': template['name'],
                'template_key': template_key,
                'num_personas_evaluated': len(individual_evaluations),
                'timestamp': datetime.now().isoformat()
            },
            'template_details': template,
            'collective_feedback': collective_feedback,
            'individual_evaluations': individual_evaluations,
            'statistical_summary': self._calculate_statistics(individual_evaluations),
            'key_insights': self._extract_key_insights(
                collective_feedback,
                individual_evaluations
            )
        }

        return result

    def _get_personas_for_segment(
        self,
        segment_name: str,
        num_personas: int,
        generation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve personas for the segment"""
        try:
            if generation_id:
                # Get personas from specific generation
                self.cursor.execute("""
                    SELECT
                        p.persona_uuid,
                        p.segment_id,
                        p.campaign_context,
                        p.core_traits,
                        p.demographic_info,
                        p.narrative_profile,
                        a.segment_name
                    FROM personas p
                    JOIN audience_segments a ON p.segment_id = a.id
                    WHERE p.generation_id = %s
                    LIMIT %s
                """, (generation_id, num_personas))
            else:
                # Get personas from segment
                self.cursor.execute("""
                    SELECT
                        p.persona_uuid,
                        p.segment_id,
                        p.campaign_context,
                        p.core_traits,
                        p.demographic_info,
                        p.narrative_profile,
                        a.segment_name
                    FROM personas p
                    JOIN audience_segments a ON p.segment_id = a.id
                    WHERE a.segment_name = %s
                    ORDER BY p.generation_timestamp DESC
                    LIMIT %s
                """, (segment_name, num_personas))

            results = self.cursor.fetchall()
            return [dict(row) for row in results]

        except Exception as e:
            print(f"Error getting personas: {e}")
            return []

    def _parallel_persona_evaluations(
        self,
        personas: List[Dict[str, Any]],
        product: str,
        template: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Evaluate product with multiple personas in parallel"""
        evaluations = []

        # Use ThreadPoolExecutor for parallel LLM calls
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    self._evaluate_single_persona,
                    persona,
                    product,
                    template
                ): persona for persona in personas
            }

            for future in as_completed(futures):
                try:
                    evaluation = future.result()
                    evaluations.append(evaluation)
                except Exception as e:
                    print(f"Error in persona evaluation: {e}")

        return evaluations

    def _evaluate_single_persona(
        self,
        persona: Dict[str, Any],
        product: str,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate product with a single persona using LLM"""
        try:
            # Build evaluation prompt
            system_prompt = f"""You are roleplaying as a realistic persona evaluating a product.

PERSONA PROFILE:
Segment: {persona['segment_name']}
Background: {persona.get('narrative_profile', 'A typical member of this segment')}

Demographics: {json.dumps(persona.get('demographic_info', {}), indent=2)}
Behavioral Traits: {json.dumps(persona.get('core_traits', {}), indent=2)}

EVALUATION TEMPLATE: {template['name']}
{template['description']}

Focus Areas to Address:
{chr(10).join(f"- {area}" for area in template['focus_areas'])}

PRODUCT TO EVALUATE:
{product}

Provide a detailed evaluation addressing each focus area. Rate overall on scale: {template['rating_scale']}
Be authentic to your persona characteristics. Provide specific reasoning based on your profile."""

            # Call Bedrock
            model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.7,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Please evaluate this product thoroughly based on the template."
                    }
                ]
            }

            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())
            evaluation_text = response_body['content'][0]['text']

            return {
                'persona_uuid': str(persona['persona_uuid']),
                'segment': persona['segment_name'],
                'evaluation': evaluation_text,
                'persona_summary': {
                    'demographics': persona.get('demographic_info', {}),
                    'key_traits': list(persona.get('core_traits', {}).keys())[:5]
                }
            }

        except Exception as e:
            print(f"Error evaluating persona {persona['persona_uuid']}: {e}")
            return {
                'persona_uuid': str(persona['persona_uuid']),
                'segment': persona['segment_name'],
                'evaluation': f"Error: {str(e)}",
                'error': True
            }

    def _fallback_evaluations(
        self,
        personas: List[Dict[str, Any]],
        template: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fallback evaluations without LLM"""
        return [{
            'persona_uuid': str(p['persona_uuid']),
            'segment': p['segment_name'],
            'evaluation': f"Evaluation requires AWS Bedrock access. Persona traits available for analysis.",
            'persona_summary': {
                'demographics': p.get('demographic_info', {}),
                'key_traits': list(p.get('core_traits', {}).keys())[:5]
            },
            'fallback': True
        } for p in personas]

    def _aggregate_collective_feedback(
        self,
        evaluations: List[Dict[str, Any]],
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate individual evaluations into collective feedback"""
        if not self.bedrock_client:
            return {
                'summary': 'Collective aggregation requires AWS Bedrock access',
                'num_evaluations': len(evaluations)
            }

        try:
            # Combine all evaluations
            combined_evaluations = "\n\n".join([
                f"Persona {i+1} ({e['segment']}):\n{e['evaluation']}"
                for i, e in enumerate(evaluations) if not e.get('error')
            ])

            # Aggregate with LLM
            aggregate_prompt = f"""You are analyzing feedback from {len(evaluations)} personas in an audience segment.

EVALUATION TEMPLATE: {template['name']}
Focus Areas: {', '.join(template['focus_areas'])}

INDIVIDUAL EVALUATIONS:
{combined_evaluations}

Provide a comprehensive COLLECTIVE SUMMARY that:
1. Identifies common themes and patterns
2. Highlights areas of consensus
3. Notes significant disagreements or variations
4. Provides overall audience sentiment
5. Lists key takeaways for product improvement

Format as a clear, actionable summary."""

            model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 3000,
                "temperature": 0.5,
                "messages": [
                    {
                        "role": "user",
                        "content": aggregate_prompt
                    }
                ]
            }

            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())
            collective_summary = response_body['content'][0]['text']

            return {
                'summary': collective_summary,
                'num_evaluations': len(evaluations),
                'consensus_level': 'high'  # Could be calculated from evaluations
            }

        except Exception as e:
            print(f"Error aggregating feedback: {e}")
            return {
                'summary': f"Error aggregating: {str(e)}",
                'num_evaluations': len(evaluations)
            }

    def _calculate_statistics(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistical summary of evaluations"""
        return {
            'total_evaluations': len(evaluations),
            'successful_evaluations': len([e for e in evaluations if not e.get('error')]),
            'failed_evaluations': len([e for e in evaluations if e.get('error')]),
            'segments_represented': list(set([e['segment'] for e in evaluations]))
        }

    def _extract_key_insights(
        self,
        collective: Dict[str, Any],
        individual: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract key insights from evaluation"""
        insights = [
            f"Evaluated by {len(individual)} personas",
            f"Segment: {individual[0]['segment'] if individual else 'Unknown'}"
        ]

        if not any(e.get('error') for e in individual):
            insights.append("All persona evaluations completed successfully")

        return insights