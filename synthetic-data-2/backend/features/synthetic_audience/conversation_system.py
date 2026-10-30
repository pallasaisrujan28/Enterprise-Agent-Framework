#!/usr/bin/env python3
"""
LangGraph Conversation System
Manages conversation memory and context for persona interactions using LangGraph
"""

import os
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
import json
import boto3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import psycopg2


class ConversationState(TypedDict):
    """State schema for conversation graph"""
    messages: Annotated[List[Dict[str, str]], "Conversation history"]
    persona_uuid: str
    persona_context: Dict[str, Any]
    template_context: Optional[Dict[str, Any]]
    product_context: Optional[str]
    conversation_id: str
    last_updated: str


class LangGraphConversationSystem:
    """
    Manages conversations with personas using LangGraph for state management
    Features:
    - Persistent conversation memory in PostgreSQL
    - Persona-specific context awareness
    - Template-based evaluation context
    - Multi-turn conversation handling
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.bedrock_client = None
        self.graph = None
        self.checkpointer = None
        self._initialize_bedrock()
        self._initialize_graph()

    def _initialize_bedrock(self):
        """Initialize AWS Bedrock client"""
        try:
            self.bedrock_client = boto3.client(
                service_name='bedrock-runtime',
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-west-2'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            print("✅ AWS Bedrock client initialized")
        except Exception as e:
            print(f"⚠️ Bedrock initialization failed: {e}")
            self.bedrock_client = None

    def _initialize_graph(self):
        """Initialize LangGraph with PostgreSQL checkpointer"""
        # Create PostgreSQL checkpointer for conversation persistence
        # Use synchronous connection
        with PostgresSaver.from_conn_string(self.database_url) as checkpointer:
            checkpointer.setup()
            self.checkpointer = checkpointer

        # For now, use in-memory checkpointer as fallback
        # TODO: Implement proper async PostgreSQL checkpointer
        from langgraph.checkpoint.memory import MemorySaver
        self.checkpointer = MemorySaver()

        # Build conversation graph
        workflow = StateGraph(ConversationState)

        # Add nodes
        workflow.add_node("load_context", self._load_persona_context)
        workflow.add_node("generate_response", self._generate_llm_response)
        workflow.add_node("save_state", self._save_conversation_state)

        # Define flow
        workflow.set_entry_point("load_context")
        workflow.add_edge("load_context", "generate_response")
        workflow.add_edge("generate_response", "save_state")
        workflow.add_edge("save_state", END)

        # Compile graph with checkpointer
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        print("✅ LangGraph conversation system initialized (using memory checkpointer)")

    def _load_persona_context(self, state: ConversationState) -> ConversationState:
        """Load persona context from database"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()

            # Get persona details
            cursor.execute("""
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
                WHERE p.persona_uuid = %s
            """, (state['persona_uuid'],))

            result = cursor.fetchone()
            if result:
                state['persona_context'] = {
                    'persona_uuid': str(result[0]),
                    'segment_id': result[1],
                    'campaign_context': result[2],
                    'core_traits': result[3],
                    'demographic_info': result[4],
                    'narrative_profile': result[5],
                    'segment_name': result[6]
                }

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"Error loading persona context: {e}")
            state['persona_context'] = {}

        return state

    def _generate_llm_response(self, state: ConversationState) -> ConversationState:
        """Generate response using AWS Bedrock Claude"""
        if not self.bedrock_client:
            # Fallback response without LLM
            response_text = "I apologize, but I'm unable to generate a detailed response at the moment. Please check the AWS Bedrock configuration."
            state['messages'].append({
                'role': 'assistant',
                'content': response_text
            })
            return state

        try:
            # Build system prompt with persona context
            system_prompt = self._build_system_prompt(state)

            # Get last user message
            last_message = state['messages'][-1]['content']

            # Prepare Claude API request
            model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.7,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": last_message
                    }
                ]
            }

            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            response_text = response_body['content'][0]['text']

            # Add to conversation history
            state['messages'].append({
                'role': 'assistant',
                'content': response_text
            })

        except Exception as e:
            print(f"Error generating LLM response: {e}")
            state['messages'].append({
                'role': 'assistant',
                'content': f"I apologize, but I encountered an error: {str(e)}"
            })

        return state

    def _build_system_prompt(self, state: ConversationState) -> str:
        """Build system prompt with persona and template context"""
        persona_ctx = state['persona_context']

        prompt = f"""You are roleplaying as a realistic synthetic persona with the following profile:

PERSONA PROFILE:
- Segment: {persona_ctx.get('segment_name', 'Unknown')}
- Campaign Context: {persona_ctx.get('campaign_context', 'General')}

NARRATIVE BACKGROUND:
{persona_ctx.get('narrative_profile', 'A typical member of this audience segment.')}

DEMOGRAPHIC TRAITS:
{json.dumps(persona_ctx.get('demographic_info', {}), indent=2)}

BEHAVIORAL TRAITS:
{json.dumps(persona_ctx.get('core_traits', {}), indent=2)}
"""

        # Add template context if available
        if state.get('template_context'):
            template = state['template_context']
            prompt += f"""

EVALUATION TEMPLATE:
You are being asked to evaluate a product based on: {template.get('template_name', 'General Feedback')}

Template Description: {template.get('description', 'Provide honest feedback based on your persona characteristics.')}

Focus Areas:
{json.dumps(template.get('focus_areas', []), indent=2)}
"""

        # Add product context if available
        if state.get('product_context'):
            prompt += f"""

PRODUCT BEING DISCUSSED:
{state['product_context']}
"""

        prompt += """

INSTRUCTIONS:
- Stay completely in character based on your persona profile
- Answer authentically based on your traits, demographics, and behaviors
- Reference your narrative background when relevant
- Be honest about whether this product/service would appeal to you
- Explain your reasoning based on your specific characteristics
- Use natural, conversational language
- If evaluating with a template, address each focus area thoughtfully
"""

        return prompt

    def _save_conversation_state(self, state: ConversationState) -> ConversationState:
        """Update timestamp for state saving"""
        state['last_updated'] = datetime.now().isoformat()
        return state

    async def chat_with_persona(
        self,
        persona_uuid: str,
        user_message: str,
        conversation_id: Optional[str] = None,
        template_context: Optional[Dict[str, Any]] = None,
        product_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle a chat message with a persona using LangGraph state management

        Args:
            persona_uuid: UUID of the persona to chat with
            user_message: User's message
            conversation_id: Optional conversation ID for continuity
            template_context: Optional evaluation template context
            product_context: Optional product description

        Returns:
            Response dictionary with assistant message and conversation state
        """
        if not conversation_id:
            conversation_id = f"conv_{persona_uuid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create or load conversation state
        config = {"configurable": {"thread_id": conversation_id}}

        # Get current state from checkpointer
        try:
            current_state = self.checkpointer.get(config)
            if current_state and 'messages' in current_state:
                messages = current_state['messages']
            else:
                messages = []
        except:
            messages = []

        # Add new user message
        messages.append({
            'role': 'user',
            'content': user_message
        })

        # Prepare initial state
        initial_state = {
            'messages': messages,
            'persona_uuid': persona_uuid,
            'persona_context': {},
            'template_context': template_context,
            'product_context': product_context,
            'conversation_id': conversation_id,
            'last_updated': datetime.now().isoformat()
        }

        # Run graph
        result = await self.graph.ainvoke(initial_state, config)

        # Extract response
        assistant_message = result['messages'][-1]['content']

        return {
            'conversation_id': conversation_id,
            'persona_uuid': persona_uuid,
            'user_message': user_message,
            'assistant_message': assistant_message,
            'full_history': result['messages'],
            'persona_context': result['persona_context'],
            'timestamp': result['last_updated']
        }

    def get_conversation_history(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve conversation history from checkpointer"""
        try:
            config = {"configurable": {"thread_id": conversation_id}}
            state = self.checkpointer.get(config)
            return state
        except Exception as e:
            print(f"Error retrieving conversation history: {e}")
            return None

    def list_persona_conversations(self, persona_uuid: str) -> List[str]:
        """List all conversation IDs for a persona"""
        # This would require custom implementation based on checkpointer
        # For now, return empty list
        return []

    def close(self):
        """Clean up resources"""
        if self.checkpointer:
            # Close checkpointer connection if needed
            pass