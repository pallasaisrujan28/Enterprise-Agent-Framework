#!/usr/bin/env python3
"""
LLM Narrative Generator
Generates realistic persona narratives and handles persona conversations using AWS Bedrock/Claude
"""

import boto3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMNarrativeGenerator:
    """
    Generates realistic persona narratives and enables conversations
    with individual personas using AWS Bedrock Claude
    """

    def __init__(self, region_name: str = None):
        """
        Initialize AWS Bedrock client

        Reads configuration from .env file:
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_DEFAULT_REGION
        - BEDROCK_MODEL_ID
        """
        try:
            # Get region from env or parameter
            if region_name is None:
                region_name = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')

            # Get model ID from env
            self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=region_name,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )

            print(f"✅ AWS Bedrock client initialized")
            print(f"   Model: {self.model_id}")
            print(f"   Region: {region_name}")
        except Exception as e:
            print(f"⚠️  AWS Bedrock initialization error: {e}")
            self.bedrock_client = None
            self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

    # ========================================================================
    # PERSONA NARRATIVE GENERATION
    # ========================================================================

    def generate_persona_narrative(
        self,
        persona_data: Dict[str, Any],
        campaign_context: str
    ) -> str:
        """
        Generate a rich, realistic narrative for a persona

        Args:
            persona_data: Dict with traits, demographics, segment
            campaign_context: The product/campaign this persona is for

        Returns:
            Realistic persona narrative describing the individual
        """

        prompt = self._create_narrative_prompt(persona_data, campaign_context)

        try:
            response = self._call_bedrock(prompt, max_tokens=1500, temperature=0.8)
            return response

        except Exception as e:
            print(f"❌ Error generating narrative: {e}")
            # Fallback: Basic narrative from traits
            return self._create_fallback_narrative(persona_data, campaign_context)

    def _create_narrative_prompt(
        self,
        persona_data: Dict[str, Any],
        campaign_context: str
    ) -> str:
        """Create structured prompt for persona narrative"""

        segment = persona_data.get('segment', 'Individual')
        demographics = persona_data.get('demographics', {})
        behavioral_traits = persona_data.get('behavioral_traits', {})

        # Get TRUE traits (things this persona HAS)
        true_traits = [k for k, v in behavioral_traits.items() if v == True]

        # Format demographics
        demo_str = self._format_demographics(demographics)

        # Format behavioral traits
        traits_str = "\n".join([f"- {trait}" for trait in true_traits[:20]])

        prompt = f"""You are creating a realistic persona profile for marketing research.

Campaign Context: {campaign_context}
Target Segment: {segment}

Demographics:
{demo_str}

Key Behavioral Characteristics (things this person exhibits):
{traits_str}

Based on this data, create a realistic, detailed persona profile that includes:

1. **Name and Basic Info**: Give them a realistic name, age, location
2. **Background**: Brief professional and personal background
3. **Personality & Lifestyle**: Describe their daily life, values, and priorities
4. **Purchasing Behavior**: How they make decisions, what influences them
5. **Relationship to Product**: How they might interact with "{campaign_context}"
6. **Key Motivations**: What drives their choices and behavior

Write in third person, 250-400 words. Make it specific and realistic - this should feel like a real person, not a generic template. Focus on the traits that are TRUE for this person."""

        return prompt

    def _format_demographics(self, demographics: Dict) -> str:
        """Format demographics into readable text"""
        lines = []
        for key, value in demographics.items():
            if value == True:
                lines.append(f"- {key}")
            elif value == False:
                continue  # Skip false demographics
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "- Demographics not specified"

    def _create_fallback_narrative(
        self,
        persona_data: Dict[str, Any],
        campaign_context: str
    ) -> str:
        """Create basic narrative when LLM is unavailable"""

        segment = persona_data.get('segment', 'Individual')
        demographics = persona_data.get('demographics', {})
        behavioral = persona_data.get('behavioral_traits', {})

        # Count key traits
        true_traits = [k for k, v in behavioral.items() if v == True]
        trait_count = len(true_traits)

        # Get gender if available
        gender = "Individual"
        if demographics.get('Female'):
            gender = "woman"
        elif demographics.get('Male'):
            gender = "man"

        narrative = f"""A {gender} from the {segment} segment, interested in {campaign_context}.

This individual exhibits {trait_count} key behavioral characteristics from our research data. Their profile suggests they are representative of their demographic segment with specific purchasing patterns and lifestyle preferences relevant to this campaign.

[Note: Detailed narrative requires AWS Bedrock connection]

Key traits include: {', '.join(true_traits[:10])}..."""

        return narrative

    # ========================================================================
    # BATCH NARRATIVE GENERATION
    # ========================================================================

    def batch_generate_narratives(
        self,
        personas: List[Dict],
        campaign_context: str,
        batch_size: int = 10,
        use_parallel: bool = True
    ) -> List[Dict]:
        """
        Generate narratives for multiple personas in batches

        Args:
            personas: List of persona dicts
            campaign_context: Campaign/product description
            batch_size: Number of personas to process at once
            use_parallel: Use parallel processing (faster, recommended)

        Returns:
            Updated personas with narrative_profile field
        """

        print(f"\n📝 Generating narratives for {len(personas)} personas...")
        print(f"   Batch size: {batch_size}")
        print(f"   Campaign: {campaign_context}")
        print(f"   Mode: {'Parallel' if use_parallel else 'Sequential'}")

        if use_parallel:
            return self._batch_generate_parallel(personas, campaign_context, batch_size)
        else:
            return self._batch_generate_sequential(personas, campaign_context, batch_size)

    def _batch_generate_sequential(
        self,
        personas: List[Dict],
        campaign_context: str,
        batch_size: int
    ) -> List[Dict]:
        """Sequential narrative generation (original method)"""

        updated_personas = []

        for i in range(0, len(personas), batch_size):
            batch = personas[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(personas) + batch_size - 1) // batch_size

            print(f"\n   Processing batch {batch_num}/{total_batches}...")

            for j, persona in enumerate(batch):
                try:
                    narrative = self.generate_persona_narrative(
                        persona_data=persona,
                        campaign_context=campaign_context
                    )

                    persona['narrative_profile'] = narrative
                    updated_personas.append(persona)

                    if (i + j + 1) % 5 == 0:
                        print(f"      Generated {i + j + 1}/{len(personas)} narratives...")

                except Exception as e:
                    print(f"      ⚠️  Error for persona {persona.get('persona_id')}: {e}")
                    persona['narrative_profile'] = self._create_fallback_narrative(
                        persona,
                        campaign_context
                    )
                    updated_personas.append(persona)

        print(f"\n✅ Narrative generation complete: {len(updated_personas)}/{len(personas)} personas")

        return updated_personas

    def _batch_generate_parallel(
        self,
        personas: List[Dict],
        campaign_context: str,
        batch_size: int
    ) -> List[Dict]:
        """Parallel narrative generation using ThreadPoolExecutor"""

        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time

        print(f"   Using {batch_size} parallel threads for faster generation...")

        updated_personas = [None] * len(personas)  # Preserve order
        errors = []

        def generate_single(index, persona):
            """Generate narrative for a single persona"""
            try:
                narrative = self.generate_persona_narrative(
                    persona_data=persona,
                    campaign_context=campaign_context
                )
                persona['narrative_profile'] = narrative
                return index, persona, None
            except Exception as e:
                fallback = self._create_fallback_narrative(persona, campaign_context)
                persona['narrative_profile'] = fallback
                return index, persona, str(e)

        # Generate narratives in parallel
        start_time = time.time()
        completed_count = 0

        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(generate_single, i, persona): i
                for i, persona in enumerate(personas)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                index, persona, error = future.result()
                updated_personas[index] = persona
                completed_count += 1

                if error:
                    errors.append(f"Persona {persona.get('persona_id')}: {error}")

                # Progress update every 10 personas
                if completed_count % 10 == 0 or completed_count == len(personas):
                    elapsed = time.time() - start_time
                    rate = completed_count / elapsed if elapsed > 0 else 0
                    remaining = (len(personas) - completed_count) / rate if rate > 0 else 0
                    print(f"      Generated {completed_count}/{len(personas)} narratives "
                          f"({rate:.1f}/sec, ~{remaining:.0f}s remaining)")

        elapsed = time.time() - start_time
        print(f"\n✅ Narrative generation complete in {elapsed:.1f}s")
        print(f"   Success: {len(personas) - len(errors)}/{len(personas)}")
        if errors:
            print(f"   Errors: {len(errors)} (using fallback narratives)")

        return updated_personas

    # ========================================================================
    # PERSONA CONVERSATION (Chat with individual persona)
    # ========================================================================

    def generate_persona_response(
        self,
        persona_data: Dict[str, Any],
        user_message: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Generate response from persona to user's question

        This makes the persona respond AS THAT SPECIFIC PERSON based on their traits

        Args:
            persona_data: Full persona profile (traits, narrative, etc)
            user_message: What the user is asking
            conversation_history: Previous messages in conversation

        Returns:
            Persona's response as that specific individual
        """

        if conversation_history is None:
            conversation_history = []

        prompt = self._create_conversation_prompt(
            persona_data,
            user_message,
            conversation_history
        )

        try:
            response = self._call_bedrock(
                prompt,
                max_tokens=800,
                temperature=0.7,
                conversation_history=conversation_history
            )
            return response

        except Exception as e:
            print(f"❌ Error generating persona response: {e}")
            return self._create_fallback_response(persona_data, user_message)

    def _create_conversation_prompt(
        self,
        persona_data: Dict[str, Any],
        user_message: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """Create prompt for persona conversation"""

        segment = persona_data.get('segment', 'Individual')
        campaign = persona_data.get('campaign_context', 'product')
        narrative = persona_data.get('narrative', '')
        demographics = persona_data.get('demographics', {})
        behavioral_traits = persona_data.get('behavioral_traits', {})

        # Get TRUE traits
        true_traits = [k for k, v in behavioral_traits.items() if v == True]
        traits_str = ", ".join(true_traits[:15])

        # Build conversation context
        history_str = ""
        if conversation_history:
            history_str = "\n\nPrevious conversation:\n"
            for msg in conversation_history[-6:]:  # Last 3 exchanges
                role = "User" if msg['role'] == 'user' else "You"
                history_str += f"{role}: {msg['content']}\n"

        prompt = f"""You are roleplaying as a specific individual for marketing research purposes.

YOUR IDENTITY:
{narrative if narrative else f"You are a {segment} who is being surveyed about {campaign}."}

YOUR KEY CHARACTERISTICS:
- Segment: {segment}
- Key traits: {traits_str}

IMPORTANT INSTRUCTIONS:
1. Respond AS THIS SPECIFIC PERSON, not as a generic representative
2. Base your opinions and responses on the traits listed above
3. Be realistic - you might not be interested, you might have concerns, you might ask questions
4. Keep responses conversational and natural (100-200 words)
5. Reference your background and traits when relevant
6. Be honest about your perspective - don't just agree with everything
{history_str}

User's current message: {user_message}

Respond as this individual:"""

        return prompt

    def _create_fallback_response(
        self,
        persona_data: Dict[str, Any],
        user_message: str
    ) -> str:
        """Fallback response when LLM unavailable"""

        segment = persona_data.get('segment', 'Individual')
        return f"As a member of {segment}, I appreciate your question about '{user_message[:50]}...'. However, I need more information to provide a detailed response. [LLM connection required for full persona interaction]"

    # ========================================================================
    # AWS BEDROCK INTEGRATION
    # ========================================================================

    def _call_bedrock(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """Call AWS Bedrock Claude API"""

        if not self.bedrock_client:
            raise Exception("AWS Bedrock client not initialized")

        # Build messages array
        messages = []
        if conversation_history:
            messages.extend(conversation_history)

        messages.append({
            "role": "user",
            "content": prompt
        })

        # Call Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }

        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )

        # Parse response
        result = json.loads(response['body'].read())
        return result['content'][0]['text']

    def test_connection(self) -> bool:
        """Test if AWS Bedrock connection works"""
        try:
            test_prompt = "Say 'Hello' in one word."
            response = self._call_bedrock(test_prompt, max_tokens=10)
            print(f"✅ AWS Bedrock connection successful!")
            print(f"   Response: {response}")
            return True
        except Exception as e:
            error_str = str(e)
            print(f"❌ AWS Bedrock connection failed: {error_str}")

            if "AccessDeniedException" in error_str:
                print("\n" + "="*80)
                print("🔧 SETUP REQUIRED: Enable Bedrock Model Access")
                print("="*80)
                print("You need to request access to Claude models in AWS Bedrock:")
                print("\n1. Go to: https://console.aws.amazon.com/bedrock/")
                print("2. Navigate to: Model access (in left sidebar)")
                print("3. Click: 'Manage model access' or 'Enable specific models'")
                print("4. Select: Anthropic Claude 3.5 Haiku (or any Claude model)")
                print("5. Click: 'Request model access' or 'Save changes'")
                print("6. Wait: Usually instant, sometimes takes a few minutes")
                print("\n" + "="*80)
                print("After enabling, run this test again.")
                print("="*80 + "\n")

            return False


# ============================================================================
# EXAMPLE USAGE & TESTING
# ============================================================================

if __name__ == "__main__":
    # Initialize generator
    generator = LLMNarrativeGenerator()

    # Test connection
    print("\n" + "="*80)
    print("TESTING AWS BEDROCK CONNECTION")
    print("="*80)
    generator.test_connection()

    # Test narrative generation
    print("\n" + "="*80)
    print("TESTING NARRATIVE GENERATION")
    print("="*80)

    sample_persona = {
        'segment': 'Healthcare Professionals',
        'campaign_context': 'Premium anti-aging skincare serum',
        'demographics': {
            'Female': True,
            'Senior Management (e.g. Executive VP, Senior VP)': False
        },
        'behavioral_traits': {
            'I tend to buy the premium version of products': True,
            'I look for expert opinions before buying expensive products': True,
            'Price-conscious': False,
            'Healthy ageing': True,
            'Skincare': True
        }
    }

    narrative = generator.generate_persona_narrative(
        persona_data=sample_persona,
        campaign_context=sample_persona['campaign_context']
    )

    print(f"\n📝 Generated Narrative:")
    print("-" * 80)
    print(narrative)
    print("-" * 80)

    # Test conversation
    print("\n" + "="*80)
    print("TESTING PERSONA CONVERSATION")
    print("="*80)

    sample_persona['narrative'] = narrative

    response = generator.generate_persona_response(
        persona_data=sample_persona,
        user_message="Would you be interested in trying our $200 anti-aging serum with retinol and hyaluronic acid?",
        conversation_history=[]
    )

    print(f"\n💬 User: Would you be interested in trying our $200 anti-aging serum with retinol and hyaluronic acid?")
    print(f"\n🎭 Persona Response:")
    print("-" * 80)
    print(response)
    print("-" * 80)