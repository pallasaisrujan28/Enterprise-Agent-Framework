import os
import asyncio
import json
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from loguru import logger
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

class PersonaGenerationRequest(BaseModel):
    """Request model for persona generation"""
    demographic_data: Dict[str, Any]
    behavioral_scores: Dict[str, float]
    psychographic_data: Dict[str, Any]
    context: str
    narrative_style: str = "detailed"

class LLMPersonaEngine:
    """AWS Bedrock Claude 3.5 Sonnet integration for persona narrative generation"""
    
    def __init__(self, aws_access_key_id: Optional[str] = None, aws_secret_access_key: Optional[str] = None, aws_session_token: Optional[str] = None, region: Optional[str] = None):
        # Load environment variables explicitly to bypass AWS CLI config
        from dotenv import load_dotenv
        load_dotenv()
        
        # AWS credentials
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_session_token = aws_session_token or os.getenv("AWS_SESSION_TOKEN")
        self.region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise ValueError("AWS credentials are required for Bedrock access")
        
        # Initialize Bedrock client with explicit credentials (bypass AWS CLI config)
        try:
            client_kwargs = {
                'service_name': 'bedrock-runtime',
                'aws_access_key_id': self.aws_access_key_id,
                'aws_secret_access_key': self.aws_secret_access_key,
                'region_name': self.region
            }
            
            # Add session token if available (for temporary credentials)
            if self.aws_session_token:
                client_kwargs['aws_session_token'] = self.aws_session_token
                
            self.bedrock_client = boto3.client(**client_kwargs)
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to initialize AWS Bedrock client: {str(e)}")
            raise ValueError(f"AWS Bedrock initialization failed: {str(e)}")
        
        # Claude Sonnet 4 inference profile ARN for Bedrock
        self.model_id = "arn:aws:bedrock:us-west-2:866647877267:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0"
        
        logger.info(f"Initialized LLM engine with AWS Bedrock model: {self.model_id}")
    
    async def generate_persona_narrative(self, request: PersonaGenerationRequest) -> Dict[str, Any]:
        """Generate rich persona narrative using Claude 3.5 Sonnet via AWS Bedrock"""
        import time
        start_time = time.time()
        
        try:
            # DEBUG: Print LLM engine input data
            # Debug logging removed for production
            
            logger.info(f"🔄 LLM API Call: Starting Bedrock request for persona {request.demographic_data.get('name', 'Unknown')}")
            
            prompt = self._build_persona_prompt(request)
            
            # Prepare the request body for Bedrock
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 13000,  # Increased to 13k tokens for enhanced generation capacity
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            logger.info(f"🔄 LLM API Call: Sending request to Bedrock (prompt length: {len(prompt)} chars)")
            
            # Call Bedrock API with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.bedrock_client.invoke_model,
                    modelId=self.model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json"
                ),
                timeout=30.0  # 30 second timeout
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            narrative_content = response_body['content'][0]['text']
            
            processing_time = time.time() - start_time
            logger.info(f"✅ LLM API Call: Received response from Bedrock (processing time: {processing_time:.2f}s, response length: {len(narrative_content)} chars)")
            
            # Parse the structured response
            persona_data = self._parse_narrative_response(narrative_content)
            
            logger.info(f"✅ LLM Processing: Generated persona narrative for: {request.demographic_data.get('name', 'Unknown')} (total time: {processing_time:.2f}s)")
            
            return {
                "narrative": narrative_content,
                "structured_data": persona_data,
                "model_used": self.model_id,
                "generation_metadata": {
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "prompt_length": len(prompt),
                    "aws_region": self.region,
                    "processing_time_seconds": processing_time
                }
            }
            
        except asyncio.TimeoutError:
            logger.error("Bedrock API call timed out after 30 seconds")
            raise ValueError("Bedrock API call timed out - check AWS credentials and network connectivity")
        except ClientError as e:
            logger.error(f"AWS Bedrock error generating persona narrative: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error generating persona narrative: {str(e)}")
            raise
    
    def _build_persona_prompt(self, request: PersonaGenerationRequest) -> str:
        """Build comprehensive prompt for Claude 3.7 Sonnet with strict constraint enforcement"""
        
        demographic_info = self._format_demographic_data(request.demographic_data)
        behavioral_info = self._format_behavioral_scores(request.behavioral_scores)
        psychographic_info = self._format_psychographic_data(request.psychographic_data)
        
        # Extract critical constraints for emphasis
        critical_constraints = self._extract_critical_constraints(request.demographic_data)
        
        prompt = f"""
You are an expert persona generation specialist. You MUST create a comprehensive, realistic persona that EXACTLY matches the provided constraints.

## MANDATORY DEMOGRAPHIC CONSTRAINTS (NO DEVIATIONS ALLOWED):
{demographic_info}

## BEHAVIORAL ATTRIBUTES:
{behavioral_info}

## PSYCHOGRAPHIC PROFILE:
{psychographic_info}

## CONTEXT:
{request.context}

## CRITICAL CONSTRAINT ENFORCEMENT:
{critical_constraints}

## INSTRUCTIONS:
Generate a detailed, human-like persona that includes:

1. **Personal Background**: Rich backstory, life experiences, formative events
2. **Professional Life**: Work experiences, career progression, industry knowledge
3. **Daily Life**: Typical day, routines, habits, lifestyle patterns
4. **Motivations & Goals**: What drives them, short/long-term aspirations
5. **Pain Points & Challenges**: Current struggles, frustrations, barriers (both personal and professional)
6. **Decision-Making Process**: How they evaluate options, key influences
7. **Communication Style**: Preferred channels, tone, language patterns
8. **Technology Usage**: Digital behavior, platform preferences, adoption patterns
9. **Values & Beliefs**: Core principles, worldview, ethical stance
10. **Social Connections**: Relationships, community involvement, influence networks
11. **Future Outlook**: Hopes, fears, anticipated life changes

**ABSOLUTE REQUIREMENTS - FAILURE TO COMPLY WILL RESULT IN REJECTION:**
- The persona MUST match EVERY demographic constraint exactly as specified
- Age MUST be precisely as stated - no approximations, ranges, or variations
- Location MUST be exactly as specified - no similar cities or regions
- Income MUST fall within the exact range provided - no exceptions
- Education level MUST match exactly - no upgrades or downgrades
- Family status MUST be precisely as specified
- Gender MUST be exactly as stated
- ALL psychographic preferences MUST be reflected in the persona
- ALL behavioral patterns MUST be consistently demonstrated

**VALIDATION CHECKLIST - VERIFY BEFORE FINALIZING:**
✓ Age matches exactly (not approximately)
✓ Location is precisely correct
✓ Income aligns with specified range
✓ Education level is exact match
✓ Family status is correctly represented
✓ Gender is accurately reflected
✓ Psychographic traits are evident throughout
✓ Behavioral patterns are consistent
✓ Professional background aligns with education/income
✓ Lifestyle reflects income and location constraints

**CONSTRAINT VIOLATION PREVENTION:**
- Do NOT use phrases like "around", "approximately", "about", "roughly" when describing demographics
- Do NOT suggest alternative locations or similar areas
- Do NOT adjust income levels for "realism"
- Do NOT modify education levels based on assumptions
- Do NOT change family status for narrative convenience

Ensure the persona is:
- PRECISELY ALIGNED with ALL provided constraints
- Internally consistent and realistic within those constraints
- Rich in specific details that support the exact demographics
- Emotionally authentic while maintaining constraint compliance
- Suitable for {request.narrative_style} business applications

Format your response as a narrative story that brings this person to life, followed by a structured summary that confirms all constraints are met.
"""
        
        return prompt
    
    def _extract_critical_constraints(self, demographic_data: Dict[str, Any]) -> str:
        """Extract and emphasize the most critical constraints that must be followed"""
        constraints = []
        
        # Age constraint
        if 'exact_age' in demographic_data:
            constraints.append(f"🚨 AGE MUST BE EXACTLY {demographic_data['exact_age']} YEARS OLD")
        elif 'age' in demographic_data:
            constraints.append(f"🚨 AGE MUST BE EXACTLY {demographic_data['age']} YEARS OLD")
        elif 'age_range' in demographic_data:
            age_range = demographic_data['age_range']
            if isinstance(age_range, str) and '-' in age_range:
                parts = age_range.split('-')
                if len(parts) == 2 and parts[0] == parts[1]:
                    constraints.append(f"🚨 AGE MUST BE EXACTLY {parts[0]} YEARS OLD")
                else:
                    constraints.append(f"🚨 AGE MUST BE BETWEEN {parts[0]} AND {parts[1]} YEARS OLD")
        
        # Location constraint
        if 'location' in demographic_data:
            location = demographic_data['location']
            if isinstance(location, dict):
                location_str = location.get('full_location', str(location))
            else:
                location_str = str(location)
            constraints.append(f"🚨 LOCATION MUST BE EXACTLY: {location_str}")
        
        # Income constraint
        if 'income_range' in demographic_data:
            constraints.append(f"🚨 INCOME MUST BE WITHIN: {demographic_data['income_range']}")
        
        # Education constraint
        if 'education' in demographic_data:
            constraints.append(f"🚨 EDUCATION MUST BE: {demographic_data['education']}")
        
        # Gender constraint
        if 'gender' in demographic_data:
            constraints.append(f"🚨 GENDER MUST BE: {demographic_data['gender']}")
        
        # Family status constraint
        if 'family_status' in demographic_data:
            constraints.append(f"🚨 FAMILY STATUS MUST BE: {demographic_data['family_status']}")
        
        if not constraints:
            constraints.append("🚨 ALL PROVIDED DEMOGRAPHIC DATA MUST BE EXACTLY MATCHED")
        
        return "\n".join(constraints)
    
    def _format_demographic_data(self, data: Dict[str, Any]) -> str:
        """Format demographic data for prompt with strict constraints"""
        formatted = []
        
        # Handle exact age with strict enforcement
        if 'exact_age' in data:
            formatted.append(f"**MANDATORY AGE**: EXACTLY {data['exact_age']} years old (ZERO TOLERANCE FOR DEVIATION)")
        elif 'age_range' in data:
            # Check if it's a single age disguised as range
            age_range = data['age_range']
            if isinstance(age_range, str) and '-' in age_range:
                parts = age_range.split('-')
                if len(parts) == 2 and parts[0] == parts[1]:
                    formatted.append(f"**MANDATORY AGE**: EXACTLY {parts[0]} years old (ZERO TOLERANCE FOR DEVIATION)")
                else:
                    formatted.append(f"**MANDATORY AGE RANGE**: MUST be between {parts[0]} and {parts[1]} years old (INCLUSIVE)")
            else:
                formatted.append(f"**MANDATORY AGE RANGE**: {age_range} (STRICT COMPLIANCE REQUIRED)")
        elif 'age' in data:
            formatted.append(f"**MANDATORY AGE**: EXACTLY {data['age']} years old (ZERO TOLERANCE FOR DEVIATION)")
            
        if 'gender' in data:
            formatted.append(f"**MANDATORY GENDER**: {data['gender']} (EXACT MATCH REQUIRED)")
            
        if 'location' in data:
            if isinstance(data['location'], dict):
                location_str = data['location'].get('full_location', str(data['location']))
            else:
                location_str = str(data['location'])
            formatted.append(f"**MANDATORY LOCATION**: {location_str} (EXACT LOCATION REQUIRED - NO SUBSTITUTES)")
            
        if 'education' in data:
            formatted.append(f"**MANDATORY EDUCATION**: {data['education']} (EXACT LEVEL REQUIRED)")
            
        if 'income_range' in data:
            formatted.append(f"**MANDATORY INCOME**: {data['income_range']} (MUST FALL WITHIN THIS EXACT RANGE)")
            
        if 'family_status' in data:
            formatted.append(f"**MANDATORY FAMILY STATUS**: {data['family_status']} (EXACT STATUS REQUIRED)")
        
        return "\n".join(formatted)
    
    def _format_behavioral_scores(self, scores: Dict[str, float]) -> str:
        """Format behavioral scores for prompt"""
        formatted = []
        
        for attribute, score in scores.items():
            # Convert 0-100 scale to descriptive terms
            if score >= 80:
                level = "Very High"
            elif score >= 60:
                level = "High"
            elif score >= 40:
                level = "Moderate"
            elif score >= 20:
                level = "Low"
            else:
                level = "Very Low"
            
            formatted.append(f"{attribute.replace('_', ' ').title()}: {level} ({score}/100)")
        
        return "\n".join(formatted)
    
    def _format_psychographic_data(self, data: Dict[str, Any]) -> str:
        """Format psychographic data for prompt with strict adherence requirements"""
        formatted = []
        
        if 'personality_traits' in data:
            traits = ", ".join(data['personality_traits'])
            formatted.append(f"**REQUIRED PERSONALITY TRAITS**: {traits} (MUST be clearly demonstrated in narrative)")
        
        if 'values' in data:
            values = ", ".join(data['values'])
            formatted.append(f"**REQUIRED CORE VALUES**: {values} (MUST drive decisions and behavior)")
        
        if 'interests' in data:
            interests = ", ".join(data['interests'])
            formatted.append(f"**REQUIRED INTERESTS**: {interests} (MUST be actively pursued)")
        
        if 'lifestyle' in data:
            if isinstance(data['lifestyle'], dict):
                lifestyle_items = []
                if 'preferred_activities' in data['lifestyle']:
                    activities = ", ".join(data['lifestyle']['preferred_activities'])
                    lifestyle_items.append(f"Activities: {activities}")
                if 'shopping_style' in data['lifestyle']:
                    lifestyle_items.append(f"Shopping: {data['lifestyle']['shopping_style']}")
                if 'media_consumption' in data['lifestyle']:
                    media = data['lifestyle']['media_consumption']
                    if isinstance(media, dict):
                        media_str = ", ".join([f"{k}: {v}" for k, v in media.items()])
                    else:
                        media_str = str(media)
                    lifestyle_items.append(f"Media: {media_str}")
                if lifestyle_items:
                    formatted.append(f"**REQUIRED LIFESTYLE**: {'; '.join(lifestyle_items)} (MUST be reflected in daily life)")
            elif isinstance(data['lifestyle'], list):
                lifestyle = ", ".join(data['lifestyle'])
                formatted.append(f"**REQUIRED LIFESTYLE**: {lifestyle} (MUST be reflected in daily life)")
        
        if 'media_consumption' in data and 'lifestyle' not in data:
            if isinstance(data['media_consumption'], list):
                media = ", ".join(data['media_consumption'])
            else:
                media = str(data['media_consumption'])
            formatted.append(f"**REQUIRED MEDIA PREFERENCES**: {media} (MUST be actively consumed)")
        
        if 'decision_making_style' in data:
            formatted.append(f"**REQUIRED DECISION MAKING**: {data['decision_making_style']} (MUST be consistently applied)")
        
        return "\n".join(formatted)
    
    def _parse_narrative_response(self, narrative: str) -> Dict[str, Any]:
        """Extract structured data from narrative response"""
        # Basic parsing - can be enhanced with more sophisticated NLP
        return {
            "narrative_length": len(narrative),
            "word_count": len(narrative.split()),
            "has_background": "background" in narrative.lower(),
            "has_goals": "goal" in narrative.lower() or "aspiration" in narrative.lower(),
            "has_pain_points": "challenge" in narrative.lower() or "struggle" in narrative.lower(),
            "emotional_tone": self._analyze_emotional_tone(narrative)
        }
    
    def _analyze_emotional_tone(self, text: str) -> str:
        """Basic emotional tone analysis"""
        positive_words = ["happy", "excited", "optimistic", "confident", "satisfied"]
        negative_words = ["frustrated", "worried", "stressed", "disappointed", "anxious"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    async def generate_batch_personas(self, requests: List[PersonaGenerationRequest]) -> List[Dict[str, Any]]:
        """Generate multiple personas in batch"""
        tasks = [self.generate_persona_narrative(request) for request in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate persona {i}: {str(result)}")
            else:
                successful_results.append(result)
        
        logger.info(f"Generated {len(successful_results)}/{len(requests)} personas successfully")
        return successful_results
    
    async def generate_batch_narratives(self, requests: List[PersonaGenerationRequest]) -> List[str]:
        """Generate multiple persona narratives in batch"""
        tasks = [self.generate_persona_narrative(request) for request in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        narratives = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate narrative {i}: {str(result)}")
                narratives.append("Failed to generate narrative due to an error.")
            else:
                # Extract narrative from the result dictionary
                narrative = result.get('narrative', 'No narrative generated')
                narratives.append(narrative)
        
        logger.info(f"Generated {len(narratives)} narratives")
        return narratives