#!/usr/bin/env python3
"""
Synthetic Audience Platform - FastAPI Endpoints
Complete API for frontend integration

Flow:
1. User specifies: segment, campaign query, number of personas
2. API returns: Selected traits as JSON for review
3. User can: Edit/remove traits
4. API generates: Individual realistic personas using LLM
5. API stores: Personas in database
6. User can: Chat with individual personas about the product
"""

from fastapi import FastAPI, HTTPException, Body, File, UploadFile, Form, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import sys
import os
import base64

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.synthetic_audience.persona_generator import PersonaGenerationPipeline
from features.synthetic_audience.narrative_generator import LLMNarrativeGenerator
from features.synthetic_audience.template_evaluator import AudienceTemplateEvaluator
from features.synthetic_audience.conversation_system import LangGraphConversationSystem
import json
from datetime import datetime
import uuid
import asyncio
from typing import TypedDict
from dataclasses import dataclass, field

# ============================================================================
# PYDANTIC MODELS (Request/Response schemas for frontend)
# ============================================================================

class TraitSelectionRequest(BaseModel):
    """Step 1: User specifies campaign parameters"""
    campaign_query: str = Field(..., description="Product/campaign description", example="Premium anti-aging skincare serum")
    audience_segment: str = Field(..., description="Target audience segment", example="Healthcare Professionals")
    max_traits: int = Field(50, description="Maximum number of traits to select", ge=10, le=100)

class TraitSelectionResponse(BaseModel):
    """Step 2: API returns selected traits for user review"""
    success: bool
    campaign_info: Dict[str, Any]
    selection_summary: Dict[str, Any]
    traits: List[Dict[str, Any]]
    trait_categories_breakdown: Dict[str, Any]
    session_id: str  # For tracking this selection

class TraitUpdateRequest(BaseModel):
    """Step 3: User can modify trait selection"""
    session_id: str
    traits: List[Dict[str, Any]]  # Modified list of traits
    campaign_query: str
    audience_segment: str

class PersonaGenerationRequest(BaseModel):
    """Step 4: User confirms and requests persona generation"""
    session_id: str
    num_personas: int = Field(..., description="Number of personas to generate", ge=1, le=500)
    traits: List[Dict[str, Any]]  # Final approved traits
    campaign_query: str
    audience_segment: str
    include_narratives: bool = Field(True, description="Generate LLM narratives (recommended)")

class PersonaGenerationResponse(BaseModel):
    """Step 5: API returns generated personas"""
    success: bool
    generation_id: str
    personas_generated: int
    personas_stored: int
    persona_uuids: List[str]
    summary: Dict[str, Any]

class GetPersonasRequest(BaseModel):
    """Get all personas for a generation"""
    generation_id: Optional[str] = None
    audience_segment: Optional[str] = None
    campaign_query: Optional[str] = None
    limit: int = Field(100, ge=1, le=500)

class GetPersonaDetailRequest(BaseModel):
    """Get detailed info about specific persona"""
    persona_uuid: str

class AudienceTemplateRequest(BaseModel):
    """Request for audience template evaluation"""
    product_description: str = Field(..., description="Product or service to evaluate")
    audience_segment: str = Field(..., description="Target audience segment")
    template_key: str = Field(..., description="Evaluation template key")
    num_personas: int = Field(10, description="Number of personas to evaluate with", ge=5, le=50)
    existing_generation_id: Optional[str] = Field(None, description="Use existing personas (optional)")

class AudienceTemplateResponse(BaseModel):
    """Response from audience template evaluation"""
    success: bool
    evaluation_metadata: Dict[str, Any]
    template_details: Dict[str, Any]
    collective_feedback: Dict[str, Any]
    individual_evaluations: List[Dict[str, Any]]
    statistical_summary: Dict[str, Any]
    key_insights: List[str]

class ChatWithMemoryRequest(BaseModel):
    """Enhanced chat request with LangGraph memory"""
    persona_uuid: str = Field(..., description="Persona to chat with")
    user_message: str = Field(..., description="User's message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for continuity")
    template_context: Optional[Dict[str, Any]] = Field(None, description="Template evaluation context")
    product_context: Optional[str] = Field(None, description="Product being discussed")

class ChatWithMemoryResponse(BaseModel):
    """Response from LangGraph chat"""
    conversation_id: str
    persona_uuid: str
    user_message: str
    assistant_message: str
    full_history: List[Dict[str, str]]
    persona_context: Dict[str, Any]
    timestamp: str

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

# Create router instead of app (will be mounted in main.py with /api/audience prefix)
router = APIRouter(
    tags=["Synthetic Audience"]
)

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5454/synthetic_personas"

# Global instances
pipeline = PersonaGenerationPipeline(DATABASE_URL)
llm_generator = LLMNarrativeGenerator()
audience_evaluator = AudienceTemplateEvaluator(DATABASE_URL)
langgraph_system = LangGraphConversationSystem(DATABASE_URL)

# ============================================================================
# SHARED CONVERSATION MEMORY (LangGraph-inspired)
# ============================================================================

@dataclass
class AssetMemory:
    """Stores uploaded asset in memory for the session"""
    filename: str
    content_type: str
    base64_data: str
    upload_timestamp: str
    
@dataclass
class MessageMemory:
    """Single message in conversation history"""
    role: str  # 'user' or 'assistant'
    content: str
    persona_uuid: Optional[str] = None
    persona_name: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class GroupConversationState(TypedDict):
    """
    Shared state for group conversation (LangGraph-style)
    All personas in the group have access to this shared memory
    """
    conversation_id: str
    audience_group: str
    messages: List[Dict[str, Any]]  # Full conversation history
    assets: List[Dict[str, Any]]  # All uploaded assets (images/videos/PDFs)
    persona_uuids: List[str]  # Personas participating in this conversation
    created_at: str
    last_updated: str

# In-memory session storage (use Redis/PostgreSQL checkpointer in production)
sessions = {}  # Legacy sessions for trait selection/generation flow
group_conversation_sessions: Dict[str, GroupConversationState] = {}  # NEW: Shared memory for group chat

# ============================================================================
# HELPER FUNCTIONS: Conversation Memory Management
# ============================================================================

def get_or_create_conversation(conversation_id: str, audience_group: str, persona_uuids: List[str]) -> GroupConversationState:
    """
    Get existing conversation or create new one with shared memory
    This implements LangGraph-style state management in memory
    """
    if conversation_id not in group_conversation_sessions:
        # Create new conversation state
        group_conversation_sessions[conversation_id] = {
            'conversation_id': conversation_id,
            'audience_group': audience_group,
            'messages': [],
            'assets': [],
            'persona_uuids': persona_uuids,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
    return group_conversation_sessions[conversation_id]

def add_user_message(conversation_id: str, content: str):
    """Add user message to shared conversation history"""
    if conversation_id in group_conversation_sessions:
        group_conversation_sessions[conversation_id]['messages'].append({
            'role': 'user',
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        group_conversation_sessions[conversation_id]['last_updated'] = datetime.now().isoformat()

def add_assistant_message(conversation_id: str, persona_uuid: str, persona_name: str, content: str):
    """Add persona response to shared conversation history"""
    if conversation_id in group_conversation_sessions:
        group_conversation_sessions[conversation_id]['messages'].append({
            'role': 'assistant',
            'content': content,
            'persona_uuid': persona_uuid,
            'persona_name': persona_name,
            'timestamp': datetime.now().isoformat()
        })
        group_conversation_sessions[conversation_id]['last_updated'] = datetime.now().isoformat()

def add_asset_to_conversation(conversation_id: str, filename: str, content_type: str, base64_data: str):
    """Store uploaded asset in conversation memory so all personas can reference it"""
    if conversation_id in group_conversation_sessions:
        group_conversation_sessions[conversation_id]['assets'].append({
            'filename': filename,
            'content_type': content_type,
            'base64_data': base64_data,
            'upload_timestamp': datetime.now().isoformat()
        })
        group_conversation_sessions[conversation_id]['last_updated'] = datetime.now().isoformat()

def format_conversation_history(conversation_state: GroupConversationState) -> str:
    """Format conversation history for persona prompt context"""
    if not conversation_state['messages']:
        return ""
    
    history_text = "\n\nCONVERSATION HISTORY (shared with all group members):\n"
    for msg in conversation_state['messages']:
        if msg['role'] == 'user':
            history_text += f"\nUser: {msg['content']}\n"
        else:
            persona_name = msg.get('persona_name', 'Group Member')
            history_text += f"\n{persona_name}: {msg['content']}\n"
    
    return history_text

def format_asset_context(conversation_state: GroupConversationState) -> str:
    """Format asset information for persona context"""
    if not conversation_state['assets']:
        return ""
    
    asset_text = f"\n\nUPLOADED ASSETS (available to all group members): {len(conversation_state['assets'])} file(s)\n"
    for i, asset in enumerate(conversation_state['assets'], 1):
        asset_text += f"- Asset {i}: {asset['filename']} ({asset['content_type']})\n"
    
    return asset_text

# ============================================================================
# ENDPOINT 1: TRAIT SELECTION
# ============================================================================

@router.post("/select-traits", response_model=TraitSelectionResponse)
async def select_traits(request: TraitSelectionRequest):
    """
    Step 1: Select traits based on campaign query and audience segment

    Frontend sends:
    - Campaign description
    - Target audience segment
    - Number of traits desired

    API returns:
    - Selected traits with probabilities
    - Context analysis
    - Session ID for tracking
    """
    try:
        pipeline.connect_db()

        # Select traits using enhanced selector
        result = pipeline.select_traits_for_campaign(
            query=request.campaign_query,
            audience_segment=request.audience_segment,
            max_traits=request.max_traits
        )

        if not result.get('ready_for_generation'):
            raise HTTPException(status_code=500, detail="Trait selection failed")

        # Create session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            'trait_selection': result,
            'timestamp': datetime.now().isoformat(),
            'campaign_query': request.campaign_query,
            'audience_segment': request.audience_segment
        }

        pipeline.close_db()

        return TraitSelectionResponse(
            success=True,
            campaign_info=result['campaign_info'],
            selection_summary=result['selection_summary'],
            traits=result['traits'],
            trait_categories_breakdown=result['trait_categories_breakdown'],
            session_id=session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error selecting traits: {str(e)}")

# ============================================================================
# ENDPOINT 2: UPDATE TRAITS (Optional - user edits)
# ============================================================================

@router.post("/update-traits")
async def update_traits(request: TraitUpdateRequest):
    """
    Step 2 (Optional): User can edit/remove traits before persona generation

    Frontend sends:
    - Session ID
    - Modified list of traits

    API returns:
    - Updated trait selection
    - Confirmation
    """
    try:
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        # Update session with modified traits
        sessions[request.session_id]['trait_selection']['traits'] = request.traits
        sessions[request.session_id]['trait_selection']['selection_summary']['total_traits_selected'] = len(request.traits)

        return {
            "success": True,
            "message": "Traits updated successfully",
            "traits_count": len(request.traits),
            "session_id": request.session_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating traits: {str(e)}")

# ============================================================================
# ENDPOINT 3: GENERATE PERSONAS WITH LLM NARRATIVES
# ============================================================================

@router.post("/generate-personas", response_model=PersonaGenerationResponse)
async def generate_personas(request: PersonaGenerationRequest):
    """
    Step 3: Generate realistic personas with LLM narratives

    This is the MAIN generation step that:
    1. Creates personas matching probability distributions
    2. Generates realistic narratives using AWS Bedrock/Claude
    3. Stores personas in database

    Frontend sends:
    - Session ID (from trait selection)
    - Number of personas to generate
    - Final approved traits

    API returns:
    - Generation ID
    - List of persona UUIDs
    - Summary statistics
    """
    try:
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        pipeline.connect_db()

        # Build trait selection from approved traits
        trait_selection_json = {
            'campaign_info': {
                'query': request.campaign_query,
                'target_segment': request.audience_segment,
                'timestamp': datetime.now().isoformat()
            },
            'selection_summary': {
                'total_traits_selected': len(request.traits),
                'quality_score': 0.0  # Not needed for generation
            },
            'traits': request.traits
        }

        # Step 1: Generate personas with statistical sampling
        print(f"\n🎭 Generating {request.num_personas} personas...")
        personas = pipeline.generate_personas(
            trait_selection_json=trait_selection_json,
            num_personas=request.num_personas,
            include_narrative=False  # We'll add narratives separately
        )

        # Step 2: Generate LLM narratives if requested
        if request.include_narratives:
            print(f"\n📝 Generating LLM narratives for {len(personas)} personas...")
            personas = llm_generator.batch_generate_narratives(
                personas=personas,
                campaign_context=request.campaign_query,
                batch_size=20,  # Process 20 in parallel
                use_parallel=True
            )

        # Step 3: Store in database
        stored_uuids = pipeline.store_personas(
            personas=personas,
            trait_selection_json=trait_selection_json
        )

        # Create generation ID for tracking
        generation_id = str(uuid.uuid4())

        # Store generation info in session
        sessions[request.session_id]['generation_id'] = generation_id
        sessions[request.session_id]['persona_uuids'] = stored_uuids
        sessions[request.session_id]['num_personas'] = len(stored_uuids)

        pipeline.close_db()

        return PersonaGenerationResponse(
            success=True,
            generation_id=generation_id,
            personas_generated=len(personas),
            personas_stored=len(stored_uuids),
            persona_uuids=stored_uuids,
            summary={
                'campaign_query': request.campaign_query,
                'audience_segment': request.audience_segment,
                'traits_used': len(request.traits),
                'narratives_included': request.include_narratives,
                'timestamp': datetime.now().isoformat()
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating personas: {str(e)}")

# ============================================================================
# ENDPOINT 4: GET ALL PERSONAS
# ============================================================================

@router.post("/get-personas")
async def get_personas(request: GetPersonasRequest):
    """
    Get list of generated personas

    Frontend can filter by:
    - Generation ID
    - Audience segment
    - Campaign query

    Returns:
    - List of personas with basic info
    """
    try:
        pipeline.connect_db()

        # Build query with segment name for grouping
        query = """
            SELECT p.persona_uuid, p.campaign_context, p.generation_timestamp,
                   p.segment_id, s.segment_name, p.narrative_profile
            FROM personas p
            JOIN audience_segments s ON p.segment_id = s.id
            WHERE 1=1
        """
        params = []

        if request.audience_segment:
            query += " AND s.segment_name = %s"
            params.append(request.audience_segment)

        if request.campaign_query:
            query += " AND p.campaign_context ILIKE %s"
            params.append(f"%{request.campaign_query}%")

        query += f" ORDER BY p.generation_timestamp DESC, s.segment_name LIMIT {request.limit}"

        pipeline.cursor.execute(query, params)
        results = pipeline.cursor.fetchall()

        # Group personas by segment + campaign
        from collections import defaultdict
        grouped = defaultdict(list)

        for row in results:
            group_key = f"{row['segment_name']}_{row['campaign_context']}"
            grouped[group_key].append({
                'persona_uuid': row['persona_uuid'],
                'campaign_context': row['campaign_context'],
                'generation_timestamp': row['generation_timestamp'].isoformat(),
                'segment_id': row['segment_id'],
                'segment_name': row['segment_name'],
                'narrative_summary': row['narrative_profile'][:150] + "..." if row['narrative_profile'] else "No narrative"
            })

        # Convert to list format
        personas_list = []
        for group_key, group_personas in grouped.items():
            for persona in group_personas:
                personas_list.append(persona)

        pipeline.close_db()

        # Also return grouping info
        groups = []
        for group_key, group_personas in grouped.items():
            groups.append({
                "group_name": group_key,
                "segment_name": group_personas[0]['segment_name'],
                "campaign_context": group_personas[0]['campaign_context'],
                "persona_count": len(group_personas)
            })

        return {
            "success": True,
            "personas": personas_list,
            "groups": groups,
            "count": len(personas_list)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching personas: {str(e)}")

# ============================================================================
# ENDPOINT 5: GET PERSONA DETAIL
# ============================================================================

@router.post("/get-persona-detail")
async def get_persona_detail(request: GetPersonaDetailRequest):
    """
    Get complete details about a specific persona

    Returns:
    - Full trait profile
    - Demographics
    - Narrative (if generated)
    - Metadata
    """
    try:
        pipeline.connect_db()

        pipeline.cursor.execute("""
            SELECT
                p.persona_uuid,
                p.campaign_context,
                p.generation_timestamp,
                p.core_traits,
                p.extended_traits,
                p.demographic_info,
                p.narrative_profile,
                p.generation_metadata,
                s.segment_name
            FROM personas p
            JOIN audience_segments s ON p.segment_id = s.id
            WHERE p.persona_uuid = %s
        """, (request.persona_uuid,))

        result = pipeline.cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Persona not found")

        pipeline.close_db()

        return {
            "success": True,
            "persona": {
                'uuid': result['persona_uuid'],
                'segment': result['segment_name'],
                'campaign_context': result['campaign_context'],
                'generation_timestamp': result['generation_timestamp'].isoformat(),
                'demographics': result['demographic_info'],
                'behavioral_traits': result['core_traits'],
                'all_traits': result['extended_traits'],
                'narrative': result['narrative_profile'],
                'metadata': result['generation_metadata']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching persona: {str(e)}")

# ============================================================================
# ENDPOINT 6: GET EVALUATION TEMPLATES
# ============================================================================

@router.get("/templates")
async def get_templates():
    """
    Get all available evaluation templates

    Returns:
    - Dictionary of all templates with their details
    - Template keys, names, descriptions, focus areas
    """
    try:
        templates = audience_evaluator.get_evaluation_templates()
        return {
            "success": True,
            "templates": templates,
            "count": len(templates)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching templates: {str(e)}")

# ============================================================================
# ENDPOINT 8: AUDIENCE TEMPLATE EVALUATION (NEW - Collective Feedback)
# ============================================================================

@router.post("/evaluate-audience", response_model=AudienceTemplateResponse)
async def evaluate_audience(request: AudienceTemplateRequest):
    """
    Evaluate a product using an audience segment with a specific template

    This provides COLLECTIVE feedback from multiple personas based on:
    - ROI analysis
    - User experience
    - Brand alignment
    - Purchase intent
    - Feature importance
    - Competitive analysis

    Frontend sends:
    - Product description
    - Audience segment
    - Template to use (roi_analysis, user_experience, etc.)
    - Number of personas to evaluate with

    API returns:
    - Collective audience feedback summary
    - Individual persona evaluations
    - Statistical analysis
    - Key insights

    Example flow:
    1. User wants to know if "Healthcare Professionals" find ROI in "$200 skincare serum"
    2. API evaluates with 10 Healthcare Professional personas using ROI template
    3. Each persona evaluates based on their specific traits
    4. API aggregates into collective feedback
    5. User can then chat with individual personas for deeper insights
    """
    try:
        audience_evaluator.connect_db()

        # Perform template-based evaluation
        result = audience_evaluator.evaluate_product_with_template(
            product_description=request.product_description,
            audience_segment=request.audience_segment,
            template_key=request.template_key,
            num_personas=request.num_personas,
            existing_generation_id=request.existing_generation_id
        )

        audience_evaluator.close_db()

        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])

        return AudienceTemplateResponse(
            success=True,
            evaluation_metadata=result['evaluation_metadata'],
            template_details=result['template_details'],
            collective_feedback=result['collective_feedback'],
            individual_evaluations=result['individual_evaluations'],
            statistical_summary=result['statistical_summary'],
            key_insights=result['key_insights']
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error evaluating audience: {str(e)}")

# ============================================================================
# ENDPOINT 9: CHAT WITH PERSONA (LangGraph Enhanced with Memory)
# ============================================================================

@router.post("/chat-with-memory", response_model=ChatWithMemoryResponse)
async def chat_with_memory(request: ChatWithMemoryRequest):
    """
    Enhanced chat with persona using LangGraph for conversation memory

    This is the upgraded version of chat-with-persona that:
    - Persists conversation history in PostgreSQL
    - Maintains context across multiple interactions
    - Supports template-based evaluation context
    - Tracks product discussion context

    Frontend sends:
    - Persona UUID
    - User message
    - Optional: Conversation ID (for continuing conversation)
    - Optional: Template context (if evaluating with template)
    - Optional: Product context

    API returns:
    - Response from persona
    - Full conversation history
    - Conversation ID for continuity

    Example flow:
    1. User evaluates product with audience template (endpoint 8)
    2. User sees interesting persona in individual_evaluations
    3. User starts chat with that specific persona using this endpoint
    4. Conversation persists across multiple messages
    5. Persona stays in character and remembers context
    """
    try:
        # Use LangGraph system for memory-enabled chat
        result = await langgraph_system.chat_with_persona(
            persona_uuid=request.persona_uuid,
            user_message=request.user_message,
            conversation_id=request.conversation_id,
            template_context=request.template_context,
            product_context=request.product_context
        )

        return ChatWithMemoryResponse(
            conversation_id=result['conversation_id'],
            persona_uuid=result['persona_uuid'],
            user_message=result['user_message'],
            assistant_message=result['assistant_message'],
            full_history=result['full_history'],
            persona_context=result['persona_context'],
            timestamp=result['timestamp']
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error in chat with memory: {str(e)}")

# ============================================================================
# ENDPOINT 10: GET CONVERSATION HISTORY
# ============================================================================

@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Retrieve full conversation history by ID

    Returns:
    - Complete conversation state
    - All messages
    - Persona context
    """
    try:
        history = langgraph_system.get_conversation_history(conversation_id)

        if not history:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            "success": True,
            "conversation_id": conversation_id,
            "history": history
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversation: {str(e)}")

# ============================================================================
# DATA MANAGEMENT ENDPOINTS
# ============================================================================

@router.delete("/delete-all-personas")
async def delete_all_personas():
    """
    Delete all personas and conversation history from database

    WARNING: This action cannot be undone

    Returns:
    - Number of personas deleted
    - Number of conversation checkpoints cleared
    """
    try:
        import psycopg2
        database_url = "postgresql://postgres:postgres@localhost:5454/synthetic_personas"
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Count before deletion
        cursor.execute("SELECT COUNT(*) FROM personas")
        personas_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM checkpoints")
        checkpoints_count = cursor.fetchone()[0]

        # Delete all conversation data
        cursor.execute("DELETE FROM checkpoint_writes")
        cursor.execute("DELETE FROM checkpoint_blobs")
        cursor.execute("DELETE FROM checkpoints")

        # Delete all personas
        cursor.execute("DELETE FROM personas")

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "success": True,
            "personas_deleted": personas_count,
            "checkpoints_cleared": checkpoints_count,
            "message": f"Successfully deleted {personas_count} personas and {checkpoints_count} conversation checkpoints"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting personas: {str(e)}")

# ============================================================================
# MEDIA INPUT ENDPOINTS (Video/Image Analysis)
# ============================================================================

@router.post("/evaluate-media-with-personas")
async def evaluate_media_with_personas(
    media_file: UploadFile = File(...),
    audience_segment: str = Form(...),
    template_key: str = Form(...),
    generation_id: str = Form(None)
):
    """
    Have personas evaluate uploaded marketing video/image

    Returns:
    - Collective summary from all personas
    - Individual persona evaluations
    - Insights and recommendations
    """
    try:
        # Read and encode media
        media_content = await media_file.read()
        media_base64 = base64.b64encode(media_content).decode('utf-8')
        content_type = media_file.content_type or "image/jpeg"

        # Get template
        audience_evaluator.connect_db()
        templates = audience_evaluator.get_evaluation_templates()
        if template_key not in templates:
            raise HTTPException(status_code=400, detail=f"Template {template_key} not found")

        template = templates[template_key]

        # Get personas (use existing or get from DB)
        pipeline.connect_db()

        # Try to get personas by segment (simpler and more reliable)
        print(f"🔍 Looking for personas with segment: {audience_segment}")
        pipeline.cursor.execute("""
            SELECT p.persona_uuid, p.narrative_profile, p.campaign_context, p.core_traits, p.demographic_info
            FROM personas p
            JOIN audience_segments s ON p.segment_id = s.id
            WHERE s.segment_name = %s
            ORDER BY p.created_at DESC
            LIMIT 10
        """, (audience_segment,))

        personas = pipeline.cursor.fetchall()
        print(f"✅ Found {len(personas)} personas for evaluation")

        if not personas:
            # Get list of available segments for better error message
            pipeline.cursor.execute("SELECT DISTINCT segment_name FROM audience_segments")
            available_segments = [row['segment_name'] for row in pipeline.cursor.fetchall()]
            raise HTTPException(
                status_code=404,
                detail=f"No personas found for segment '{audience_segment}'. Available segments: {', '.join(available_segments)}"
            )

        # Evaluate media with each persona
        individual_evaluations = []

        import boto3
        import os
        
        # Use AWS credentials from environment (set in main.py startup from .env)
        bedrock = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-west-2'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        for persona in personas:
            # Create evaluation prompt with persona context
            evaluation_prompt = f"""You are evaluating marketing media from the perspective of this persona:

**Persona Profile:**
{persona['narrative_profile']}

**Campaign Context:** {persona['campaign_context'] or 'General marketing'}

**Evaluation Template:** {template['name']}
**Focus Areas:** {', '.join(template['focus_areas'])}

Please evaluate this marketing media and provide:
1. Overall impression (1-5 stars)
2. What works well
3. What could be improved
4. Likelihood to engage/purchase (1-10)
5. Specific feedback based on your persona's traits and preferences

Be authentic to your persona's perspective, background, and values."""

            # Call Claude Vision API
            message_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": content_type,
                        "data": media_base64
                    }
                },
                {
                    "type": "text",
                    "text": evaluation_prompt
                }
            ]

            response = bedrock.invoke_model(
                modelId=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0'),
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1500,
                    "messages": [{
                        "role": "user",
                        "content": message_content
                    }]
                })
            )

            result = json.loads(response['body'].read())
            evaluation = result['content'][0]['text']

            individual_evaluations.append({
                "persona_uuid": persona['persona_uuid'],
                "evaluation": evaluation,
                "persona_summary": persona['narrative_profile'][:200] + "..."
            })

        # Generate collective summary
        all_evaluations = "\n\n---\n\n".join([e['evaluation'] for e in individual_evaluations])

        summary_prompt = f"""Based on these {len(individual_evaluations)} individual persona evaluations of a marketing {content_type.split('/')[0]}, provide:

1. **Overall Consensus**: Common themes across all personas
2. **Key Strengths**: What most personas liked
3. **Areas for Improvement**: Common concerns or suggestions
4. **Audience Segmentation Insights**: How different types of personas responded
5. **Action Items**: Top 3 recommendations for improvement

EVALUATIONS:
{all_evaluations}

Provide a concise, actionable summary."""

        summary_response = bedrock.invoke_model(
            modelId=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0'),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [{
                    "role": "user",
                    "content": summary_prompt
                }]
            })
        )

        summary_result = json.loads(summary_response['body'].read())
        collective_summary = summary_result['content'][0]['text']

        pipeline.close_db()
        audience_evaluator.close_db()

        return {
            "success": True,
            "media_type": content_type,
            "template_used": template['name'],
            "num_personas": len(individual_evaluations),
            "collective_summary": collective_summary,
            "individual_evaluations": individual_evaluations,
            "audience_segment": audience_segment
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error evaluating media: {str(e)}")


@router.post("/analyze-media-campaign")
async def analyze_media_campaign(
    media_file: UploadFile = File(...),
    audience_segment: str = Form(...),
    campaign_template: str = Form(...)
):
    """
    Analyze image/video for campaign insights

    Accepts:
    - media_file: Image or video file
    - audience_segment: Target audience segment
    - campaign_template: Campaign evaluation template (e.g., "ROI Analysis", "UX Evaluation")

    Returns:
    - Media analysis
    - Campaign insights
    - Recommendations
    """
    try:
        # Read and encode media file
        media_content = await media_file.read()
        media_base64 = base64.b64encode(media_content).decode('utf-8')

        # Determine media type
        content_type = media_file.content_type or "image/jpeg"

        # Analyze media using Claude Vision
        import boto3
        bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')

        analysis_prompt = f"""Analyze this marketing campaign media for the target audience: {audience_segment}.

Template: {campaign_template}

Provide detailed analysis including:
1. Visual elements and messaging
2. Target audience alignment
3. Effectiveness for {audience_segment}
4. Recommendations for improvement
5. Predicted engagement and conversion potential"""

        # Create message with image
        message_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": content_type,
                    "data": media_base64
                }
            },
            {
                "type": "text",
                "text": analysis_prompt
            }
        ]

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [{
                    "role": "user",
                    "content": message_content
                }]
            })
        )

        result = json.loads(response['body'].read())
        analysis = result['content'][0]['text']

        return {
            "success": True,
            "media_type": content_type,
            "audience_segment": audience_segment,
            "campaign_template": campaign_template,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error analyzing media: {str(e)}")


@router.post("/chat-with-persona-media")
async def chat_with_persona_media(
    persona_uuid: str = Form(...),
    user_message: str = Form(...),
    media_file: UploadFile = File(...),
    conversation_history: str = Form("[]")
):
    """
    Chat with a persona about a specific image/video

    Accepts:
    - persona_uuid: ID of persona to chat with
    - user_message: User's question about the media
    - media_file: Image or video file
    - conversation_history: JSON string of previous messages

    Returns:
    - Persona's response about the media
    - Updated conversation history
    """
    try:
        pipeline.connect_db()

        # Get persona details
        pipeline.cursor.execute("""
            SELECT
                p.persona_uuid,
                p.campaign_context,
                p.narrative_profile,
                p.core_traits,
                p.demographic_info,
                s.segment_name
            FROM personas p
            JOIN audience_segments s ON p.segment_id = s.segment_id
            WHERE p.persona_uuid = %s
        """, (persona_uuid,))

        persona_row = pipeline.cursor.fetchone()

        if not persona_row:
            raise HTTPException(status_code=404, detail=f"Persona {persona_uuid} not found")

        persona_data = {
            'uuid': persona_row[0],
            'campaign_context': persona_row[1],
            'narrative': persona_row[2],
            'traits': persona_row[3] if persona_row[3] else {},
            'demographics': persona_row[4] if persona_row[4] else {},
            'segment': persona_row[5]
        }

        # Read and encode media
        media_content = await media_file.read()
        media_base64 = base64.b64encode(media_content).decode('utf-8')
        content_type = media_file.content_type or "image/jpeg"

        # Parse conversation history
        history = json.loads(conversation_history) if conversation_history else []

        # Build persona context
        persona_context = f"""You are responding as this specific persona:

Narrative: {persona_data['narrative']}

Key Traits: {json.dumps(persona_data['traits'], indent=2)}
Demographics: {json.dumps(persona_data['demographics'], indent=2)}

Respond to the user's question about the image/video AS THIS PERSONA. Stay in character based on your traits, background, and preferences."""

        # Build message with image
        message_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": content_type,
                    "data": media_base64
                }
            },
            {
                "type": "text",
                "text": f"{persona_context}\n\nUser's question: {user_message}"
            }
        ]

        # Add conversation history as system context
        messages = []
        if history:
            for msg in history[-5:]:  # Last 5 messages for context
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": message_content})

        # Get response from Claude
        import boto3
        bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": messages
            })
        )

        result = json.loads(response['body'].read())
        persona_response = result['content'][0]['text']

        # Update history
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": persona_response})

        return {
            "success": True,
            "persona_uuid": persona_uuid,
            "persona_summary": {
                "segment": persona_data['segment'],
                "campaign_context": persona_data['campaign_context']
            },
            "response": persona_response,
            "conversation_history": history
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error in media chat: {str(e)}")
    finally:
        if pipeline.cursor:
            pipeline.cursor.close()

# ============================================================================
# NEW: GROUP CHAT ENDPOINTS (Client Requirement)
# ============================================================================

@router.post("/chat-with-group")
async def chat_with_group(
    audience_group: str = Form(...),
    user_message: str = Form(...),
    media_file: UploadFile = File(None),
    conversation_id: str = Form(None)
):
    """
    Chat with an ENTIRE audience group collectively WITH SHARED MEMORY
    
    LANGGRAPH-INSPIRED IMPLEMENTATION:
    - All personas share the same conversation state
    - Conversation history persists across multiple turns
    - Uploaded assets are stored in memory and accessible to all personas
    - Each persona can reference previous messages and assets
    
    Args:
        audience_group: Group name (e.g., "Healthcare Professionals_anti-aging serum")
        user_message: User's question/message
        media_file: Optional image/video upload
        conversation_id: Optional conversation ID for continuity (auto-generated if not provided)
        
    Returns:
        - Collective response from all personas in group
        - Individual persona perspectives
        - Full conversation history with shared context
    """
    try:
        pipeline.connect_db()
        
        # Parse group name to get segment and campaign
        parts = audience_group.split('_', 1)
        segment_name = parts[0] if len(parts) > 0 else audience_group
        campaign_context = parts[1] if len(parts) > 1 else ""
        
        # Get all personas in this group
        query = """
            SELECT p.persona_uuid, p.narrative_profile, p.core_traits, 
                   p.demographic_info, p.campaign_context
            FROM personas p
            JOIN audience_segments s ON p.segment_id = s.id
            WHERE s.segment_name = %s
        """
        params = [segment_name]
        
        if campaign_context:
            query += " AND p.campaign_context ILIKE %s"
            params.append(f"%{campaign_context}%")
            
        query += " LIMIT 10"  # Limit to 10 personas for group chat
        
        pipeline.cursor.execute(query, params)
        personas = pipeline.cursor.fetchall()
        
        if not personas:
            raise HTTPException(status_code=404, detail=f"No personas found for group: {audience_group}")
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"group_{segment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Get persona UUIDs
        persona_uuids = [p['persona_uuid'] for p in personas]
        
        # Get or create conversation state (LangGraph-style shared memory)
        conversation_state = get_or_create_conversation(conversation_id, audience_group, persona_uuids)
        
        # Process and store media asset if uploaded
        media_base64 = None
        content_type = None
        if media_file:
            media_content = await media_file.read()
            media_base64 = base64.b64encode(media_content).decode('utf-8')
            content_type = media_file.content_type or "image/jpeg"
            
            # Store asset in shared memory so all personas can access it
            add_asset_to_conversation(
                conversation_id,
                media_file.filename or "uploaded_file",
                content_type,
                media_base64
            )
        
        # Add user message to shared conversation history
        add_user_message(conversation_id, user_message)
        
        # Format shared context for all personas
        conversation_history = format_conversation_history(conversation_state)
        asset_context = format_asset_context(conversation_state)
        
        # Get responses from each persona in the group (PARALLEL - all personas respond simultaneously!)
        import boto3
        import asyncio
        
        bedrock = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-west-2'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Define async function to get response from a single persona
        async def get_persona_response(persona, index):
            """Get response from one persona asynchronously"""
            persona_name = f"{segment_name} - Persona {index+1}"
            
            # Build persona context WITH SHARED MEMORY
            persona_prompt = f"""You are responding as this persona from the {segment_name} segment:

{persona['narrative_profile']}

Key Traits: {json.dumps(persona['core_traits'], indent=2) if persona['core_traits'] else 'N/A'}

{conversation_history}
{asset_context}

CURRENT USER MESSAGE: {user_message}

IMPORTANT INSTRUCTIONS:
- You have access to the full conversation history above (shared with all group members)
- You can reference previous messages and uploaded assets
- Respond authentically from your persona's perspective
- Share your genuine thoughts, opinions, and reactions
- DO NOT include any physical actions, gestures, or stage directions (e.g., "fixes glasses", "leans forward", "adjusts shirt", etc.)
- Focus ONLY on your actual verbal/written response
- Be conversational and natural
- You can use formatting like bullet points or numbered lists if helpful
- If referring to previous messages or assets, be specific

Respond now:"""

            # Build message content
            message_content = []
            
            # Include MOST RECENT asset only (to avoid token limits)
            if media_file and media_base64:
                message_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": content_type,
                        "data": media_base64
                    }
                })
            
            message_content.append({
                "type": "text",
                "text": persona_prompt
            })
            
            # Get response from Claude (this is the I/O operation that will run in parallel)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: bedrock.invoke_model(
                    modelId=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0'),
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1000,
                        "messages": [{
                            "role": "user",
                            "content": message_content
                        }]
                    })
                )
            )
            
            result = json.loads(response['body'].read())
            persona_response = result['content'][0]['text']
            
            # Add persona response to shared conversation history
            add_assistant_message(conversation_id, persona['persona_uuid'], persona_name, persona_response)
            
            return {
                "persona_uuid": persona['persona_uuid'],
                "response": persona_response,
                "persona_summary": persona['narrative_profile'][:150] + "...",
                "index": index  # For ordering
            }
        
        # Execute all persona responses IN PARALLEL using asyncio.gather()
        print(f"⚡ Calling {len(personas)} personas in parallel...")
        tasks = [get_persona_response(persona, i) for i, persona in enumerate(personas)]
        individual_responses = await asyncio.gather(*tasks)
        
        # Sort by index to maintain order
        individual_responses = sorted(individual_responses, key=lambda x: x['index'])
        print(f"✅ All {len(individual_responses)} personas responded!")
        
        # Generate collective summary (also aware of conversation history)
        all_responses = "\n\n---\n\n".join([
            f"Persona {i+1}: {r['response']}" 
            for i, r in enumerate(individual_responses)
        ])
        
        summary_prompt = f"""Based on these {len(individual_responses)} responses from {segment_name} personas to the question: "{user_message}"

{conversation_history}

LATEST INDIVIDUAL RESPONSES:
{all_responses}

Provide a collective summary that:
1. Captures the overall consensus
2. Highlights diverse perspectives
3. Identifies key themes
4. Provides actionable insights
5. References conversation context if relevant

Format as a conversational response to the user."""

        summary_response = bedrock.invoke_model(
            modelId=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0'),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "messages": [{
                    "role": "user",
                    "content": summary_prompt
                }]
            })
        )
        
        summary_result = json.loads(summary_response['body'].read())
        collective_response = summary_result['content'][0]['text']
        
        pipeline.close_db()
        
        # Return response with full conversation state
        return {
            "success": True,
            "conversation_id": conversation_id,
            "audience_group": audience_group,
            "num_personas": len(individual_responses),
            "collective_response": collective_response,
            "individual_responses": individual_responses,
            "conversation_history": conversation_state['messages'],  # Full history
            "total_assets": len(conversation_state['assets']),  # Asset count
            "has_media": media_file is not None,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error in group chat: {str(e)}")



@router.post("/chat-with-persona-enhanced")
async def chat_with_persona_enhanced(
    persona_uuid: str = Form(...),
    user_message: str = Form(...),
    media_file: UploadFile = File(None),
    conversation_id: str = Form(None)
):
    """
    Enhanced individual persona chat with media support
    
    NEW CLIENT REQUIREMENT:
    - User can select individual persona from a group
    - Chat one-on-one with that specific persona
    - Supports text + media upload in chat
    - Maintains conversation history
    
    Args:
        persona_uuid: Specific persona to chat with
        user_message: User's question/message
        media_file: Optional image/video upload
        conversation_id: Optional conversation ID for continuity
        
    Returns:
        - Persona's response
        - Conversation history
        - Media context if uploaded
    """
    try:
        pipeline.connect_db()
        
        # Get persona details
        pipeline.cursor.execute("""
            SELECT
                p.persona_uuid,
                p.campaign_context,
                p.narrative_profile,
                p.core_traits,
                p.demographic_info,
                s.segment_name
            FROM personas p
            JOIN audience_segments s ON p.segment_id = s.id
            WHERE p.persona_uuid = %s
        """, (persona_uuid,))
        
        persona_row = pipeline.cursor.fetchone()
        
        if not persona_row:
            raise HTTPException(status_code=404, detail=f"Persona {persona_uuid} not found")
        
        persona_data = {
            'uuid': persona_row['persona_uuid'],
            'campaign_context': persona_row['campaign_context'],
            'narrative': persona_row['narrative_profile'],
            'traits': persona_row['core_traits'] if persona_row['core_traits'] else {},
            'demographics': persona_row['demographic_info'] if persona_row['demographic_info'] else {},
            'segment': persona_row['segment_name']
        }
        
        # Process media if uploaded
        media_context = ""
        media_base64 = None
        content_type = None
        
        if media_file:
            media_content = await media_file.read()
            media_base64 = base64.b64encode(media_content).decode('utf-8')
            content_type = media_file.content_type or "image/jpeg"
            media_context = f"\n\n[User uploaded an image/video for context]"
        
        # Build persona context
        persona_prompt = f"""You are responding as this specific persona:

{persona_data['narrative']}

Key Traits: {json.dumps(persona_data['traits'], indent=2)}
Demographics: {json.dumps(persona_data['demographics'], indent=2)}

User's question: {user_message}{media_context}

IMPORTANT INSTRUCTIONS:
- Respond authentically AS THIS PERSONA
- Share your genuine thoughts, opinions, and reactions
- DO NOT include any physical actions, gestures, or stage directions (e.g., "fixes glasses", "leans forward", "adjusts shirt", "*smiles*", etc.)
- Focus ONLY on your actual verbal/written response
- Be conversational and natural
- You can use formatting like bullet points or numbered lists if helpful
- Stay in character based on your traits, background, and preferences

Respond now:"""

        # Build message content
        message_content = []
        
        if media_file:
            message_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": content_type,
                    "data": media_base64
                }
            })
        
        message_content.append({
            "type": "text",
            "text": persona_prompt
        })
        
        # Get response from Claude
        import boto3
        bedrock = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-west-2'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        response = bedrock.invoke_model(
            modelId=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0'),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "messages": [{
                    "role": "user",
                    "content": message_content
                }]
            })
        )
        
        result = json.loads(response['body'].read())
        persona_response = result['content'][0]['text']
        
        # Store conversation history (simplified - expand with database storage if needed)
        conversation_history = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": persona_response}
        ]
        
        pipeline.close_db()
        
        return {
            "success": True,
            "persona_uuid": persona_uuid,
            "persona_summary": {
                "segment": persona_data['segment'],
                "campaign_context": persona_data['campaign_context'],
                "narrative_preview": persona_data['narrative'][:200] + "..."
            },
            "response": persona_response,
            "conversation_history": conversation_history,
            "has_media": media_file is not None,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error in persona chat: {str(e)}")


# ============================================================================
# HEALTH CHECK & INFO ENDPOINTS
# ============================================================================

@router.get("/")
async def root():
    return {
        "message": "Synthetic Audience Platform API",
        "version": "3.0.0",
        "status": "operational",
        "features": {
            "persona_generation": "Generate realistic personas with traits and narratives",
            "audience_evaluation": "Evaluate products with collective audience feedback using templates",
            "memory_chat": "Chat with personas using LangGraph for persistent memory",
            "group_chat": "NEW - Chat with entire audience groups",
            "media_chat": "NEW - Upload media in conversations"
        },
        "endpoints": {
            "trait_selection": "/select-traits",
            "update_traits": "/update-traits",
            "generate_personas": "/generate-personas",
            "get_personas": "/get-personas",
            "get_persona_detail": "/get-persona-detail",
            "get_templates": "/templates",
            "evaluate_audience": "/evaluate-audience",
            "chat_with_memory": "/chat-with-memory",
            "chat_with_group": "/chat-with-group (NEW)",
            "chat_with_persona_enhanced": "/chat-with-persona-enhanced (NEW)",
            "get_conversation": "/conversation/{conversation_id}",
            "analyze_media_campaign": "/analyze-media-campaign",
            "chat_with_persona_media": "/chat-with-persona-media"
        },
        "documentation": "/docs"
    }

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        pipeline.connect_db()
        pipeline.cursor.execute("SELECT 1")
        pipeline.close_db()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


# ============================================================================
# INSIGHTS DASHBOARD ENDPOINT (NEW)
# ============================================================================

@router.post("/generate-insights-dashboard")
async def generate_insights_dashboard(
    audience_group: str = Form(...),
    campaign_context: str = Form(...),
    campaign_goal: str = Form(default="Drive awareness and sales"),
    conversation_history: str = Form(default="[]")
):
    """
    Generate real-time marketing insights dashboard from group chat conversation
    
    This analyzes the group chat conversation and returns actionable metrics:
    - Add to Cart Rate
    - Purchase Intent Score
    - Demographic Performance
    - Sentiment Analysis
    - Key Objections
    - Targeting Recommendations
    
    Args:
        audience_group: Group identifier (e.g., "University Students_Beauty Product Launch")
        campaign_context: What product/campaign is being discussed
        campaign_goal: Campaign objective
        conversation_history: JSON array of conversation messages
    
    Returns:
        Dashboard data with charts and actionable insights
    """
    try:
        from services.conversation_insights_engine import ConversationInsightsEngine
        
        print(f"📊 Insights request - conversation_history type: {type(conversation_history)}")
        print(f"📊 First 100 chars: {str(conversation_history)[:100]}")
        
        # Parse conversation history - handle both string and dict
        if isinstance(conversation_history, str):
            try:
                messages = json.loads(conversation_history)
                print(f"✅ Parsed {len(messages)} messages from JSON string")
            except Exception as e:
                print(f"❌ Failed to parse conversation_history: {e}")
                messages = []
        elif isinstance(conversation_history, (list, dict)):
            messages = conversation_history if isinstance(conversation_history, list) else []
            print(f"✅ Received {len(messages)} messages as list")
        else:
            messages = []
            print(f"⚠️ Unknown conversation_history type: {type(conversation_history)}")
        
        # Parse group key to get segment name and campaign context
        parts = audience_group.split("_")
        segment_name = parts[0] if len(parts) > 0 else ""
        campaign_ctx = "_".join(parts[1:]) if len(parts) > 1 else ""
        
        print(f"🔍 Looking for personas: segment={segment_name}, campaign={campaign_ctx}")
        
        # Get personas from DATABASE - same query as get-personas endpoint
        pipeline.connect_db()
        
        query = """
            SELECT p.persona_uuid, p.campaign_context, p.narrative_profile, 
                   p.demographic_info, s.segment_name
            FROM personas p
            JOIN audience_segments s ON p.segment_id = s.id
            WHERE s.segment_name = %s AND p.campaign_context = %s
            LIMIT 10
        """
        
        pipeline.cursor.execute(query, (segment_name, campaign_ctx))
        rows = pipeline.cursor.fetchall()
        pipeline.close_db()
        
        if not rows:
            raise HTTPException(status_code=404, detail=f"No personas found for group: {audience_group} (segment={segment_name}, campaign={campaign_ctx})")
        
        print(f"✅ Loaded {len(rows)} personas from database")
        
        # Format personas
        personas = []
        for row in rows:
            # demographic_info is already a dict from psycopg2's JSON column - don't parse it again!
            demographic_info = row['demographic_info'] if row['demographic_info'] else {}
            # If it's a string, parse it; if already dict, use as-is
            if isinstance(demographic_info, str):
                try:
                    demographic_info = json.loads(demographic_info)
                except:
                    demographic_info = {}
            
            personas.append({
                "persona_uuid": row['persona_uuid'],
                "segment_name": row['segment_name'],
                "campaign_context": row['campaign_context'],
                "narrative_profile": row['narrative_profile'] or "",
                "demographic_info": demographic_info
            })
        
        # Initialize insights engine
        import boto3
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-west-2')
        insights_engine = ConversationInsightsEngine(bedrock_client=bedrock_client)
        
        print(f"📊 Generating insights with structured persona analysis...")
        
        # IMPORTANT: If no persona responses yet, trigger structured analysis
        # This asks each persona to analyze the asset and respond in JSON format
        if len(messages) <= 2:  # Only asset upload, no real conversation
            print("⚡ No responses yet - triggering structured persona analysis")
            dashboard = await insights_engine.generate_insights_with_persona_analysis(
                personas=personas,
                product_context=campaign_context,
                campaign_goal=campaign_goal,
                uploaded_assets=messages  # Pass asset info
            )
        else:
            # Original flow: analyze existing conversation
            dashboard = await insights_engine.generate_insights_dashboard(
                conversation_history=messages,
                personas=personas,
                product_context=campaign_context,
                campaign_goal=campaign_goal
            )
        
        return {
            "success": True,
            "dashboard": dashboard,
            "audience_group": audience_group,
            "num_personas": len(personas),
            "num_messages_analyzed": len(messages)
        }
        
    except Exception as e:
        print(f"Error generating insights dashboard: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


# ============================================================================
# Note: This router is mounted in main.py
# ============================================================================