"""Advanced LLM service for persona extraction using CO-STAR prompt framework"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib
import re

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import boto3
    from botocore.exceptions import ClientError
    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False

from pydantic import BaseModel, Field
import numpy as np

logger = logging.getLogger(__name__)

class PersonaExtractionRequest(BaseModel):
    """Request model for persona extraction"""
    text_content: str = Field(..., description="Input text content for persona extraction")
    persona_count: int = Field(default=3, ge=1, le=10, description="Number of personas to generate")
    domain: Optional[str] = Field(default=None, description="Domain context")
    custom_attributes: Optional[List[str]] = Field(default=None, description="Custom attributes to extract")
    demographic_focus: Optional[List[str]] = Field(default=None, description="Focus areas for demographic extraction")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")

class PersonaExtractionResult(BaseModel):
    """Result of persona extraction from LLM"""
    personas: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    extraction_metadata: Dict[str, Any]
    processing_time: float
    model_used: str
    validation_results: Dict[str, Any]

class LLMPersonaService:
    """Advanced LLM service for persona extraction with multiple provider support"""
    
    def __init__(self, 
                 anthropic_api_key: Optional[str] = None,
                 openai_api_key: Optional[str] = None,
                 aws_region: str = "us-east-1",
                 preferred_provider: str = "anthropic"):
        """
        Initialize LLM service with multiple provider support
        
        Args:
            anthropic_api_key: Anthropic API key
            openai_api_key: OpenAI API key
            aws_region: AWS region for Bedrock
            preferred_provider: Preferred LLM provider (anthropic, openai, bedrock)
        """
        self.preferred_provider = preferred_provider
        self.anthropic_client = None
        self.openai_client = None
        self.bedrock_client = None
        
        # Initialize Anthropic client
        if ANTHROPIC_AVAILABLE and anthropic_api_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
                logger.info("Anthropic client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
        
        # Initialize OpenAI client
        if OPENAI_AVAILABLE and openai_api_key:
            try:
                self.openai_client = openai.OpenAI(api_key=openai_api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Initialize Bedrock client
        if BEDROCK_AVAILABLE:
            try:
                self.bedrock_client = boto3.client('bedrock-runtime', region_name=aws_region)
                logger.info("AWS Bedrock client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock client: {e}")
    
    def _create_costar_prompt(self, 
                             text_content: str, 
                             persona_count: int,
                             domain: Optional[str] = None,
                             custom_attributes: Optional[List[str]] = None,
                             demographic_focus: Optional[List[str]] = None) -> str:
        """
        Create CO-STAR framework prompt for persona extraction
        
        CO-STAR Framework:
        - Context: Background information
        - Objective: Clear goal
        - Style: Communication style
        - Tone: Emotional tone
        - Audience: Target audience
        - Response: Expected format
        """
        
        # Build custom attributes section
        custom_attrs_section = ""
        if custom_attributes:
            custom_attrs_section = f"""
            
Additional Custom Attributes to Extract:
            {', '.join(custom_attributes)}
            """
        
        # Build demographic focus section
        demo_focus_section = ""
        if demographic_focus:
            demo_focus_section = f"""
            
Prioritize these demographic aspects:
            {', '.join(demographic_focus)}
            """
        
        domain_context = f" in the {domain} domain" if domain else ""
        
        prompt = f"""
**CONTEXT:**
You are an expert persona analyst specializing in extracting detailed user personas from text data{domain_context}. You have extensive experience in market research, user experience design, and behavioral psychology.

**OBJECTIVE:**
Analyze the provided text content and extract {persona_count} distinct, realistic personas that represent different user segments found in the data. Each persona should be comprehensive, evidence-based, and actionable for business decisions.

**STYLE:**
Use a systematic, analytical approach. Be precise and data-driven in your extraction. Ensure each persona is distinct and represents a meaningful user segment.

**TONE:**
Professional, objective, and insightful. Focus on actionable insights while maintaining scientific rigor.

**AUDIENCE:**
Business stakeholders, UX designers, and marketing professionals who will use these personas for strategic decision-making.

**RESPONSE FORMAT:**
Provide your response as a valid JSON object with the following structure:

```json
{{
  "personas": [
    {{
      "id": "unique_identifier",
      "name": "Persona Name",
      "demographics": {{
        "age_range": "25-35",
        "gender": "female/male/non-binary/unknown",
        "location": "urban/suburban/rural or specific region",
        "occupation": "job title or category",
        "income_level": "low/medium/high or range",
        "education": "education level",
        "family_status": "single/married/family etc."
      }},
      "psychographics": {{
        "interests": ["interest1", "interest2", "interest3"],
        "values": ["value1", "value2", "value3"],
        "personality_traits": ["trait1", "trait2", "trait3"],
        "lifestyle": ["lifestyle1", "lifestyle2"],
        "motivations": ["motivation1", "motivation2"],
        "pain_points": ["pain1", "pain2"],
        "goals": ["goal1", "goal2"]
      }},
      "behaviors": {{
        "shopping_habits": ["habit1", "habit2"],
        "communication_preferences": ["pref1", "pref2"],
        "decision_factors": ["factor1", "factor2"],
        "media_consumption": ["media1", "media2"],
        "technology_usage": ["tech1", "tech2"],
        "brand_preferences": ["brand_type1", "brand_type2"]
      }},
      "narrative": "A compelling 2-3 sentence description of this persona",
      "confidence_scores": {{
        "demographics": 0.85,
        "psychographics": 0.78,
        "behaviors": 0.82,
        "overall": 0.82
      }},
      "source_evidence": {{
        "supporting_quotes": ["quote1", "quote2"],
        "extraction_reasoning": "Brief explanation of how this persona was derived"
      }}{custom_attrs_section}
    }}
  ],
  "extraction_metadata": {{
    "text_analysis_summary": "Brief summary of key themes found",
    "persona_differentiation": "How personas differ from each other",
    "confidence_rationale": "Explanation of confidence scoring",
    "limitations": "Any limitations or assumptions made"
  }}
}}{demo_focus_section}

**TEXT CONTENT TO ANALYZE:**

{text_content}

**IMPORTANT GUIDELINES:**
1. Base all personas on actual evidence from the text
2. Ensure personas are distinct and non-overlapping
3. Assign realistic confidence scores (0.0-1.0) based on evidence strength
4. Include specific quotes that support each persona attribute
5. If insufficient data exists for certain attributes, mark as "unknown" rather than guessing
6. Focus on actionable insights that can inform business decisions
7. Ensure demographic representation is balanced and unbiased
8. Validate logical consistency between different persona attributes

Provide only the JSON response, no additional text.
        """
        
        return prompt.strip()
    
    async def _call_anthropic(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call Anthropic Claude API"""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")
        
        try:
            response = await asyncio.to_thread(
                self.anthropic_client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise
    
    async def _call_openai(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call OpenAI GPT API"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4-turbo-preview",
                max_tokens=max_tokens,
                temperature=0.3,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert persona analyst. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    async def _call_bedrock(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call AWS Bedrock Claude API with timeout"""
        if not self.bedrock_client:
            raise ValueError("Bedrock client not initialized")
        
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
            
            # Add timeout to prevent hanging
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.bedrock_client.invoke_model,
                    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    body=body
                ),
                timeout=30.0  # 30 second timeout
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
        except asyncio.TimeoutError:
            logger.error("Bedrock API call timed out after 30 seconds")
            raise ValueError("Bedrock API call timed out - check AWS credentials and network connectivity")
        except Exception as e:
            logger.error(f"Bedrock API call failed: {e}")
            raise
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate LLM response"""
        try:
            # Extract JSON from response if it contains additional text
            json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try to find JSON object in the response
                json_match = re.search(r'{.*}', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                else:
                    json_text = response_text
            
            parsed_data = json.loads(json_text)
            
            # Validate required structure
            if 'personas' not in parsed_data:
                raise ValueError("Missing 'personas' key in response")
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            raise
    
    async def extract_personas(self, 
                              text_content: str,
                              persona_count: int = 3,
                              domain: Optional[str] = None,
                              custom_attributes: Optional[List[str]] = None,
                              demographic_focus: Optional[List[str]] = None,
                              confidence_threshold: float = 0.7) -> PersonaExtractionResult:
        """
        Extract personas from text using advanced LLM processing
        
        Args:
            text_content: Input text to analyze
            persona_count: Number of personas to extract
            domain: Domain context for extraction
            custom_attributes: Additional attributes to extract
            demographic_focus: Demographic aspects to prioritize
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            PersonaExtractionResult with extracted personas and metadata
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Create CO-STAR prompt
            prompt = self._create_costar_prompt(
                text_content=text_content,
                persona_count=persona_count,
                domain=domain,
                custom_attributes=custom_attributes,
                demographic_focus=demographic_focus
            )
            
            # Try providers in order of preference
            response_text = None
            model_used = None
            
            providers_to_try = [self.preferred_provider]
            if self.preferred_provider != "anthropic":
                providers_to_try.append("anthropic")
            if self.preferred_provider != "openai":
                providers_to_try.append("openai")
            if self.preferred_provider != "bedrock":
                providers_to_try.append("bedrock")
            
            for provider in providers_to_try:
                try:
                    if provider == "anthropic" and self.anthropic_client:
                        response_text = await self._call_anthropic(prompt)
                        model_used = "claude-3-5-sonnet"
                        break
                    elif provider == "openai" and self.openai_client:
                        response_text = await self._call_openai(prompt)
                        model_used = "gpt-4-turbo"
                        break
                    elif provider == "bedrock" and self.bedrock_client:
                        response_text = await self._call_bedrock(prompt)
                        model_used = "claude-3-5-sonnet-bedrock"
                        break
                except Exception as e:
                    logger.warning(f"Provider {provider} failed: {e}")
                    continue
            
            if not response_text:
                raise ValueError("All LLM providers failed")
            
            # Parse response
            parsed_data = self._parse_llm_response(response_text)
            
            # Filter by confidence threshold
            filtered_personas = []
            for persona in parsed_data.get('personas', []):
                overall_confidence = persona.get('confidence_scores', {}).get('overall', 0.0)
                if overall_confidence >= confidence_threshold:
                    filtered_personas.append(persona)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Calculate aggregate confidence scores
            confidence_scores = {
                'overall': float(np.mean([p.get('confidence_scores', {}).get('overall', 0.0) for p in filtered_personas])) if filtered_personas else 0.0,
            'demographics': float(np.mean([p.get('confidence_scores', {}).get('demographics', 0.0) for p in filtered_personas])) if filtered_personas else 0.0,
            'psychographics': float(np.mean([p.get('confidence_scores', {}).get('psychographics', 0.0) for p in filtered_personas])) if filtered_personas else 0.0,
            'behaviors': float(np.mean([p.get('confidence_scores', {}).get('behaviors', 0.0) for p in filtered_personas])) if filtered_personas else 0.0
            }
            
            return PersonaExtractionResult(
                personas=filtered_personas,
                confidence_scores=confidence_scores,
                extraction_metadata={
                    **parsed_data.get('extraction_metadata', {}),
                    'prompt_length': len(prompt),
                    'response_length': len(response_text),
                    'personas_before_filtering': len(parsed_data.get('personas', [])),
                    'personas_after_filtering': len(filtered_personas),
                    'confidence_threshold_used': confidence_threshold
                },
                processing_time=processing_time,
                model_used=model_used,
                validation_results={
                    'structure_valid': True,
                    'personas_extracted': len(filtered_personas),
                    'confidence_threshold_met': len(filtered_personas) > 0
                }
            )
            
        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Persona extraction failed: {e}")
            
            return PersonaExtractionResult(
                personas=[],
                confidence_scores={'overall': 0.0, 'demographics': 0.0, 'psychographics': 0.0, 'behaviors': 0.0},
                extraction_metadata={'error': str(e)},
                processing_time=processing_time,
                model_used="none",
                validation_results={'structure_valid': False, 'personas_extracted': 0, 'confidence_threshold_met': False}
            )
    
    async def validate_persona(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a persona using LLM-based adversarial questioning"""
        validation_prompt = f"""
        Analyze the following persona for logical consistency, realism, and potential biases:
        
        {json.dumps(persona, indent=2)}
        
        Provide a validation report in JSON format:
        {{
            "consistency_score": 0.85,
            "realism_score": 0.90,
            "bias_indicators": ["potential bias 1", "potential bias 2"],
            "logical_conflicts": ["conflict 1", "conflict 2"],
            "improvement_suggestions": ["suggestion 1", "suggestion 2"],
            "overall_quality": 0.87
        }}
        """
        
        try:
            if self.anthropic_client:
                response = await self._call_anthropic(validation_prompt, max_tokens=1000)
                return self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"Persona validation failed: {e}")
            return {
                "consistency_score": 0.5,
                "realism_score": 0.5,
                "bias_indicators": [],
                "logical_conflicts": [],
                "improvement_suggestions": [],
                "overall_quality": 0.5
            }