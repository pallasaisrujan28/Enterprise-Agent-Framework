#!/usr/bin/env python3
"""
Phase 3: Persona Generation Pipeline
Implements statistical sampling to create realistic personas matching trait distributions
"""

import psycopg2
import psycopg2.extras
import numpy as np
import json
import uuid
import boto3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from features.synthetic_audience.trait_selector import DynamicScoringLayerV2
from dotenv import load_dotenv

load_dotenv()


class PersonaGenerationPipeline:
    """
    Complete persona generation pipeline:
    1. Select traits using enhanced selector
    2. Output trait JSON for user review
    3. Generate personas matching exact probability distributions
    4. Store personas in database
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.trait_selector = DynamicScoringLayerV2(database_url)
        self.conn = None
        self.cursor = None
        self.accuracy_threshold = 0.95  # 95% accuracy target from developer guide

        # Initialize AWS Bedrock client for archetype generation
        try:
            region_name = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
            self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=region_name,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            print(f"✅ AWS Bedrock client initialized for archetype generation")
        except Exception as e:
            print(f"⚠️  AWS Bedrock initialization warning: {e}")
            self.bedrock_client = None
            self.model_id = None

    def connect_db(self):
        """Connect to database"""
        self.conn = psycopg2.connect(self.database_url)
        self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.trait_selector.connect_db()
        print("✅ Connected to database")

    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        self.trait_selector.close_db()

    # ========================================================================
    # STEP 1: TRAIT SELECTION & JSON OUTPUT
    # ========================================================================

    def select_traits_for_campaign(
        self,
        query: str,
        audience_segment: str,
        max_traits: int = 50
    ) -> Dict[str, Any]:
        """
        Step 1: Select traits and output as JSON for user review

        Returns comprehensive JSON with:
        - Campaign context analysis
        - Selected traits with probabilities
        - Metadata for persona generation
        """

        print(f"\n{'='*80}")
        print(f"STEP 1: TRAIT SELECTION FOR CAMPAIGN")
        print(f"{'='*80}")
        print(f"Query: {query}")
        print(f"Segment: {audience_segment}")
        print(f"Max traits: {max_traits}")

        # Use enhanced trait selector
        selection_result = self.trait_selector.select_traits(
            query=query,
            audience_segment=audience_segment,
            max_traits=max_traits
        )

        if 'error' in selection_result:
            return {
                'success': False,
                'error': selection_result['error']
            }

        # Get trait probabilities for this segment
        trait_data_with_probabilities = self._enrich_traits_with_probabilities(
            selection_result['comprehensive_traits'],
            audience_segment
        )

        # Build comprehensive JSON output
        output_json = {
            'campaign_info': {
                'query': query,
                'target_segment': audience_segment,
                'timestamp': datetime.now().isoformat(),
                'context_analysis': selection_result.get('context', {})
            },
            'selection_summary': {
                'total_traits_selected': len(trait_data_with_probabilities),
                'quality_score': selection_result.get('quality_score', 0.0),
                'avg_semantic_score': selection_result.get('avg_semantic_score', 0.0),
                'avg_category_weight': selection_result.get('avg_category_weight', 0.0)
            },
            'traits': trait_data_with_probabilities,
            'trait_categories_breakdown': self._get_category_breakdown(trait_data_with_probabilities),
            'ready_for_generation': True,
            'generation_params': {
                'segment': audience_segment,
                'query': query,
                'trait_count': len(trait_data_with_probabilities)
            }
        }

        print(f"\n✅ Trait selection complete!")
        print(f"   Selected {len(trait_data_with_probabilities)} traits")
        print(f"   Quality score: {output_json['selection_summary']['quality_score']:.3f}")
        print(f"   Ready for user review")

        return output_json

    def _enrich_traits_with_probabilities(
        self,
        selected_traits: List[Dict],
        audience_segment: str
    ) -> List[Dict]:
        """Add probability values and additional metadata to selected traits"""

        enriched_traits = []

        for trait in selected_traits:
            # Get probability from database
            self.cursor.execute("""
                SELECT
                    t.id as trait_id,
                    t.trait_text,
                    t.section,
                    t.source_sheet,
                    t.trait_type,
                    tc.category_name,
                    tc.priority_level,
                    tp.probability_value,
                    tp.is_demographic
                FROM traits t
                JOIN trait_categories tc ON t.category_id = tc.id
                LEFT JOIN trait_probabilities tp ON tp.trait_id = t.id
                JOIN audience_segments s ON tp.segment_id = s.id
                WHERE t.trait_text = %s
                AND s.segment_name = %s
                LIMIT 1;
            """, (trait['trait_text'], audience_segment))

            result = self.cursor.fetchone()

            if result:
                enriched_trait = {
                    'trait_id': result['trait_id'],
                    'trait_text': result['trait_text'],
                    'trait_name': result['trait_text'],  # Add for frontend compatibility
                    'section': result['section'],  # Add section for full context display
                    'category': result['category_name'],
                    'priority_level': result['priority_level'],
                    'probability': float(result['probability_value']) if result['probability_value'] else 0.5,
                    'is_demographic': result['is_demographic'],
                    'trait_type': result['trait_type'],
                    'source_sheet': result['source_sheet'],
                    'selection_score': trait.get('final_score', 0.0),
                    'relevance_score': trait.get('final_score', 0.0),  # Add for frontend compatibility
                    'semantic_score': trait.get('semantic_score', 0.0),
                    'selected': True  # Add default selected flag for frontend
                }
                enriched_traits.append(enriched_trait)

        return enriched_traits

    def _get_category_breakdown(self, traits: List[Dict]) -> Dict[str, Any]:
        """Get breakdown of traits by category"""

        categories = {}
        for trait in traits:
            cat = trait['category']
            if cat not in categories:
                categories[cat] = {
                    'count': 0,
                    'avg_probability': 0.0,
                    'priority_level': trait['priority_level']
                }
            categories[cat]['count'] += 1
            categories[cat]['avg_probability'] += trait['probability']

        # Calculate averages
        for cat in categories:
            if categories[cat]['count'] > 0:
                categories[cat]['avg_probability'] /= categories[cat]['count']

        return categories

    def save_trait_selection_json(self, output_json: Dict, filename: str = None):
        """Save trait selection JSON to file for user review"""

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            segment = output_json['campaign_info']['target_segment'].replace(' ', '_')
            filename = f"trait_selection_{segment}_{timestamp}.json"

        filepath = f"/Users/Saisrujan/Downloads/Synthetic Data/backend/Synthetic_audience/results/{filename}"

        with open(filepath, 'w') as f:
            json.dump(output_json, f, indent=2)

        print(f"\n💾 Trait selection saved to: {filepath}")
        return filepath

    # ========================================================================
    # STEP 2: STATISTICAL PERSONA GENERATION
    # ========================================================================

    def generate_personas(
        self,
        trait_selection_json: Dict,
        num_personas: int = 100,
        include_narrative: bool = True
    ) -> List[Dict]:
        """
        Step 2: Generate statistically accurate personas

        Uses probability distributions to create personas that match
        the original survey data within 95% accuracy

        Args:
            trait_selection_json: Output from select_traits_for_campaign()
            num_personas: Number of personas to generate
            include_narrative: Whether to generate LLM narratives (slower)

        Returns:
            List of generated personas with traits sampled from distributions
        """

        print(f"\n{'='*80}")
        print(f"STEP 2: GENERATING {num_personas} PERSONAS")
        print(f"{'='*80}")

        traits = trait_selection_json['traits']
        segment = trait_selection_json['campaign_info']['target_segment']
        query = trait_selection_json['campaign_info']['query']

        print(f"Segment: {segment}")
        print(f"Campaign: {query}")
        print(f"Traits to sample: {len(traits)}")

        # STEP 1: Pre-calculate stratified trait assignments with archetype-based correlation
        print(f"\n🎯 Calculating archetype-based trait assignments...")
        trait_assignments_per_persona = self._calculate_stratified_assignments(
            traits=traits,
            num_personas=num_personas,
            segment=segment,
            campaign_query=query
        )

        # STEP 2: Generate personas with assigned traits
        print(f"👥 Generating {num_personas} personas...")
        personas = []
        for i in range(num_personas):
            persona = self._generate_single_persona(
                persona_number=i + 1,
                trait_assignments=trait_assignments_per_persona[i],
                traits=traits,
                segment=segment,
                query=query
            )
            personas.append(persona)

            if (i + 1) % 25 == 0:
                print(f"   Generated {i + 1}/{num_personas} personas...")

        # Validate statistical accuracy
        accuracy = self._validate_statistical_accuracy(personas, traits)

        print(f"\n📊 Generation Complete!")
        print(f"   Personas generated: {len(personas)}")
        print(f"   Statistical accuracy: {accuracy:.3f} ({accuracy*100:.1f}%)")

        if accuracy < self.accuracy_threshold:
            print(f"   ⚠️  Warning: Accuracy {accuracy:.3f} below threshold {self.accuracy_threshold}")
        else:
            print(f"   ✅ Accuracy meets {self.accuracy_threshold} threshold")

        return personas

    def _generate_single_persona(
        self,
        persona_number: int,
        trait_assignments: Dict[str, bool],
        traits: List[Dict],
        segment: str,
        query: str
    ) -> Dict:
        """Generate a single persona using pre-assigned trait values"""

        persona = {
            'persona_id': f'persona_{persona_number:04d}',
            'persona_uuid': str(uuid.uuid4()),
            'segment': segment,
            'campaign_query': query,
            'generation_timestamp': datetime.now().isoformat(),
            'traits': {},
            'demographics': {},
            'behavioral_traits': {}
        }

        # Assign traits from pre-calculated assignments
        for trait in traits:
            trait_text = trait['trait_text']
            category = trait['category']

            # Get assigned value from stratified sampling
            sampled_value = trait_assignments.get(trait_text, False)

            # Store in appropriate section
            persona['traits'][trait_text] = sampled_value

            if category == 'demographics' or trait['is_demographic']:
                persona['demographics'][trait_text] = sampled_value
            else:
                persona['behavioral_traits'][trait_text] = sampled_value

        return persona

    def _call_bedrock(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Call AWS Bedrock Claude API"""
        if not self.bedrock_client:
            raise Exception("AWS Bedrock client not initialized")

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{
                "role": "user",
                "content": prompt
            }]
        }

        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )

        result = json.loads(response['body'].read())
        return result['content'][0]['text']

    def _generate_archetypes(
        self,
        traits: List[Dict],
        segment: str,
        campaign_query: str,
        num_archetypes: int = 8
    ) -> List[Dict]:
        """
        Generate realistic persona archetypes using LLM

        Returns list of archetypes, each with:
        - archetype_name: Descriptive name
        - description: Brief description
        - trait_probabilities: Dict of trait -> probability for this archetype
        - expected_proportion: What % of population fits this archetype
        """

        print(f"\n🎯 Generating {num_archetypes} realistic persona archetypes...")

        # Prepare trait summary for LLM
        trait_summary = []
        for trait in traits[:30]:  # Use top 30 traits to avoid token limits
            trait_summary.append({
                'trait': trait['trait_text'],
                'population_probability': trait['probability'],
                'category': trait.get('category', 'unknown')
            })

        prompt = f"""You are a market research expert analyzing audience segments for a campaign.

Campaign: {campaign_query}
Target Segment: {segment}

Available Traits (from survey data with population probabilities):
{json.dumps(trait_summary, indent=2)}

Task: Generate {num_archetypes} realistic persona archetypes that:
1. Represent diverse types within this segment
2. Have CORRELATED traits (traits that naturally occur together)
3. Account for the population probabilities (high-probability traits should appear in more archetypes)
4. Are mutually exclusive types (each persona fits primarily one archetype)

For each archetype, specify:
- archetype_name: A descriptive name (e.g., "Budget-Conscious Student", "Premium Quality Seeker")
- description: 1-2 sentence description
- key_traits: List of 5-10 trait names that are HIGHLY LIKELY for this archetype
- excluded_traits: List of traits that are UNLIKELY/IMPOSSIBLE for this archetype
- expected_proportion: Estimated % of population (must sum to 1.0 across all archetypes)

Return ONLY a valid JSON array with exactly {num_archetypes} archetype objects, no additional text.

Example format:
[
  {{
    "archetype_name": "Budget-Conscious Student",
    "description": "Price-sensitive students who research extensively before purchases",
    "key_traits": ["Social media updates", "Product reviews", "Budget shopping"],
    "excluded_traits": ["Premium products", "Luxury brands"],
    "expected_proportion": 0.25
  }},
  ...
]"""

        try:
            response = self._call_bedrock(prompt, max_tokens=3000, temperature=0.8)

            # Parse JSON response
            # Sometimes LLM wraps JSON in markdown code blocks
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                response = response.split('```')[1].split('```')[0]

            archetypes = json.loads(response.strip())

            # Normalize proportions to sum to 1.0
            total_prop = sum(a.get('expected_proportion', 1.0/num_archetypes) for a in archetypes)
            for archetype in archetypes:
                if 'expected_proportion' not in archetype:
                    archetype['expected_proportion'] = 1.0 / num_archetypes
                else:
                    archetype['expected_proportion'] = archetype['expected_proportion'] / total_prop

            print(f"✅ Generated {len(archetypes)} archetypes:")
            for i, arch in enumerate(archetypes, 1):
                print(f"   {i}. {arch['archetype_name']} ({arch['expected_proportion']*100:.1f}%)")

            return archetypes

        except Exception as e:
            print(f"❌ Error generating archetypes: {e}")
            print(f"   Response: {response[:500] if 'response' in locals() else 'No response'}")
            raise

    def _calculate_stratified_assignments(
        self,
        traits: List[Dict],
        num_personas: int,
        segment: str = None,
        campaign_query: str = None
    ) -> List[Dict[str, bool]]:
        """
        NEW: Calculate trait assignments using archetype-based approach

        This ensures:
        1. Traits are CORRELATED (realistic combinations)
        2. Population statistics are maintained
        3. Individual personas are realistic

        Returns: List of dicts, one per persona, with trait assignments
        """

        print(f"\n{'='*80}")
        print(f"ARCHETYPE-BASED TRAIT ASSIGNMENT")
        print(f"{'='*80}")

        # Step 1: Generate archetypes using LLM
        try:
            archetypes = self._generate_archetypes(
                traits=traits,
                segment=segment or "General",
                campaign_query=campaign_query or "Product campaign",
                num_archetypes=min(8, max(4, num_personas // 15))  # 4-8 archetypes
            )
        except Exception as e:
            print(f"⚠️  Archetype generation failed, falling back to correlation-aware sampling")
            return self._fallback_correlation_aware_sampling(traits, num_personas)

        # Step 2: Assign personas to archetypes
        print(f"\n👥 Assigning {num_personas} personas to archetypes...")
        archetype_assignments = []
        for archetype in archetypes:
            num_in_archetype = round(archetype['expected_proportion'] * num_personas)
            archetype_assignments.extend([archetype] * num_in_archetype)

        # Adjust for rounding errors
        while len(archetype_assignments) < num_personas:
            archetype_assignments.append(archetypes[0])
        while len(archetype_assignments) > num_personas:
            archetype_assignments.pop()

        # Shuffle to randomize order
        np.random.shuffle(archetype_assignments)

        print(f"   Archetype distribution:")
        for arch in archetypes:
            count = sum(1 for a in archetype_assignments if a['archetype_name'] == arch['archetype_name'])
            print(f"   - {arch['archetype_name']}: {count} personas ({count/num_personas*100:.1f}%)")

        # Step 3: Assign traits to each persona based on their archetype
        print(f"\n🎲 Assigning traits to personas based on archetypes...")
        persona_assignments = []

        for persona_idx, assigned_archetype in enumerate(archetype_assignments):
            persona_traits = {}

            key_traits = assigned_archetype.get('key_traits', [])
            excluded_traits = assigned_archetype.get('excluded_traits', [])

            for trait in traits:
                trait_text = trait['trait_text']
                base_prob = trait['probability']

                # Adjust probability based on archetype
                if trait_text in key_traits:
                    # High probability for key traits (80-95%)
                    adjusted_prob = min(0.95, base_prob + 0.5)
                elif trait_text in excluded_traits:
                    # Very low probability for excluded traits (0-10%)
                    adjusted_prob = max(0.0, base_prob - 0.7)
                else:
                    # Normal probability with slight variation
                    adjusted_prob = base_prob * np.random.uniform(0.7, 1.3)
                    adjusted_prob = max(0.0, min(1.0, adjusted_prob))

                # Sample trait value
                persona_traits[trait_text] = np.random.random() < adjusted_prob

            persona_assignments.append(persona_traits)

        # Step 4: Validate and adjust to match population statistics
        print(f"\n📊 Validating population statistics...")
        persona_assignments = self._adjust_for_statistical_accuracy(
            persona_assignments, traits, num_personas
        )

        return persona_assignments

    def _fallback_correlation_aware_sampling(
        self,
        traits: List[Dict],
        num_personas: int
    ) -> List[Dict[str, bool]]:
        """
        Fallback: Use correlation-aware sampling without archetypes

        This is better than pure random but doesn't require LLM
        """
        print(f"   Using correlation-aware fallback method...")

        persona_assignments = [{} for _ in range(num_personas)]
        persona_indices = list(range(num_personas))

        # Group traits by category for better correlation
        traits_by_category = {}
        for trait in traits:
            category = trait.get('category', 'other')
            if category not in traits_by_category:
                traits_by_category[category] = []
            traits_by_category[category].append(trait)

        # Assign traits category by category (provides some correlation within categories)
        for category, category_traits in traits_by_category.items():
            for trait in category_traits:
                trait_text = trait['trait_text']
                probability = trait['probability']

                num_with_trait = round(probability * num_personas)
                np.random.shuffle(persona_indices)
                personas_with_trait = persona_indices[:num_with_trait]

                for persona_idx in range(num_personas):
                    persona_assignments[persona_idx][trait_text] = persona_idx in personas_with_trait

        return persona_assignments

    def _adjust_for_statistical_accuracy(
        self,
        persona_assignments: List[Dict[str, bool]],
        traits: List[Dict],
        num_personas: int
    ) -> List[Dict[str, bool]]:
        """
        Adjust trait assignments to match target population statistics exactly

        This is done by flipping minimal number of assignments
        """

        for trait in traits:
            trait_text = trait['trait_text']
            target_prob = trait['probability']
            target_count = round(target_prob * num_personas)

            # Count current assignments
            current_count = sum(1 for p in persona_assignments if p.get(trait_text, False))

            diff = target_count - current_count

            if diff > 0:
                # Need to set more to True
                false_indices = [i for i, p in enumerate(persona_assignments) if not p.get(trait_text, False)]
                np.random.shuffle(false_indices)
                for idx in false_indices[:diff]:
                    persona_assignments[idx][trait_text] = True

            elif diff < 0:
                # Need to set more to False
                true_indices = [i for i, p in enumerate(persona_assignments) if p.get(trait_text, False)]
                np.random.shuffle(true_indices)
                for idx in true_indices[:abs(diff)]:
                    persona_assignments[idx][trait_text] = False

        return persona_assignments

    def _validate_statistical_accuracy(
        self,
        personas: List[Dict],
        expected_traits: List[Dict]
    ) -> float:
        """
        Validate that generated personas match expected distributions

        With stratified sampling, this should return ~1.0 (perfect accuracy)
        """

        trait_accuracies = []
        mismatches = []

        for trait_data in expected_traits:
            trait_text = trait_data['trait_text']
            expected_prob = trait_data['probability']

            # Count how many personas have this trait = True
            trait_count = sum(
                1 for p in personas
                if p['traits'].get(trait_text, False) == True
            )

            generated_prob = trait_count / len(personas) if len(personas) > 0 else 0

            # Calculate accuracy
            accuracy = 1.0 - abs(generated_prob - expected_prob)
            trait_accuracies.append(accuracy)

            # Track any mismatches for debugging
            if accuracy < 0.99:  # Allow for tiny rounding errors
                mismatches.append({
                    'trait': trait_text,
                    'expected': expected_prob,
                    'generated': generated_prob,
                    'accuracy': accuracy
                })

        avg_accuracy = np.mean(trait_accuracies)

        # Report any significant mismatches
        if mismatches and avg_accuracy < 0.95:
            print(f"\n⚠️  Distribution mismatches detected:")
            for m in mismatches[:5]:  # Show first 5
                print(f"   {m['trait'][:50]:50s} | Expected: {m['expected']:.3f} | Got: {m['generated']:.3f}")

        return avg_accuracy

    # ========================================================================
    # STEP 3: PERSONA STORAGE
    # ========================================================================

    def store_personas(
        self,
        personas: List[Dict],
        trait_selection_json: Dict
    ) -> List[str]:
        """
        Step 3: Store generated personas in database

        Returns list of persona UUIDs
        """

        print(f"\n{'='*80}")
        print(f"STEP 3: STORING PERSONAS IN DATABASE")
        print(f"{'='*80}")

        stored_uuids = []

        # Get segment ID
        segment_name = trait_selection_json['campaign_info']['target_segment']
        self.cursor.execute(
            "SELECT id FROM audience_segments WHERE segment_name = %s",
            (segment_name,)
        )
        segment_result = self.cursor.fetchone()

        if not segment_result:
            print(f"❌ Error: Segment '{segment_name}' not found in database")
            return []

        segment_id = segment_result['id']
        campaign_context = trait_selection_json['campaign_info']['query']

        # Store each persona
        for i, persona in enumerate(personas):
            try:
                self.cursor.execute("""
                    INSERT INTO personas (
                        persona_uuid,
                        segment_id,
                        campaign_context,
                        core_traits,
                        extended_traits,
                        demographic_info,
                        narrative_profile,
                        generation_metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING persona_uuid
                """, (
                    persona['persona_uuid'],
                    segment_id,
                    campaign_context,
                    json.dumps(persona['behavioral_traits']),
                    json.dumps(persona['traits']),  # All traits for follow-up
                    json.dumps(persona['demographics']),
                    persona.get('narrative_profile', None),  # Store narrative if present
                    json.dumps({
                        'persona_id': persona['persona_id'],
                        'generation_timestamp': persona['generation_timestamp'],
                        'campaign_query': persona['campaign_query'],
                        'trait_count': len(persona['traits']),
                        'selection_summary': trait_selection_json['selection_summary']
                    })
                ))

                result = self.cursor.fetchone()
                stored_uuids.append(result['persona_uuid'])

                if (i + 1) % 25 == 0:
                    print(f"   Stored {i + 1}/{len(personas)} personas...")

            except Exception as e:
                print(f"   ⚠️  Error storing persona {persona['persona_id']}: {e}")
                continue

        self.conn.commit()

        print(f"\n✅ Storage complete!")
        print(f"   Personas stored: {len(stored_uuids)}")
        print(f"   Success rate: {len(stored_uuids)/len(personas)*100:.1f}%")

        return stored_uuids

    # ========================================================================
    # COMPLETE END-TO-END PIPELINE
    # ========================================================================

    def run_complete_pipeline(
        self,
        query: str,
        audience_segment: str,
        num_personas: int = 100,
        max_traits: int = 50,
        save_json: bool = True,
        include_narratives: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete persona generation pipeline:
        1. Select traits and output JSON
        2. Generate personas matching distributions
        3. Generate LLM narratives (if enabled)
        4. Store in database

        Returns:
            Complete results including trait selection, personas, and UUIDs
        """

        print(f"\n{'#'*80}")
        print(f"# PERSONA GENERATION PIPELINE - COMPLETE WORKFLOW")
        print(f"{'#'*80}")
        print(f"Campaign: {query}")
        print(f"Segment: {audience_segment}")
        print(f"Personas to generate: {num_personas}")
        print(f"{'#'*80}\n")

        try:
            # Step 1: Trait Selection
            trait_selection = self.select_traits_for_campaign(
                query=query,
                audience_segment=audience_segment,
                max_traits=max_traits
            )

            if not trait_selection.get('ready_for_generation'):
                return {
                    'success': False,
                    'error': 'Trait selection failed',
                    'trait_selection': trait_selection
                }

            # Optionally save JSON for user review
            json_path = None
            if save_json:
                json_path = self.save_trait_selection_json(trait_selection)

            # Step 2: Generate Personas (statistical sampling)
            personas = self.generate_personas(
                trait_selection_json=trait_selection,
                num_personas=num_personas,
                include_narrative=False  # Narratives added separately
            )

            # Step 2.5: Generate LLM Narratives (if requested)
            if include_narratives:
                from llm_narrative_generator import LLMNarrativeGenerator
                llm_gen = LLMNarrativeGenerator()
                personas = llm_gen.batch_generate_narratives(
                    personas=personas,
                    campaign_context=query,
                    batch_size=20,
                    use_parallel=True
                )

            # Step 3: Store Personas
            stored_uuids = self.store_personas(
                personas=personas,
                trait_selection_json=trait_selection
            )

            # Return complete results
            result = {
                'success': True,
                'trait_selection': trait_selection,
                'trait_selection_json_path': json_path,
                'personas_generated': len(personas),
                'personas_stored': len(stored_uuids),
                'persona_uuids': stored_uuids,
                'personas': personas,  # Full persona data
                'pipeline_summary': {
                    'query': query,
                    'segment': audience_segment,
                    'traits_selected': len(trait_selection['traits']),
                    'personas_generated': len(personas),
                    'personas_stored': len(stored_uuids),
                    'quality_score': trait_selection['selection_summary']['quality_score'],
                    'completion_timestamp': datetime.now().isoformat()
                }
            }

            print(f"\n{'#'*80}")
            print(f"# PIPELINE COMPLETE - SUCCESS!")
            print(f"{'#'*80}")
            print(f"✅ Traits selected: {result['pipeline_summary']['traits_selected']}")
            print(f"✅ Personas generated: {result['pipeline_summary']['personas_generated']}")
            print(f"✅ Personas stored: {result['pipeline_summary']['personas_stored']}")
            print(f"✅ Quality score: {result['pipeline_summary']['quality_score']:.3f}")
            if json_path:
                print(f"📄 Trait JSON: {json_path}")
            print(f"{'#'*80}\n")

            return result

        except Exception as e:
            print(f"\n❌ Pipeline error: {e}")
            import traceback
            traceback.print_exc()

            return {
                'success': False,
                'error': str(e)
            }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_trait_selection_from_json(json_path: str) -> Dict:
    """Load trait selection JSON from file"""
    with open(json_path, 'r') as f:
        return json.load(f)


def export_personas_to_json(personas: List[Dict], output_path: str):
    """Export generated personas to JSON file"""
    with open(output_path, 'w') as f:
        json.dump(personas, f, indent=2)
    print(f"📄 Personas exported to: {output_path}")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/synthetic_personas"

    # Initialize pipeline
    pipeline = PersonaGenerationPipeline(DATABASE_URL)
    pipeline.connect_db()

    try:
        # Example: Run complete pipeline
        result = pipeline.run_complete_pipeline(
            query="Premium skincare products for anti-aging",
            audience_segment="Healthcare Professionals",
            num_personas=100,
            max_traits=40,
            save_json=True
        )

        if result['success']:
            print("\n" + "="*80)
            print("PIPELINE RESULTS")
            print("="*80)
            print(f"Personas generated: {result['personas_generated']}")
            print(f"Personas stored: {result['personas_stored']}")
            print(f"\nFirst 3 persona UUIDs:")
            for i, uuid_str in enumerate(result['persona_uuids'][:3], 1):
                print(f"  {i}. {uuid_str}")

            # Example: Show first persona
            if result['personas']:
                print(f"\n{'='*80}")
                print("SAMPLE PERSONA")
                print("="*80)
                first_persona = result['personas'][0]
                print(f"ID: {first_persona['persona_id']}")
                print(f"UUID: {first_persona['persona_uuid']}")
                print(f"Segment: {first_persona['segment']}")
                print(f"\nDemographics:")
                for trait, value in list(first_persona['demographics'].items())[:5]:
                    print(f"  {trait}: {value}")
                print(f"\nBehavioral Traits (sample):")
                for trait, value in list(first_persona['behavioral_traits'].items())[:5]:
                    print(f"  {trait}: {value}")

    finally:
        pipeline.close_db()