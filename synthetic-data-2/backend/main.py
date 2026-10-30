from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import uvicorn
import os
from datetime import datetime
import asyncio
from loguru import logger
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from dotenv import load_dotenv

# Helper function to convert numpy types to Python native types
def convert_numpy_types(obj):
    """Recursively convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj

# Load environment variables from .env file
load_dotenv()

# Import core components
from engines.hybrid_engine import HybridPersonaEngine, GenerationConfig, GenerationRequest, GenerationMethod
from services.evaluation_metrics import EvaluationMetrics
from services.clustering_engine import ClusteringEngine
from services.distribution_matcher import DistributionMatcher
from storage.file_storage import FileStorageManager, StorageConfig
from models.persona_models import PersonaFormData, GeneratedPersona, EvaluationResults

# Import advanced services
from extraction.llm_persona_service import LLMPersonaService, PersonaExtractionRequest, PersonaExtractionResult
from extraction.advanced_nlp_service import AdvancedNLPService
from extraction.demographic_extraction_service import DemographicExtractionService, DemographicExtractionResult
from scoring.validation_service import PersonaValidationService, ValidationResult

# Import audience generation API
from features.synthetic_audience.api import router as audience_router
from scoring.bias_detection_service import BiasDetectionService, BiasAnalysisResult
from scoring.confidence_scoring_service import ConfidenceScoringService, PersonaConfidenceProfile
from scoring.validation_service import PersonaValidationService
from storage.data_adapter import ConfidenceDataAdapter

# Additional imports for text-to-persona functionality
import re
# import spacy  # Commented out due to installation issues
from textblob import TextBlob
from collections import Counter
import hashlib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans as TextKMeans
import nltk 
from datetime import datetime, timezone

# Pydantic models for API requests/responses
class PersonaGenerationRequest(BaseModel):
    sample_size: int = Field(default=10, ge=1, le=1000, description="Number of personas to generate")
    persona_name: Optional[str] = Field(default=None, description="Base name for generated personas (for folder organization)")
    demographic_constraints: Optional[Dict[str, Any]] = Field(default=None, description="Demographic filtering constraints")
    psychographic_preferences: Optional[Dict[str, Any]] = Field(default=None, description="Psychographic targeting preferences")
    behavioral_patterns: Optional[Dict[str, Any]] = Field(default=None, description="Behavioral pattern specifications")
    generation_method: str = Field(default="hybrid_advanced", description="Generation method: rule_based, llm_only, diversity_only, hybrid_basic, hybrid_advanced, distribution_matched")
    quality_threshold: float = Field(default=float(os.getenv("DEFAULT_QUALITY_THRESHOLD", "0.3")), ge=0.0, le=1.0, description="Minimum quality threshold")
    enable_clustering: bool = Field(default=True, description="Enable clustering analysis")
    distribution_matching: bool = Field(default=True, description="Enable distribution matching")
    target_clusters: Optional[int] = Field(default=None, description="Target number of clusters")
    industry_context: Optional[str] = Field(default=None, description="Industry context for personas")
    use_case_context: Optional[str] = Field(default=None, description="Use case context for personas")
    export_format: str = Field(default="json", description="Export format: json, csv, both")
    project_name: Optional[str] = Field(default=None, description="Project name for organization")
    tags: Optional[List[str]] = Field(default=None, description="Tags for categorization")

class PersonaResponse(BaseModel):
    id: Optional[str] = None
    demographics: Dict[str, Any]
    psychographics: Dict[str, Any]
    behavioral_patterns: Dict[str, Any]
    narrative: Optional[str] = None
    generation_method: str
    confidence_score: float
    cluster_id: Optional[int] = None
    component_scores: Optional[Dict[str, Any]] = None

class GenerationResponse(BaseModel):
    personas: List[PersonaResponse]
    generation_metadata: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    clustering_results: Optional[Dict[str, Any]] = None
    distribution_analysis: Optional[Dict[str, Any]] = None
    storage_ids: Optional[List[str]] = None
    export_paths: Optional[List[str]] = None
    execution_time: float
    success: bool
    message: str
    warnings: Optional[List[str]] = None
    errors: Optional[List[str]] = None

# Text-to-Persona Models
class TextToPersonaRequest(BaseModel):
    text_content: str = Field(..., min_length=50, description="Input text content for persona extraction")
    file_content: Optional[str] = Field(default=None, description="File content if uploaded")
    batch_processing: bool = Field(default=False, description="Enable batch processing for multiple texts")
    persona_count: int = Field(default=3, ge=1, le=10, description="Number of personas to generate")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")
    domain: Optional[str] = Field(default=None, description="Domain context (e.g., healthcare, finance)")
    language: str = Field(default="en", description="Text language")
    demographic_focus: Optional[List[str]] = Field(default=None, description="Focus areas for demographic extraction")
    custom_attributes: Optional[List[str]] = Field(default=None, description="Custom attributes to extract")
    processing_options: Optional[Dict[str, Any]] = Field(default=None, description="Advanced processing options")

class ExtractedPersona(BaseModel):
    id: str
    name: str
    demographics: Dict[str, Any] = Field(description="Age, gender, location, occupation, income, education, family_status")
    psychographics: Dict[str, Any] = Field(description="Interests, values, personality_traits, lifestyle, motivations")
    behaviors: Dict[str, Any] = Field(description="Shopping habits, communication preferences, decision factors, media consumption, technology usage")
    confidence_scores: Dict[str, float] = Field(description="Confidence scores for each attribute category")
    source_evidence: Dict[str, List[str]] = Field(description="Text evidence supporting each extracted attribute")
    processing_metadata: Dict[str, Any] = Field(description="Processing information and model details")

class TextToPersonaResponse(BaseModel):
    generated_personas: List[ExtractedPersona]
    processing_summary: Dict[str, Any]
    text_analysis: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    execution_time: float
    success: bool
    message: str
    warnings: Optional[List[str]] = None
    errors: Optional[List[str]] = None

# Persona-to-Persona Models
class PersonaToPersonaRequest(BaseModel):
    source_persona_ids: List[str] = Field(..., min_items=1, max_items=5, description="Source persona IDs")
    operation_type: str = Field(..., description="Operation type: merge, variants, evolution, mixing")
    output_count: int = Field(default=1, ge=1, le=5, description="Number of output personas")
    validation_strictness: str = Field(default="medium", description="Validation level: low, medium, high")
    attribute_weights: Optional[Dict[str, float]] = Field(default=None, description="Weights for different attribute categories")
    scenario_context: Optional[str] = Field(default=None, description="Scenario context for generation")
    mutation_intensity: float = Field(default=0.3, ge=0.0, le=1.0, description="Intensity of mutations for variants/evolution")
    advanced_settings: Optional[Dict[str, Any]] = Field(default=None, description="Advanced processing settings")

class GeneratedPersonaP2P(BaseModel):
    id: str
    name: str
    source_personas: List[Dict[str, Any]] = Field(description="Source persona information with weights")
    generation_method: str
    attributes: Dict[str, Any] = Field(description="Generated persona attributes")
    inheritance_map: Dict[str, Dict[str, Any]] = Field(description="Mapping of inherited attributes to sources")
    quality_metrics: Dict[str, float] = Field(description="Quality assessment scores")
    operation_metadata: Dict[str, Any] = Field(description="Operation details and parameters")
    bias_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Bias detection analysis results")

class PersonaToPersonaResponse(BaseModel):
    generated_personas: List[GeneratedPersonaP2P]
    operation_summary: Dict[str, Any]
    quality_analysis: Dict[str, Any]
    generation_log: List[Dict[str, Any]]
    execution_time: float
    success: bool
    message: str
    warnings: Optional[List[str]] = None
    errors: Optional[List[str]] = None

app = FastAPI(
    title="Synthetic Persona Generation API",
    description="AI-powered persona generation with hybrid engine and advanced evaluation metrics",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3010", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include audience generation router
app.include_router(audience_router, prefix="/api/audience", tags=["audience-generation"])

# Global instances (will be initialized on startup)
hybrid_engine = None
evaluation_metrics = None
clustering_engine = None
distribution_matcher = None
file_storage = None

# Advanced service instances
llm_persona_service = None
advanced_nlp_service = None
demographic_extraction_service = None
validation_service = None
bias_detection_service = None
confidence_scoring_service = None
data_adapter = None

# Analytics helper functions
def _calculate_relationship_analysis(persona_data_list):
    """Calculate clustering and similarity metrics"""
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    
    if len(persona_data_list) < 2:
        return {
            "silhouette_score": 0.0,
            "cluster_visualization": [],
            "similarity_matrix": [],
            "cluster_centers": []
        }
    
    # Extract numerical features for clustering
    features = []
    for persona in persona_data_list:
        feature_vector = []
        # Add personality traits
        personality = persona.get('personality', {})
        feature_vector.extend([
            personality.get('openness', 0.5),
            personality.get('conscientiousness', 0.5),
            personality.get('extraversion', 0.5),
            personality.get('agreeableness', 0.5),
            personality.get('neuroticism', 0.5)
        ])
        # Add values
        values = persona.get('values', {})
        feature_vector.extend([
            values.get('achievement', 0.5),
            values.get('security', 0.5),
            values.get('hedonism', 0.5),
            values.get('tradition', 0.5),
            values.get('benevolence', 0.5)
        ])
        # Add age (normalized)
        feature_vector.append(persona.get('age', 30) / 100.0)
        features.append(feature_vector)
    
    features_array = np.array(features)
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features_array)
    
    # Perform clustering
    n_clusters = min(3, len(persona_data_list))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(features_scaled)
    
    # Calculate silhouette score
    silhouette_avg = silhouette_score(features_scaled, cluster_labels) if len(set(cluster_labels)) > 1 else 0.0
    
    # PCA for visualization
    pca = PCA(n_components=2)
    features_2d = pca.fit_transform(features_scaled)
    
    # Create visualization data
    cluster_visualization = []
    for i, persona in enumerate(persona_data_list):
        cluster_visualization.append({
            "persona_id": persona['id'],
            "name": persona['name'],
            "x": float(features_2d[i][0]),
            "y": float(features_2d[i][1]),
            "cluster": int(cluster_labels[i]),
            "age": persona['age'],
            "gender": persona['gender']
        })
    
    # Calculate similarity matrix
    from sklearn.metrics.pairwise import cosine_similarity
    similarity_matrix = cosine_similarity(features_scaled).tolist()
    
    # Cluster centers
    cluster_centers = []
    for i in range(n_clusters):
        center_2d = pca.transform(kmeans.cluster_centers_[i].reshape(1, -1))[0]
        cluster_centers.append({
            "cluster": i,
            "x": float(center_2d[0]),
            "y": float(center_2d[1]),
            "size": int(np.sum(cluster_labels == i))
        })
    
    return {
        "silhouette_score": float(silhouette_avg),
        "cluster_visualization": cluster_visualization,
        "similarity_matrix": similarity_matrix,
        "cluster_centers": cluster_centers
    }

def _calculate_quality_assessment(persona_data_list):
    """Calculate quality and reliability metrics"""
    if not persona_data_list:
        return {
            "average_quality_scores": {},
            "uniqueness_distribution": [],
            "completeness_stats": {},
            "consistency_metrics": {}
        }
    
    # Aggregate quality metrics
    quality_scores = {
        "realism_score": [],
        "uniqueness_score": [],
        "completeness_score": [],
        "consistency_score": [],
        "overall_quality": []
    }
    
    for persona in persona_data_list:
        quality_metrics = persona.get('quality_metrics', {})
        for key in quality_scores.keys():
            score = quality_metrics.get(key, 0.0)
            quality_scores[key].append(score)
    
    # Calculate averages
    average_quality_scores = {}
    for key, scores in quality_scores.items():
        if scores:
            average_quality_scores[key] = {
                "mean": float(np.mean(scores)),
            "std": float(np.std(scores)),
            "min": float(np.min(scores)),
            "max": float(np.max(scores))
            }
    
    return {
        "average_quality_scores": average_quality_scores,
        "uniqueness_distribution": quality_scores.get("uniqueness_score", []),
        "completeness_stats": average_quality_scores.get("completeness_score", {}),
        "consistency_metrics": average_quality_scores.get("consistency_score", {})
    }

def _calculate_diversity_metrics(persona_data_list):
    """Calculate diversity and coverage metrics"""
    if not persona_data_list:
        return {
            "diversity_index": 0.0,
            "psychographic_diversity": {},
            "demographic_coverage": {},
            "feature_importance": {}
        }
    
    # Calculate personality trait diversity
    personality_traits = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
    psychographic_diversity = {}
    
    for trait in personality_traits:
        trait_values = []
        for persona in persona_data_list:
            personality = persona.get('personality', {})
            trait_values.append(personality.get(trait, 0.5))
        
        if trait_values:
            psychographic_diversity[trait] = {
                "mean": float(np.mean(trait_values)),
                "std": float(np.std(trait_values)),
                "range": float(np.max(trait_values) - np.min(trait_values))
            }
    
    # Calculate overall diversity index (coefficient of variation)
    all_trait_stds = [metrics["std"] for metrics in psychographic_diversity.values()]
    diversity_index = float(np.mean(all_trait_stds)) if all_trait_stds else 0.0
    
    return {
        "diversity_index": diversity_index,
        "psychographic_diversity": psychographic_diversity,
        "demographic_coverage": _calculate_demographic_coverage(persona_data_list),
        "feature_importance": _calculate_feature_importance(persona_data_list)
    }

def _calculate_bias_indicators(persona_data_list):
    """Calculate bias detection metrics"""
    if not persona_data_list:
        return {
            "gender_bias_score": 0.0,
            "age_distribution_skew": 0.0,
            "geographic_concentration": 0.0,
            "bias_alerts": []
        }
    
    # Gender distribution analysis
    gender_counts = {}
    for persona in persona_data_list:
        gender = persona.get('gender', 'Unknown')
        gender_counts[gender] = gender_counts.get(gender, 0) + 1
    
    total_personas = len(persona_data_list)
    gender_bias_score = 0.0
    if 'Male' in gender_counts and 'Female' in gender_counts:
        male_ratio = gender_counts['Male'] / total_personas
        female_ratio = gender_counts['Female'] / total_personas
        gender_bias_score = abs(male_ratio - female_ratio)
    
    # Age distribution analysis
    ages = [persona.get('age', 30) for persona in persona_data_list]
    age_skew = float(abs(np.mean(ages) - np.median(ages))) if ages else 0.0
    
    # Geographic concentration
    locations = []
    for persona in persona_data_list:
        location = persona.get('location', {})
        if isinstance(location, dict):
            country = location.get('country', 'Unknown')
            locations.append(country)
        else:
            locations.append('Unknown')
    
    location_counts = {}
    for location in locations:
        location_counts[location] = location_counts.get(location, 0) + 1
    
    # Calculate geographic concentration (Herfindahl index)
    geographic_concentration = 0.0
    if location_counts:
        for count in location_counts.values():
            proportion = count / total_personas
            geographic_concentration += proportion ** 2
    
    # Generate bias alerts
    bias_alerts = []
    if gender_bias_score > 0.3:
        bias_alerts.append(f"High gender bias detected: {gender_bias_score:.2f}")
    if age_skew > 10:
        bias_alerts.append(f"Age distribution is skewed: {age_skew:.1f} years")
    if geographic_concentration > 0.7:
        bias_alerts.append(f"High geographic concentration: {geographic_concentration:.2f}")
    
    return {
        "gender_bias_score": float(gender_bias_score),
        "age_distribution_skew": float(age_skew),
        "geographic_concentration": float(geographic_concentration),
        "bias_alerts": bias_alerts
    }

def _calculate_demographic_distribution(persona_data_list):
    """Calculate demographic distribution metrics"""
    if not persona_data_list:
        return {}
    
    # Age distribution
    ages = [persona.get('age', 30) for persona in persona_data_list]
    age_ranges = {
        "18-25": 0, "26-35": 0, "36-45": 0, "46-55": 0, "56-65": 0, "65+": 0
    }
    
    for age in ages:
        if age <= 25:
            age_ranges["18-25"] += 1
        elif age <= 35:
            age_ranges["26-35"] += 1
        elif age <= 45:
            age_ranges["36-45"] += 1
        elif age <= 55:
            age_ranges["46-55"] += 1
        elif age <= 65:
            age_ranges["56-65"] += 1
        else:
            age_ranges["65+"] += 1
    
    # Gender distribution
    gender_distribution = {}
    for persona in persona_data_list:
        gender = persona.get('gender', 'Unknown')
        gender_distribution[gender] = gender_distribution.get(gender, 0) + 1
    
    # Income distribution
    income_distribution = {}
    for persona in persona_data_list:
        income = persona.get('income_range', 'Unknown')
        income_distribution[income] = income_distribution.get(income, 0) + 1
    
    # Education distribution
    education_distribution = {}
    for persona in persona_data_list:
        education = persona.get('education', 'Unknown')
        education_distribution[education] = education_distribution.get(education, 0) + 1
    
    return {
        "age_distribution": age_ranges,
        "gender_distribution": gender_distribution,
        "income_distribution": income_distribution,
        "education_distribution": education_distribution
    }

def _calculate_demographic_coverage(persona_data_list):
    """Calculate demographic coverage metrics"""
    demographics = _calculate_demographic_distribution(persona_data_list)
    
    # Calculate coverage scores (how well distributed across categories)
    coverage_scores = {}
    
    for category, distribution in demographics.items():
        if distribution:
            total = sum(distribution.values())
            # Calculate entropy as a measure of distribution evenness
            entropy = 0.0
            for count in distribution.values():
                if count > 0:
                    p = count / total
                    entropy -= p * np.log2(p)
            
            # Normalize entropy by maximum possible entropy
            max_entropy = np.log2(len(distribution)) if len(distribution) > 1 else 1
            coverage_scores[category] = entropy / max_entropy if max_entropy > 0 else 0
    
    return coverage_scores

def _calculate_feature_importance(persona_data_list):
    """Calculate feature importance for clustering"""
    if len(persona_data_list) < 2:
        return {}
    
    # This is a simplified feature importance calculation
    # In a real implementation, you might use more sophisticated methods
    feature_names = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
    importance_scores = {}
    
    for feature in feature_names:
        values = []
        for persona in persona_data_list:
            personality = persona.get('personality', {})
            values.append(personality.get(feature, 0.5))
        
        # Use standard deviation as a proxy for importance
        importance_scores[feature] = float(np.std(values)) if values else 0.0
    
    return importance_scores

@app.on_event("startup")
async def startup_event():
    """Initialize core components on startup"""
    global hybrid_engine, evaluation_metrics, clustering_engine, distribution_matcher, file_storage
    global llm_persona_service, advanced_nlp_service, demographic_extraction_service
    global validation_service, bias_detection_service, confidence_scoring_service, data_adapter
    
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get AWS credentials from .env file
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
    
    # Validate AWS credentials are present
    if not aws_access_key_id or not aws_secret_access_key:
        raise ValueError("AWS credentials not found in .env file. Please check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
    
    # Set environment variables for boto3 (in case they weren't already set)
    os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key_id
    os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key
    os.environ["AWS_DEFAULT_REGION"] = aws_region
    
    # Get API keys for LLM services (not needed for Bedrock but keeping for fallback)
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    try:
        # Initialize storage manager
        storage_config = StorageConfig()
        storage_config.base_path = "./data/personas"
        storage_config.auto_create_dirs = True
        storage_config.use_compression = True
        file_storage = FileStorageManager(base_path=storage_config.base_path)
        
        # Initialize core components
        hybrid_engine = HybridPersonaEngine(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            storage_manager=file_storage,
            enable_gpu=False  # Set to True if GPU available
        )
        
        # Initialize advanced services
        logger.info("Initializing advanced LLM and NLP services...")
        
        # Initialize LLM Persona Service with Bedrock as preferred provider
        llm_persona_service = LLMPersonaService(
            anthropic_api_key=anthropic_api_key,
            openai_api_key=openai_api_key,
            aws_region=aws_region,
            preferred_provider="bedrock"
        )
        
        # Initialize Advanced NLP Service
        advanced_nlp_service = AdvancedNLPService()
        
        # Initialize Demographic Extraction Service
        demographic_extraction_service = DemographicExtractionService()
        
        # Initialize Validation Service
        validation_service = PersonaValidationService(llm_service=llm_persona_service)
        
        # Initialize Bias Detection Service
        bias_detection_service = BiasDetectionService()
        
        # Initialize Confidence Scoring Service
        confidence_scoring_service = ConfidenceScoringService()
        
        # Initialize Data Adapter
        data_adapter = ConfidenceDataAdapter()
        
        logger.info("Advanced services initialized successfully")
        evaluation_metrics = EvaluationMetrics()
        clustering_engine = ClusteringEngine()
        distribution_matcher = DistributionMatcher()
        
        # Perform health check
        health_status = await hybrid_engine.health_check()
        logger.info(f"System health check: {health_status['overall_status']}")
        
        logger.info("✅ Synthetic Persona Generation API initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize API components: {e}")
        raise

@app.get("/")
async def root():
    return {
        "message": "Synthetic Persona Generation API",
        "version": "1.0.0",
        "status": "active",
        "features": [
            "Hybrid Engine (Rule-based + LLM + Statistical)",
            "Distribution Matching",
            "Advanced Clustering Algorithms",
            "Comprehensive Evaluation Metrics",
            "Real-time Results Dashboard"
        ]
    }

@app.post("/api/personas/generate", response_model=GenerationResponse)
async def generate_personas(request: PersonaGenerationRequest):
    """
    Generate synthetic personas using the hybrid engine
    
    This endpoint combines rule-based sampling, LLM narrative generation (Claude 3.5 Sonnet),
    GAN/VAE diversity generation, and statistical distribution matching to create realistic personas.
    """
    try:
        if not hybrid_engine:
            raise HTTPException(status_code=503, detail="Hybrid engine not initialized")
        
        # DEBUG: Print incoming request data
        # Debug logging removed for production
        
        start_time = datetime.now()
        
        # Validate generation method
        try:
            generation_method = GenerationMethod(request.generation_method)
        except ValueError:
            valid_methods = [method.value for method in GenerationMethod]
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid generation method '{request.generation_method}'. Must be one of: {valid_methods}"
            )
        
        # Create generation configuration
        config = GenerationConfig(
            method=generation_method,
            sample_size=request.sample_size,
            quality_threshold=request.quality_threshold,
            enable_clustering=request.enable_clustering,
            distribution_matching=request.distribution_matching,
            target_clusters=request.target_clusters,
            demographic_constraints=request.demographic_constraints,
            psychographic_preferences=request.psychographic_preferences,
            behavioral_patterns=request.behavioral_patterns,
            industry_context=request.industry_context,
            use_case_context=request.use_case_context,
            export_format=request.export_format,
            validation_enabled=True,
            storage_enabled=True
        )
        
        # Create generation request
        gen_request = GenerationRequest(
            config=config,
            project_name=request.project_name,
            persona_name=request.persona_name,
            tags=request.tags,
            description=f"Generated {request.sample_size} personas using {request.generation_method} method"
        )
        
        # Generate personas using hybrid engine
        result = await hybrid_engine.generate_personas(gen_request)
        
        if not result.success:
            raise HTTPException(
                status_code=500, 
                detail=f"Generation failed: {'; '.join(result.errors or ['Unknown error'])}"
            )
        
        # Convert personas to response format
        persona_responses = []
        for i, persona in enumerate(result.personas):
            # Handle narrative field - convert PersonaNarrative object to string if needed
            narrative_data = persona.get("narrative")
            narrative_str = None
            if narrative_data:
                if isinstance(narrative_data, str):
                    narrative_str = narrative_data
                elif isinstance(narrative_data, dict):
                    # Convert PersonaNarrative dict to a readable string format
                    narrative_parts = []
                    if narrative_data.get("name"):
                        narrative_parts.append(f"Name: {narrative_data['name']}")
                    if narrative_data.get("background_story"):
                        narrative_parts.append(f"Background: {narrative_data['background_story']}")
                    if narrative_data.get("day_in_life"):
                        narrative_parts.append(f"Day in Life: {narrative_data['day_in_life']}")
                    if narrative_data.get("goals_and_motivations"):
                        narrative_parts.append(f"Goals: {narrative_data['goals_and_motivations']}")
                    if narrative_data.get("pain_points"):
                        narrative_parts.append(f"Pain Points: {narrative_data['pain_points']}")
                    if narrative_data.get("decision_making_process"):
                        narrative_parts.append(f"Decision Making: {narrative_data['decision_making_process']}")
                    if narrative_data.get("quote"):
                        narrative_parts.append(f"Quote: {narrative_data['quote']}")
                    narrative_str = "\n\n".join(narrative_parts) if narrative_parts else None
                else:
                    # Handle PersonaNarrative object with attributes
                    try:
                        narrative_parts = []
                        if hasattr(narrative_data, 'name') and narrative_data.name:
                            narrative_parts.append(f"Name: {narrative_data.name}")
                        if hasattr(narrative_data, 'background_story') and narrative_data.background_story:
                            narrative_parts.append(f"Background: {narrative_data.background_story}")
                        if hasattr(narrative_data, 'day_in_life') and narrative_data.day_in_life:
                            narrative_parts.append(f"Day in Life: {narrative_data.day_in_life}")
                        if hasattr(narrative_data, 'goals_and_motivations') and narrative_data.goals_and_motivations:
                            narrative_parts.append(f"Goals: {narrative_data.goals_and_motivations}")
                        if hasattr(narrative_data, 'pain_points') and narrative_data.pain_points:
                            narrative_parts.append(f"Pain Points: {narrative_data.pain_points}")
                        if hasattr(narrative_data, 'decision_making_process') and narrative_data.decision_making_process:
                            narrative_parts.append(f"Decision Making: {narrative_data.decision_making_process}")
                        if hasattr(narrative_data, 'quote') and narrative_data.quote:
                            narrative_parts.append(f"Quote: {narrative_data.quote}")
                        narrative_str = "\n\n".join(narrative_parts) if narrative_parts else None
                    except Exception as e:
                        logger.warning(f"Failed to convert narrative object to string: {e}")
                        narrative_str = str(narrative_data) if narrative_data else None
            
            persona_response = PersonaResponse(
                id=result.storage_ids[i] if result.storage_ids and i < len(result.storage_ids) else None,
                demographics=persona.get("demographics", {}),
                psychographics=persona.get("psychographics", {}),
                behavioral_patterns=persona.get("behavioral_patterns", {}),
                narrative=narrative_str,
                generation_method=persona.get("generation_method", request.generation_method),
                confidence_score=persona.get("confidence_score", 0.0),
                cluster_id=persona.get("cluster_id"),
                component_scores=persona.get("component_scores")
            )
            persona_responses.append(persona_response)
        
        return GenerationResponse(
            personas=persona_responses,
            generation_metadata=result.generation_metadata,
            quality_metrics=result.quality_metrics,
            clustering_results=result.clustering_results,
            distribution_analysis=result.distribution_analysis,
            storage_ids=result.storage_ids,
            export_paths=result.export_paths,
            execution_time=result.execution_time,
            success=result.success,
            message=f"Successfully generated {len(result.personas)} personas using {request.generation_method} method",
            warnings=result.warnings,
            errors=result.errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating personas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/api/personas/batch-generate", response_model=GenerationResponse)
async def batch_generate_personas(request: PersonaGenerationRequest):
    """
    Generate multiple personas in batch using the hybrid engine
    
    This endpoint efficiently generates large numbers of personas while maintaining
    statistical coherence and quality standards across the entire batch.
    Note: This is an alias for the main generation endpoint for backward compatibility.
    """
    # Redirect to main generation endpoint
    return await generate_personas(request)

@app.get("/api/dashboard/analytics/{persona_folder_name}")
async def get_persona_analytics(persona_folder_name: str):
    """
    Get comprehensive analytics for a specific persona folder
    
    Returns clustering analysis, similarity metrics, quality assessment,
    diversity metrics, and bias detection for personas in the specified folder.
    """
    try:
        if not file_storage:
            raise HTTPException(status_code=503, detail="File storage not initialized")
        
        # Load personas directly from filesystem folder
        import json
        import aiofiles
        from pathlib import Path
        
        personas_dir = os.path.join(file_storage.config.base_directory, file_storage.config.personas_directory)
        persona_folder_path = os.path.join(personas_dir, persona_folder_name)
        
        if not os.path.exists(persona_folder_path) or not os.path.isdir(persona_folder_path):
            raise HTTPException(status_code=404, detail=f"Persona folder '{persona_folder_name}' not found")
        
        # Load all JSON files from the folder
        persona_files = [f for f in os.listdir(persona_folder_path) if f.endswith('.json')]
        
        if not persona_files:
            raise HTTPException(status_code=404, detail=f"No personas found in folder '{persona_folder_name}'")
        
        # Load persona data from files
        persona_data_list = []
        for file_name in persona_files:
            file_path = os.path.join(persona_folder_path, file_name)
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    persona_file_data = json.loads(await f.read())
                    persona_data = persona_file_data.get('persona_data', {})
                    
                    # Flatten the data structure for analysis
                    flattened_data = {
                        'id': persona_file_data.get('id', file_name.replace('.json', '')),
                        'name': persona_data.get('demographics', {}).get('name', 'Unknown'),
                        'age': persona_data.get('demographics', {}).get('age', 0),
                        'gender': persona_data.get('demographics', {}).get('gender', 'Unknown'),
                        'income_range': persona_data.get('demographics', {}).get('income_range', 'Unknown'),
                        'education': persona_data.get('demographics', {}).get('education', 'Unknown'),
                        'location': persona_data.get('demographics', {}).get('location', {}),
                        'personality': persona_data.get('psychographics', {}).get('personality_traits', {}),
                        'values': persona_data.get('psychographics', {}).get('values', {}),
                        'lifestyle': persona_data.get('psychographics', {}).get('lifestyle', {}),
                        'quality_metrics': persona_file_data.get('quality_metrics', {})
                    }
                    persona_data_list.append(flattened_data)
            except Exception as e:
                logger.warning(f"Failed to load persona file {file_path}: {e}")
                continue
        
        if not persona_data_list:
            raise HTTPException(status_code=404, detail=f"No valid personas found in folder '{persona_folder_name}'")
        
        # Calculate analytics using the loaded persona data
        
        # Calculate analytics
        analytics_result = {
            "folder_name": persona_folder_name,
            "total_personas": len(persona_data_list),
            "relationship_analysis": _calculate_relationship_analysis(persona_data_list),
            "quality_assessment": _calculate_quality_assessment(persona_data_list),
            "diversity_metrics": _calculate_diversity_metrics(persona_data_list),
            "bias_indicators": _calculate_bias_indicators(persona_data_list),
            "demographic_distribution": _calculate_demographic_distribution(persona_data_list),
            "timestamp": datetime.now().isoformat()
        }
        
        return analytics_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating analytics for folder {persona_folder_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate analytics: {str(e)}")

@app.get("/api/dashboard/metrics")
async def get_dashboard_metrics():
    """
    Get comprehensive dashboard metrics for the persona generation system
    
    Returns real-time statistics about generation quality, clustering analysis,
    distribution coherence, and system performance metrics.
    """
    try:
        if not file_storage:
            raise HTTPException(status_code=503, detail="File storage not initialized")
        
        # Get storage statistics
        storage_stats = file_storage.get_storage_statistics()
        
        if storage_stats["personas"]["count"] == 0:
            return {
                "total_personas": 0,
                "quality_metrics": {},
                "clustering_metrics": {},
                "distribution_metrics": {},
                "system_health": {
                    "status": "ready",
                    "message": "No personas generated yet"
                },
                "storage_stats": storage_stats,
                "timestamp": datetime.now().isoformat()
            }
        
        # Load recent personas for analysis (limit to last 1000 for performance)
        recent_personas = await file_storage.load_personas(
            limit=1000,
            sort_by="created_at",
            sort_order="desc"
        )
        
        # Calculate quality metrics
        quality_metrics = {}
        if evaluation_metrics and recent_personas:
            try:
                quality_report = await evaluation_metrics.generate_quality_report(recent_personas)
                quality_metrics = {
                    "average_completeness": quality_report.get("average_completeness", 0),
                    "average_consistency": quality_report.get("average_consistency", 0),
                    "average_realism": quality_report.get("average_realism", 0),
                    "overall_quality": quality_report.get("overall_quality", 0)
                }
            except Exception as e:
                logger.warning(f"Failed to calculate quality metrics: {e}")
                quality_metrics = {"error": "Quality metrics unavailable"}
        
        # Perform clustering analysis
        clustering_metrics = {}
        if clustering_engine and recent_personas and len(recent_personas) > 2:
            try:
                clustering_result = await clustering_engine.cluster_personas(
                    recent_personas,
                    algorithm="kmeans",
                    n_clusters=min(8, len(recent_personas) // 10 + 2)
                )
                clustering_metrics = {
                    "optimal_clusters": clustering_result.get("n_clusters", 0),
                    "silhouette_score": clustering_result.get("silhouette_score", 0),
                    "cluster_distribution": clustering_result.get("cluster_sizes", [])
                }
            except Exception as e:
                logger.warning(f"Failed to calculate clustering metrics: {e}")
                clustering_metrics = {"error": "Clustering metrics unavailable"}
        
        # Calculate distribution coherence
        distribution_metrics = {}
        if distribution_matcher and recent_personas:
            try:
                distribution_analysis = await distribution_matcher.analyze_distributions(recent_personas)
                distribution_metrics = {
                    "demographic_coherence": distribution_analysis.get("demographic_score", 0),
                    "statistical_validity": distribution_analysis.get("statistical_score", 0),
                    "distribution_quality": distribution_analysis.get("overall_score", 0)
                }
            except Exception as e:
                logger.warning(f"Failed to calculate distribution metrics: {e}")
                distribution_metrics = {"error": "Distribution metrics unavailable"}
        
        # System health check
        system_health = {
            "status": "operational",
            "hybrid_engine": "ready" if hybrid_engine else "not_initialized",
            "llm_connection": "connected" if hybrid_engine and hasattr(hybrid_engine, 'llm_engine') else "unknown",
            "storage_status": "healthy",
            "last_generation": storage_stats.get("last_updated"),
            "total_storage_size": storage_stats.get("total_size_mb", 0)
        }
        
        return {
            "total_personas": storage_stats["personas"]["count"],
            "quality_metrics": quality_metrics,
            "clustering_metrics": clustering_metrics,
            "distribution_metrics": distribution_metrics,
            "system_health": system_health,
            "storage_stats": storage_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")

@app.get("/api/personas")
async def get_personas(
    limit: int = 50, 
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    search: str = None,
    project_name: str = None
):
    """
    Retrieve stored personas with pagination, filtering, and sorting
    
    Supports advanced filtering, sorting, and pagination for efficient data retrieval
    from the local file storage system.
    """
    try:
        if not file_storage:
            raise HTTPException(status_code=503, detail="File storage not initialized")
        
        # Build search criteria
        search_criteria = {}
        if search:
            search_criteria["search_term"] = search
        if project_name:
            search_criteria["project_name"] = project_name
        
        # Load personas with filtering and pagination
        personas = await file_storage.load_personas(
            limit=min(limit, 1000),  # Cap at 1000 for performance
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            search_criteria=search_criteria
        )
        
        # Get total count for pagination
        storage_stats = file_storage.get_storage_statistics()
        total_count = storage_stats["personas"]["count"]
        
        # Convert personas to response format
        persona_responses = []
        for persona in personas:
            persona_data = persona.persona_data
            persona_response = PersonaResponse(
                id=persona.id,
                demographics=persona_data.get("demographics", {}),
                psychographics=persona_data.get("psychographics", {}),
                behavioral_patterns=persona_data.get("behavioral_patterns", {}),
                narrative=persona_data.get("narrative"),
                generation_method=persona.generation_method,
                confidence_score=persona_data.get("confidence_score", 0.0),
                cluster_id=persona.cluster_assignment,
                component_scores=persona_data.get("component_scores")
            )
            persona_responses.append(persona_response)
        
        return {
            "personas": [persona.dict() for persona in persona_responses],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "has_more": offset + limit < total_count,
                "current_page": (offset // limit) + 1,
                "total_pages": (total_count + limit - 1) // limit
            },
            "filters": {
                "sort_by": sort_by,
                "sort_order": sort_order,
                "search": search,
                "project_name": project_name
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving personas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve personas: {str(e)}")

@app.get("/api/personas/{persona_id}", response_model=PersonaResponse)
async def get_persona(persona_id: str):
    """
    Retrieve a specific persona by ID
    
    Returns detailed persona information including generation metadata,
    quality scores, and clustering information.
    """
    try:
        if not file_storage:
            raise HTTPException(status_code=503, detail="File storage not initialized")
        
        # Load persona by ID
        persona_record = await file_storage.load_persona(persona_id)
        
        if not persona_record:
            raise HTTPException(status_code=404, detail=f"Persona with ID '{persona_id}' not found")
        
        # Convert to response format
        persona_data = persona_record.persona_data
        
        # Handle narrative field - convert PersonaNarrative object to string if needed
        narrative_data = persona_data.get("narrative")
        narrative_str = None
        if narrative_data:
            if isinstance(narrative_data, str):
                narrative_str = narrative_data
            elif isinstance(narrative_data, dict):
                # Convert PersonaNarrative dict to a readable string format
                narrative_parts = []
                if narrative_data.get("name"):
                    narrative_parts.append(f"Name: {narrative_data['name']}")
                if narrative_data.get("background_story"):
                    narrative_parts.append(f"Background: {narrative_data['background_story']}")
                if narrative_data.get("day_in_life"):
                    narrative_parts.append(f"Day in Life: {narrative_data['day_in_life']}")
                if narrative_data.get("goals_and_motivations"):
                    narrative_parts.append(f"Goals: {narrative_data['goals_and_motivations']}")
                if narrative_data.get("pain_points"):
                    narrative_parts.append(f"Pain Points: {narrative_data['pain_points']}")
                if narrative_data.get("decision_making_process"):
                    narrative_parts.append(f"Decision Making: {narrative_data['decision_making_process']}")
                if narrative_data.get("quote"):
                    narrative_parts.append(f"Quote: {narrative_data['quote']}")
                narrative_str = "\n\n".join(narrative_parts) if narrative_parts else None
            else:
                # Handle PersonaNarrative object with attributes
                try:
                    narrative_parts = []
                    if hasattr(narrative_data, 'name') and narrative_data.name:
                        narrative_parts.append(f"Name: {narrative_data.name}")
                    if hasattr(narrative_data, 'background_story') and narrative_data.background_story:
                        narrative_parts.append(f"Background: {narrative_data.background_story}")
                    if hasattr(narrative_data, 'day_in_life') and narrative_data.day_in_life:
                        narrative_parts.append(f"Day in Life: {narrative_data.day_in_life}")
                    if hasattr(narrative_data, 'goals_and_motivations') and narrative_data.goals_and_motivations:
                        narrative_parts.append(f"Goals: {narrative_data.goals_and_motivations}")
                    if hasattr(narrative_data, 'pain_points') and narrative_data.pain_points:
                        narrative_parts.append(f"Pain Points: {narrative_data.pain_points}")
                    if hasattr(narrative_data, 'decision_making_process') and narrative_data.decision_making_process:
                        narrative_parts.append(f"Decision Making: {narrative_data.decision_making_process}")
                    if hasattr(narrative_data, 'quote') and narrative_data.quote:
                        narrative_parts.append(f"Quote: {narrative_data.quote}")
                    narrative_str = "\n\n".join(narrative_parts) if narrative_parts else None
                except Exception as e:
                    logger.warning(f"Failed to convert narrative object to string: {e}")
                    narrative_str = str(narrative_data) if narrative_data else None
        
        persona_response = PersonaResponse(
            id=persona_record.id,
            demographics=persona_data.get("demographics", {}),
            psychographics=persona_data.get("psychographics", {}),
            behavioral_patterns=persona_data.get("behavioral_patterns", {}),
            narrative=narrative_str,
            generation_method=persona_record.generation_method,
            confidence_score=persona_data.get("confidence_score", 0.0),
            cluster_id=persona_record.cluster_assignment,
            component_scores=persona_data.get("component_scores")
        )
        
        return persona_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving persona {persona_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve persona: {str(e)}")









@app.get("/api/persona-names")
async def get_persona_names():
    """
    Get all unique persona names in the system by reading folder names
    
    Returns a list of all persona names that have been generated,
    useful for browsing personas by name rather than session.
    """
    try:
        if not file_storage:
            raise HTTPException(status_code=503, detail="File storage not initialized")
        
        # Get persona folder names directly from filesystem
        import os
        personas_dir = os.path.join(file_storage.config.base_directory, file_storage.config.personas_directory)
        persona_folders = []
        
        if os.path.exists(personas_dir):
            for item in os.listdir(personas_dir):
                item_path = os.path.join(personas_dir, item)
                # Only include directories, exclude index.json and other files
                if os.path.isdir(item_path) and not item.startswith('.'):
                    # Count personas in this folder
                    persona_files = [f for f in os.listdir(item_path) if f.endswith('.json')]
                    persona_folders.append({
                        "name": item,
                        "persona_count": len(persona_files),
                        "folder_path": item_path
                    })
        
        # Sort by name
        persona_folders.sort(key=lambda x: x["name"])
        
        return {
            "persona_folders": persona_folders,
            "total_folders": len(persona_folders),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving persona folder names: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve persona folder names: {str(e)}")

@app.get("/api/personas/by-name/{persona_name}")
async def get_personas_by_name(persona_name: str):
    """
    Get all personas with a specific name
    
    Retrieves all persona variations that share the same name,
    useful for comparing different generations of the same persona.
    """
    try:
        if not file_storage:
            raise HTTPException(status_code=503, detail="File storage not initialized")
        
        personas = await file_storage.load_personas_by_name(persona_name)
        
        if not personas:
            raise HTTPException(status_code=404, detail=f"No personas found with name '{persona_name}'")
        
        # Convert to response format
        persona_responses = []
        for persona in personas:
            persona_data = persona.persona_data
            
            # Handle narrative field - convert PersonaNarrative object to string if needed
            narrative_data = persona_data.get("narrative")
            narrative_str = None
            if narrative_data:
                if isinstance(narrative_data, str):
                    narrative_str = narrative_data
                elif isinstance(narrative_data, dict):
                    # Convert PersonaNarrative dict to a readable string format
                    narrative_parts = []
                    if narrative_data.get("name"):
                        narrative_parts.append(f"Name: {narrative_data['name']}")
                    if narrative_data.get("background_story"):
                        narrative_parts.append(f"Background: {narrative_data['background_story']}")
                    if narrative_data.get("day_in_life"):
                        narrative_parts.append(f"Day in Life: {narrative_data['day_in_life']}")
                    if narrative_data.get("goals_and_motivations"):
                        narrative_parts.append(f"Goals: {narrative_data['goals_and_motivations']}")
                    if narrative_data.get("pain_points"):
                        narrative_parts.append(f"Pain Points: {narrative_data['pain_points']}")
                    if narrative_data.get("decision_making_process"):
                        narrative_parts.append(f"Decision Making: {narrative_data['decision_making_process']}")
                    if narrative_data.get("quote"):
                        narrative_parts.append(f"Quote: {narrative_data['quote']}")
                    narrative_str = "\n\n".join(narrative_parts) if narrative_parts else None
                else:
                    # Handle PersonaNarrative object with attributes
                    try:
                        narrative_parts = []
                        if hasattr(narrative_data, 'name') and narrative_data.name:
                            narrative_parts.append(f"Name: {narrative_data.name}")
                        if hasattr(narrative_data, 'background_story') and narrative_data.background_story:
                            narrative_parts.append(f"Background: {narrative_data.background_story}")
                        if hasattr(narrative_data, 'day_in_life') and narrative_data.day_in_life:
                            narrative_parts.append(f"Day in Life: {narrative_data.day_in_life}")
                        if hasattr(narrative_data, 'goals_and_motivations') and narrative_data.goals_and_motivations:
                            narrative_parts.append(f"Goals: {narrative_data.goals_and_motivations}")
                        if hasattr(narrative_data, 'pain_points') and narrative_data.pain_points:
                            narrative_parts.append(f"Pain Points: {narrative_data.pain_points}")
                        if hasattr(narrative_data, 'decision_making_process') and narrative_data.decision_making_process:
                            narrative_parts.append(f"Decision Making: {narrative_data.decision_making_process}")
                        if hasattr(narrative_data, 'quote') and narrative_data.quote:
                            narrative_parts.append(f"Quote: {narrative_data.quote}")
                        narrative_str = "\n\n".join(narrative_parts) if narrative_parts else None
                    except Exception as e:
                        logger.warning(f"Failed to convert narrative object to string: {e}")
                        narrative_str = str(narrative_data) if narrative_data else None
            
            persona_response = PersonaResponse(
                id=persona.persona_id,
                demographics=persona_data.get("demographics", {}),
                psychographics=persona_data.get("psychographics", {}),
                behavioral_patterns=persona_data.get("behavioral_patterns", {}),
                narrative=narrative_str,
                generation_method=persona_data.get("generation_method", "unknown"),
                confidence_score=persona_data.get("confidence_score", 0.0),
                cluster_id=persona_data.get("cluster_id"),
                component_scores=persona_data.get("component_scores")
            )
            persona_responses.append(persona_response)
        
        return {
            "persona_name": persona_name,
            "personas": [persona.dict() for persona in persona_responses],
            "persona_count": len(persona_responses),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving personas for name {persona_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve personas by name: {str(e)}")

@app.delete("/api/personas/by-name/{persona_name}")
async def delete_personas_by_name(persona_name: str):
    """
    Delete all personas with a specific name
    
    Permanently removes all persona variations that share the same name.
    Use with caution as this operation cannot be undone.
    """
    try:
        if not file_storage:
            raise HTTPException(status_code=503, detail="File storage not initialized")
        
        success = file_storage.delete_personas_by_name(persona_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"No personas found with name '{persona_name}' or could not be deleted")
        
        return {
            "message": f"All personas with name '{persona_name}' have been deleted",
            "persona_name": persona_name,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting personas with name {persona_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete personas by name: {str(e)}")

@app.post("/api/personas/by-name/{persona_name}/analyze")
async def analyze_personas_by_name(persona_name: str, n_clusters: int = 5):
    """
    Analyze personas with a specific name using K-means clustering and bias detection
    
    Performs clustering analysis and bias detection on all personas that share the same name.
    """
    try:
        if not file_storage:
            raise HTTPException(status_code=503, detail="File storage not initialized")
        
        if not clustering_engine:
            raise HTTPException(status_code=503, detail="Clustering engine not initialized")
        
        # Load personas by name
        personas = await file_storage.load_personas_by_name(persona_name)
        
        if not personas:
            raise HTTPException(status_code=404, detail=f"No personas found with name '{persona_name}'")
        
        if len(personas) < 2:
            raise HTTPException(status_code=400, detail="At least 2 personas are required for analysis")
        
        # Convert personas to the format expected by clustering engine
        personas_data = []
        for persona in personas:
            persona_dict = persona.persona_data.copy()
            persona_dict['persona_id'] = persona.id
            personas_data.append(persona_dict)
        
        # Perform clustering analysis
        clustering_results = await clustering_engine.perform_clustering(
            personas_data, 
            n_clusters=min(n_clusters, len(personas_data))
        )
        
        # Calculate bias metrics
        bias_metrics = {}
        
        # Gender distribution analysis
        genders = [p.get('demographics', {}).get('gender', 'unknown') for p in personas_data]
        gender_counts = {}
        for gender in genders:
            gender_counts[gender] = gender_counts.get(gender, 0) + 1
        
        total_personas = len(personas_data)
        gender_distribution = {k: (v / total_personas) * 100 for k, v in gender_counts.items()}
        
        # Calculate gender bias score (deviation from 50/50 split)
        if 'male' in gender_distribution and 'female' in gender_distribution:
            male_pct = gender_distribution.get('male', 0)
            female_pct = gender_distribution.get('female', 0)
            gender_bias_score = abs(male_pct - female_pct) / 100
        else:
            gender_bias_score = 1.0  # Maximum bias if only one gender
        
        bias_metrics['gender_distribution'] = gender_distribution
        bias_metrics['gender_bias_score'] = gender_bias_score
        
        # Age distribution analysis
        ages = []
        for p in personas_data:
            age_str = p.get('demographics', {}).get('age', '')
            if isinstance(age_str, str) and '-' in age_str:
                # Handle age ranges like "25-34"
                age_parts = age_str.split('-')
                if len(age_parts) == 2:
                    try:
                        avg_age = (int(age_parts[0]) + int(age_parts[1])) / 2
                        ages.append(avg_age)
                    except ValueError:
                        pass
            elif isinstance(age_str, (int, float)):
                ages.append(float(age_str))
        
        if ages:
            ages_array = np.array(ages)
            bias_metrics['age_distribution'] = {
                'mean': float(np.mean(ages_array)),
                'std': float(np.std(ages_array)),
                'min': float(np.min(ages_array)),
                'max': float(np.max(ages_array))
            }
        
        # Income distribution analysis
        incomes = [p.get('demographics', {}).get('income', 'unknown') for p in personas_data]
        income_counts = {}
        for income in incomes:
            income_counts[income] = income_counts.get(income, 0) + 1
        income_distribution = {k: (v / total_personas) * 100 for k, v in income_counts.items()}
        bias_metrics['income_distribution'] = income_distribution
        
        # Education distribution analysis
        educations = [p.get('demographics', {}).get('education', 'unknown') for p in personas_data]
        education_counts = {}
        for education in educations:
            education_counts[education] = education_counts.get(education, 0) + 1
        education_distribution = {k: (v / total_personas) * 100 for k, v in education_counts.items()}
        bias_metrics['education_distribution'] = education_distribution
        
        # Location distribution analysis
        locations = [p.get('demographics', {}).get('location', 'unknown') for p in personas_data]
        location_counts = {}
        for location in locations:
            location_counts[location] = location_counts.get(location, 0) + 1
        location_distribution = {k: (v / total_personas) * 100 for k, v in location_counts.items()}
        bias_metrics['location_distribution'] = location_distribution
        
        # Calculate diversity metrics
        diversity_metrics = {
            'total_personas': total_personas,
            'unique_clusters': clustering_results.get('n_clusters', 0),
            'silhouette_score': clustering_results.get('silhouette_score', 0.0),
            'inertia': clustering_results.get('inertia', 0.0),
            'pca_explained_variance': clustering_results.get('pca_explained_variance', [])
        }
        
        return {
            'persona_name': persona_name,
            'analysis_timestamp': datetime.now().isoformat(),
            'clustering': clustering_results,
            'bias_metrics': bias_metrics,
            'diversity_metrics': diversity_metrics,
            'feature_importance': clustering_results.get('feature_importance', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing personas with name {persona_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze personas by name: {str(e)}")

# Text-to-Persona Processing Functions
class TextProcessor:
    """Text processing pipeline for persona extraction"""
    
    def __init__(self):
        # Initialize basic NLP processing without spacy
        self.nlp = None
        logger.info("Using basic NLP processing with TextBlob and NLTK")
        
        # Initialize NLTK data with SSL handling
        import ssl
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context
        
        import nltk
        nltk_packages = [('tokenizers/punkt', 'punkt'), ('corpora/stopwords', 'stopwords')]
        
        for data_path, package_name in nltk_packages:
            try:
                nltk.data.find(data_path)
                logger.info(f"NLTK package {package_name} already available")
            except LookupError:
                try:
                    logger.info(f"Downloading NLTK package: {package_name}")
                    nltk.download(package_name, quiet=True)
                    logger.info(f"Successfully downloaded NLTK package: {package_name}")
                except Exception as e:
                    logger.warning(f"Failed to download NLTK package {package_name}: {e}")
                    logger.warning("Some features may be limited without NLTK data.")
    
    def preprocess_text(self, text: str) -> Dict[str, Any]:
        """Clean and preprocess input text"""
        # Basic cleaning
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        cleaned_text = re.sub(r'[^\w\s.,!?;:-]', '', cleaned_text)
        
        # Segmentation
        sentences = self._segment_sentences(cleaned_text)
        
        # Basic statistics
        word_count = len(cleaned_text.split())
        sentence_count = len(sentences)
        
        return {
            "original_text": text,
            "cleaned_text": cleaned_text,
            "sentences": sentences,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": word_count / max(sentence_count, 1)
        }
    
    def _segment_sentences(self, text: str) -> List[str]:
        """Segment text into sentences"""
        if self.nlp:
            doc = self.nlp(text)
            return [sent.text.strip() for sent in doc.sents]
        else:
            # Fallback to basic sentence splitting
            return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text"""
        entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "dates": [],
            "money": [],
            "products": []
        }
        
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ["PERSON"]:
                    entities["persons"].append(ent.text)
                elif ent.label_ in ["ORG"]:
                    entities["organizations"].append(ent.text)
                elif ent.label_ in ["GPE", "LOC"]:
                    entities["locations"].append(ent.text)
                elif ent.label_ in ["DATE", "TIME"]:
                    entities["dates"].append(ent.text)
                elif ent.label_ in ["MONEY"]:
                    entities["money"].append(ent.text)
                elif ent.label_ in ["PRODUCT"]:
                    entities["products"].append(ent.text)
        
        return entities
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text"""
        blob = TextBlob(text)
        return {
            "polarity": blob.sentiment.polarity,  # -1 to 1
            "subjectivity": blob.sentiment.subjectivity  # 0 to 1
        }
    
    def extract_topics(self, text: str, num_topics: int = 5) -> List[str]:
        """Extract key topics using TF-IDF"""
        try:
            # Simple topic extraction using TF-IDF
            sentences = self._segment_sentences(text)
            if len(sentences) < 2:
                return []
            
            vectorizer = TfidfVectorizer(max_features=100, stop_words='english', ngram_range=(1, 2))
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            
            # Get top scoring terms
            top_indices = scores.argsort()[-num_topics:][::-1]
            topics = [feature_names[i] for i in top_indices if scores[i] > 0]
            
            return topics
        except Exception as e:
            logger.warning(f"Topic extraction failed: {e}")
            return []
    
    def extract_demographics(self, text: str, entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """Extract demographic information from text"""
        demographics = {
            "age_range": self._infer_age(text),
            "gender": self._infer_gender(text),
            "location": self._infer_location(text, entities),
            "occupation": self._infer_occupation(text),
            "income_range": self._infer_income(text),
            "education": self._infer_education(text),
            "family_status": self._infer_family_status(text)
        }
        return demographics
    
    def _infer_age(self, text: str) -> str:
        """Infer age range from text patterns"""
        age_patterns = {
            r'\b(?:teen|teenager|adolescent|high school)\b': "13-19",
            r'\b(?:college|university|student|young adult)\b': "18-25",
            r'\b(?:early career|twenties|20s)\b': "20-29",
            r'\b(?:thirties|30s|established career)\b': "30-39",
            r'\b(?:forties|40s|mid-career|middle-aged)\b': "40-49",
            r'\b(?:fifties|50s|senior|experienced)\b': "50-59",
            r'\b(?:sixties|60s|retirement|retired|elder)\b': "60+"
        }
        
        for pattern, age_range in age_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return age_range
        
        return "unknown"
    
    def _infer_gender(self, text: str) -> str:
        """Infer gender from text patterns"""
        male_indicators = r'\b(?:he|him|his|man|male|father|dad|husband|boyfriend|son|brother|guy)\b'
        female_indicators = r'\b(?:she|her|hers|woman|female|mother|mom|wife|girlfriend|daughter|sister|lady)\b'
        
        male_count = len(re.findall(male_indicators, text, re.IGNORECASE))
        female_count = len(re.findall(female_indicators, text, re.IGNORECASE))
        
        if male_count > female_count:
            return "male"
        elif female_count > male_count:
            return "female"
        else:
            return "non-binary"
    
    def _infer_location(self, text: str, entities: Dict[str, List[str]]) -> str:
        """Infer location from entities and text patterns"""
        if entities["locations"]:
            return entities["locations"][0]  # Return first location found
        
        location_patterns = {
            r'\b(?:urban|city|downtown|metropolitan)\b': "urban",
            r'\b(?:suburban|suburbs|residential)\b': "suburban",
            r'\b(?:rural|countryside|farm|village)\b': "rural"
        }
        
        for pattern, location_type in location_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return location_type
        
        return "unknown"
    
    def _infer_occupation(self, text: str) -> str:
        """Infer occupation from text patterns"""
        occupation_patterns = {
            r'\b(?:doctor|physician|nurse|medical|healthcare)\b': "healthcare professional",
            r'\b(?:teacher|professor|educator|academic)\b': "educator",
            r'\b(?:engineer|developer|programmer|software|tech)\b': "technology professional",
            r'\b(?:manager|executive|director|CEO|leadership)\b': "management",
            r'\b(?:artist|designer|creative|musician)\b': "creative professional",
            r'\b(?:lawyer|attorney|legal|law)\b': "legal professional",
            r'\b(?:student|studying|school|university)\b': "student",
            r'\b(?:retired|retirement|pension)\b': "retired"
        }
        
        for pattern, occupation in occupation_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return occupation
        
        return "unknown"
    
    def _infer_income(self, text: str) -> str:
        """Infer income range from text patterns"""
        income_patterns = {
            r'\b(?:low income|budget|affordable|cheap|struggling financially)\b': "$25k-$40k",
            r'\b(?:middle class|average income|moderate budget)\b': "$40k-$75k",
            r'\b(?:high income|wealthy|expensive|luxury|affluent)\b': "$75k-$150k",
            r'\b(?:very wealthy|rich|millionaire|high-end|premium)\b': "$150k+"
        }
        
        for pattern, income_range in income_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return income_range
        
        return "unknown"
    
    def _infer_education(self, text: str) -> str:
        """Infer education level from text patterns"""
        education_patterns = {
            r'\b(?:PhD|doctorate|doctoral|postdoc)\b': "doctorate",
            r'\b(?:master|MBA|graduate degree|masters)\b': "master's degree",
            r'\b(?:bachelor|college graduate|university degree|bachelors)\b': "bachelor's degree",
            r'\b(?:associate|community college|two-year)\b': "associate degree",
            r'\b(?:high school|diploma|GED)\b': "high school",
            r'\b(?:some college|partial|incomplete degree)\b': "some college"
        }
        
        for pattern, education in education_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return education
        
        return "unknown"
    
    def _infer_family_status(self, text: str) -> str:
        """Infer family status from text patterns"""
        family_patterns = {
            r'\b(?:married|spouse|husband|wife)\b': "married",
            r'\b(?:single|unmarried|dating|boyfriend|girlfriend)\b': "single",
            r'\b(?:divorced|separated|ex-spouse)\b': "divorced",
            r'\b(?:children|kids|parent|parenting|family)\b': "has children",
            r'\b(?:widowed|widow|widower)\b': "widowed"
        }
        
        for pattern, status in family_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return status
        
        return "unknown"

# Initialize text processor
text_processor = TextProcessor()

# Persona-to-Persona Processing Functions
class PersonaProcessor:
    """Persona-to-persona transformation pipeline"""
    
    def __init__(self):
        self.operation_types = {
            "merge": self._merge_personas,
            "variants": self._generate_variants,
            "evolution": self._evolve_personas,
            "mixing": self._mix_personas
        }
    
    async def process_personas(self, source_personas: List[Dict], operation_type: str, 
                             output_count: int, validation_strictness: str, 
                             advanced_settings: Dict) -> List[GeneratedPersonaP2P]:
        """Process source personas based on operation type"""
        
        if operation_type not in self.operation_types:
            raise ValueError(f"Unsupported operation type: {operation_type}")
        
        processor_func = self.operation_types[operation_type]
        return await processor_func(source_personas, output_count, validation_strictness, advanced_settings)
    
    async def _merge_personas(self, source_personas: List[Dict], output_count: int, 
                            validation_strictness: str, advanced_settings: Dict) -> List[GeneratedPersonaP2P]:
        """Merge multiple personas into new combined personas"""
        generated_personas = []
        
        for i in range(output_count):
            # Select random subset of source personas to merge
            merge_count = min(len(source_personas), random.randint(2, 4))
            selected_personas = random.sample(source_personas, merge_count)
            
            # Merge demographics (take most common values)
            merged_demographics = self._merge_demographics(selected_personas)
            
            # Merge psychographics (combine and deduplicate)
            merged_psychographics = self._merge_psychographics(selected_personas)
            
            # Merge behaviors (combine and weight by confidence)
            merged_behaviors = self._merge_behaviors(selected_personas)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_merge_confidence(selected_personas, validation_strictness)
            
            # Generate inheritance map
            inheritance_map = {
                "source_personas": [p.get("id", f"persona_{idx}") for idx, p in enumerate(selected_personas)],
                "demographic_sources": {k: self._find_demographic_source(k, v, selected_personas) for k, v in merged_demographics.items()},
                "trait_combinations": self._map_trait_combinations(selected_personas)
            }
            
            # Perform bias analysis
            bias_analysis = await self._analyze_persona_bias(merged_demographics, merged_psychographics, merged_behaviors)
            
            # Calculate detailed confidence scores
            detailed_confidence = await self._calculate_persona_confidence(
                merged_demographics, merged_psychographics, merged_behaviors,
                "merge", selected_personas
            )
            
            persona_id = hashlib.md5(f"merge_{i}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            # Combine all attributes
            attributes = {
                "demographics": merged_demographics,
                "psychographics": merged_psychographics,
                "behaviors": merged_behaviors,
                "confidence_scores": confidence_scores,
                "detailed_confidence": detailed_confidence
            }
            
            # Create operation metadata
            operation_metadata = {
                "validation_results": await self._validate_persona(merged_demographics, merged_psychographics, merged_behaviors, validation_strictness),
                "generation_log": [
                    f"Merged {len(selected_personas)} source personas",
                    f"Applied {validation_strictness} validation strictness",
                    f"Used attribute weights: {advanced_settings.get('attribute_weights', {})}"
                ],
                "processing_timestamp": datetime.now().isoformat()
            }
            
            persona = GeneratedPersonaP2P(
                id=persona_id,
                name=f"Merged Persona {i+1}",
                source_personas=[{"id": p.get("id", f"persona_{idx}"), "weight": 1.0/len(selected_personas)} for idx, p in enumerate(selected_personas)],
                generation_method="merge",
                attributes=attributes,
                inheritance_map=inheritance_map,
                quality_metrics=self._calculate_quality_metrics(merged_demographics, merged_psychographics, merged_behaviors),
                operation_metadata=operation_metadata,
                bias_analysis=bias_analysis
            )
            
            generated_personas.append(persona)
        
        return generated_personas
    
    async def _generate_variants(self, source_personas: List[Dict], output_count: int, 
                               validation_strictness: str, advanced_settings: Dict) -> List[GeneratedPersonaP2P]:
        """Generate variants of existing personas"""
        generated_personas = []
        mutation_intensity = advanced_settings.get("mutation_intensity", 0.3)
        
        for i in range(output_count):
            # Select a source persona to create variant from
            source_persona = random.choice(source_personas)
            
            # Create variant by mutating attributes
            variant_demographics = self._mutate_demographics(source_persona.get("demographics", {}), mutation_intensity)
            variant_psychographics = self._mutate_psychographics(source_persona.get("psychographics", {}), mutation_intensity)
            variant_behaviors = self._mutate_behaviors(source_persona.get("behaviors", {}), mutation_intensity)
            
            # Calculate confidence (variants typically have high confidence)
            confidence_scores = {
                "demographics": max(0.7, source_persona.get("confidence_scores", {}).get("demographics", 0.8) * (1 - mutation_intensity * 0.3)),
                "psychographics": max(0.7, source_persona.get("confidence_scores", {}).get("psychographics", 0.8) * (1 - mutation_intensity * 0.3)),
                "behaviors": max(0.7, source_persona.get("confidence_scores", {}).get("behaviors", 0.8) * (1 - mutation_intensity * 0.3))
            }
            
            inheritance_map = {
                "source_personas": [source_persona.get("id", "unknown")],
                "mutation_intensity": mutation_intensity,
                "changed_attributes": self._identify_changes(source_persona, variant_demographics, variant_psychographics, variant_behaviors)
            }
            
            persona_id = hashlib.md5(f"variant_{i}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            # Perform bias analysis
            bias_analysis = await self._analyze_persona_bias(variant_demographics, variant_psychographics, variant_behaviors)
            
            # Calculate detailed confidence scores
            detailed_confidence = await self._calculate_persona_confidence(
                variant_demographics, variant_psychographics, variant_behaviors,
                "variants", [source_persona]
            )
            
            # Prepare attributes dictionary
            attributes = {
                "demographics": variant_demographics,
                "psychographics": variant_psychographics,
                "behaviors": variant_behaviors,
                "confidence_scores": confidence_scores,
                "detailed_confidence": detailed_confidence
            }
            
            # Prepare operation metadata
            validation_results = await self._validate_persona(variant_demographics, variant_psychographics, variant_behaviors, validation_strictness)
            operation_metadata = {
                "validation_results": validation_results,
                "generation_log": [
                    f"Created variant from {source_persona.get('name', 'Unknown')}",
                    f"Applied mutation intensity: {mutation_intensity}",
                    f"Changed {len(inheritance_map['changed_attributes'])} attributes"
                ]
            }
            
            persona = GeneratedPersonaP2P(
                id=persona_id,
                name=f"Variant of {source_persona.get('name', 'Unknown')} #{i+1}",
                source_personas=[source_persona.get("id", "unknown")],
                generation_method="variants",
                attributes=attributes,
                inheritance_map=inheritance_map,
                quality_metrics=self._calculate_quality_metrics(variant_demographics, variant_psychographics, variant_behaviors),
                operation_metadata=operation_metadata,
                bias_analysis=bias_analysis
            )
            
            generated_personas.append(persona)
        
        return generated_personas
    
    async def _evolve_personas(self, source_personas: List[Dict], output_count: int, 
                             validation_strictness: str, advanced_settings: Dict) -> List[GeneratedPersonaP2P]:
        """Evolve personas based on scenario context"""
        generated_personas = []
        scenario_context = advanced_settings.get("scenario_context", "general evolution")
        
        for i in range(output_count):
            source_persona = random.choice(source_personas)
            
            # Evolve based on scenario context
            evolved_demographics = self._evolve_demographics(source_persona.get("demographics", {}), scenario_context)
            evolved_psychographics = self._evolve_psychographics(source_persona.get("psychographics", {}), scenario_context)
            evolved_behaviors = self._evolve_behaviors(source_persona.get("behaviors", {}), scenario_context)
            
            confidence_scores = {
                "demographics": 0.75,
                "psychographics": 0.8,
                "behaviors": 0.85  # Behaviors often change most in evolution
            }
            
            inheritance_map = {
                "source_personas": [source_persona.get("id", "unknown")],
                "evolution_context": scenario_context,
                "evolution_factors": self._identify_evolution_factors(scenario_context)
            }
            
            persona_id = hashlib.md5(f"evolved_{i}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            # Perform bias analysis
            bias_analysis = await self._analyze_persona_bias(evolved_demographics, evolved_psychographics, evolved_behaviors)
            
            # Calculate detailed confidence scores
            detailed_confidence = await self._calculate_persona_confidence(
                evolved_demographics, evolved_psychographics, evolved_behaviors,
                "evolution", [source_persona]
            )
            
            # Prepare attributes dictionary
            attributes = {
                "demographics": evolved_demographics,
                "psychographics": evolved_psychographics,
                "behaviors": evolved_behaviors,
                "confidence_scores": confidence_scores,
                "detailed_confidence": detailed_confidence
            }
            
            # Prepare operation metadata
            validation_results = await self._validate_persona(evolved_demographics, evolved_psychographics, evolved_behaviors, validation_strictness)
            operation_metadata = {
                "validation_results": validation_results,
                "generation_log": [
                    f"Evolved from {source_persona.get('name', 'Unknown')}",
                    f"Evolution context: {scenario_context}",
                    f"Applied evolution factors: {inheritance_map['evolution_factors']}"
                ]
            }
            
            persona = GeneratedPersonaP2P(
                id=persona_id,
                name=f"Evolved {source_persona.get('name', 'Unknown')} #{i+1}",
                source_personas=[source_persona.get("id", "unknown")],
                generation_method="evolution",
                attributes=attributes,
                inheritance_map=inheritance_map,
                quality_metrics=self._calculate_quality_metrics(evolved_demographics, evolved_psychographics, evolved_behaviors),
                operation_metadata=operation_metadata,
                bias_analysis=bias_analysis
            )
            
            generated_personas.append(persona)
        
        return generated_personas
    
    async def _mix_personas(self, source_personas: List[Dict], output_count: int, 
                          validation_strictness: str, advanced_settings: Dict) -> List[GeneratedPersonaP2P]:
        """Mix personas using weighted attribute combination"""
        generated_personas = []
        attribute_weights = advanced_settings.get("attribute_weights", {"demographics": 0.4, "psychographics": 0.4, "behaviors": 0.2})
        
        for i in range(output_count):
            # Select 2-3 personas to mix
            mix_count = min(len(source_personas), random.randint(2, 3))
            selected_personas = random.sample(source_personas, mix_count)
            
            # Mix attributes based on weights
            mixed_demographics = self._weighted_mix_demographics(selected_personas, attribute_weights.get("demographics", 0.4))
            mixed_psychographics = self._weighted_mix_psychographics(selected_personas, attribute_weights.get("psychographics", 0.4))
            mixed_behaviors = self._weighted_mix_behaviors(selected_personas, attribute_weights.get("behaviors", 0.2))
            
            inheritance_map = {
                "source_personas": [p.get("id", f"persona_{idx}") for idx, p in enumerate(selected_personas)],
                "mixing_weights": attribute_weights,
                "dominant_source": self._identify_dominant_source(selected_personas, attribute_weights)
            }
            
            persona_id = hashlib.md5(f"mixed_{i}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            # Perform bias analysis
            bias_analysis = await self._analyze_persona_bias(mixed_demographics, mixed_psychographics, mixed_behaviors)
            
            # Calculate detailed confidence scores
            detailed_confidence = await self._calculate_persona_confidence(
                mixed_demographics, mixed_psychographics, mixed_behaviors, 
                "mixing", selected_personas
            )
            
            # Create attributes dictionary
            attributes = {
                "demographics": mixed_demographics,
                "psychographics": mixed_psychographics,
                "behaviors": mixed_behaviors,
                "confidence_scores": detailed_confidence.get("confidence_scores", {"demographics": 0.7, "psychographics": 0.75, "behaviors": 0.7}),
                "detailed_confidence": detailed_confidence
            }
            
            # Create operation metadata
            validation_results = await self._validate_persona(mixed_demographics, mixed_psychographics, mixed_behaviors, validation_strictness)
            operation_metadata = {
                "validation_results": validation_results,
                "generation_log": [
                    f"Mixed {len(selected_personas)} source personas",
                    f"Applied attribute weights: {attribute_weights}",
                    f"Dominant source: {inheritance_map['dominant_source']}"
                ]
            }
            
            persona = GeneratedPersonaP2P(
                id=persona_id,
                name=f"Mixed Persona {i+1}",
                source_personas=[p.get("id", f"persona_{idx}") for idx, p in enumerate(selected_personas)],
                generation_method="mixing",
                attributes=attributes,
                inheritance_map=inheritance_map,
                quality_metrics=self._calculate_quality_metrics(mixed_demographics, mixed_psychographics, mixed_behaviors),
                operation_metadata=operation_metadata,
                bias_analysis=bias_analysis
            )
            
            generated_personas.append(persona)
        
        return generated_personas
    
    # Helper methods for persona processing
    def _merge_demographics(self, personas: List[Dict]) -> Dict[str, Any]:
        """Merge demographic data from multiple personas"""
        demographics = {}
        for key in ["age_range", "gender", "location", "occupation", "income_range", "education", "family_status"]:
            values = [p.get("demographics", {}).get(key) for p in personas if p.get("demographics", {}).get(key)]
            if values:
                # Take most common value
                demographics[key] = max(set(values), key=values.count)
            else:
                demographics[key] = "unknown"
        return demographics
    
    def _merge_psychographics(self, personas: List[Dict]) -> Dict[str, Any]:
        """Merge psychographic data from multiple personas"""
        psychographics = {"interests": [], "values": [], "personality_traits": [], "lifestyle": [], "motivations": []}
        
        for persona in personas:
            psych_data = persona.get("psychographics", {})
            for key in psychographics.keys():
                if key in psych_data and isinstance(psych_data[key], list):
                    psychographics[key].extend(psych_data[key])
        
        # Deduplicate and limit
        for key in psychographics.keys():
            psychographics[key] = list(set(psychographics[key]))[:5]
        
        return psychographics
    
    def _merge_behaviors(self, personas: List[Dict]) -> Dict[str, Any]:
        """Merge behavioral data from multiple personas"""
        behaviors = {"shopping_habits": [], "communication_preferences": [], "decision_factors": [], "media_consumption": [], "technology_usage": []}
        
        for persona in personas:
            behavior_data = persona.get("behaviors", {})
            for key in behaviors.keys():
                if key in behavior_data and isinstance(behavior_data[key], list):
                    behaviors[key].extend(behavior_data[key])
        
        # Deduplicate and limit
        for key in behaviors.keys():
            behaviors[key] = list(set(behaviors[key]))[:5]
        
        return behaviors
    
    def _calculate_merge_confidence(self, personas: List[Dict], validation_strictness: str) -> Dict[str, float]:
        """Calculate confidence scores for merged persona"""
        base_confidence = 0.7 if validation_strictness == "strict" else 0.8
        
        # Average confidence from source personas
        avg_demo_conf = float(np.mean([p.get("confidence_scores", {}).get("demographics", 0.5) for p in personas]))
        avg_psych_conf = float(np.mean([p.get("confidence_scores", {}).get("psychographics", 0.5) for p in personas]))
        avg_behav_conf = float(np.mean([p.get("confidence_scores", {}).get("behaviors", 0.5) for p in personas]))
        
        return {
            "demographics": min(base_confidence, avg_demo_conf),
            "psychographics": min(base_confidence, avg_psych_conf),
            "behaviors": min(base_confidence, avg_behav_conf)
        }
    
    def _mutate_demographics(self, demographics: Dict, intensity: float) -> Dict[str, Any]:
        """Mutate demographic attributes based on intensity"""
        mutated = demographics.copy()
        
        # Define mutation options for each demographic field
        mutations = {
            "age_range": ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"],
            "gender": ["male", "female", "non-binary"],
            "location": ["urban", "suburban", "rural"],
            "occupation": ["professional", "student", "retired", "entrepreneur", "creative"],
            "income_range": ["$25k-$40k", "$40k-$75k", "$75k-$150k", "$150k+"],
            "education": ["high school", "some college", "bachelor's degree", "master's degree", "doctorate"],
            "family_status": ["single", "married", "divorced", "has children"]
        }
        
        for key, options in mutations.items():
            if random.random() < intensity and key in mutated:
                mutated[key] = random.choice(options)
        
        return mutated
    
    def _mutate_psychographics(self, psychographics: Dict, intensity: float) -> Dict[str, Any]:
        """Mutate psychographic attributes"""
        mutated = {k: v.copy() if isinstance(v, list) else v for k, v in psychographics.items()}
        
        mutation_options = {
            "interests": ["technology", "travel", "fitness", "cooking", "reading", "music", "art", "sports"],
            "values": ["family", "success", "creativity", "security", "adventure", "tradition", "innovation"],
            "personality_traits": ["outgoing", "analytical", "creative", "practical", "empathetic", "ambitious"],
            "lifestyle": ["active", "relaxed", "social", "private", "adventurous", "routine-oriented"],
            "motivations": ["achievement", "connection", "growth", "stability", "recognition", "contribution"]
        }
        
        for key, options in mutation_options.items():
            if key in mutated and isinstance(mutated[key], list):
                if random.random() < intensity:
                    # Add new item or replace existing
                    if len(mutated[key]) < 5:
                        mutated[key].append(random.choice(options))
                    else:
                        mutated[key][random.randint(0, len(mutated[key])-1)] = random.choice(options)
        
        return mutated
    
    def _mutate_behaviors(self, behaviors: Dict, intensity: float) -> Dict[str, Any]:
        """Mutate behavioral attributes"""
        mutated = {k: v.copy() if isinstance(v, list) else v for k, v in behaviors.items()}
        
        behavior_options = {
            "shopping_habits": ["impulsive", "research-driven", "brand-loyal", "price-conscious", "quality-focused"],
            "communication_preferences": ["phone calls", "text messages", "email", "video calls", "in-person"],
            "decision_factors": ["price", "quality", "brand", "reviews", "recommendations", "convenience"],
            "media_consumption": ["social media", "news websites", "podcasts", "streaming", "traditional TV"],
            "technology_usage": ["early adopter", "mainstream", "cautious", "mobile-first", "desktop-preferred"]
        }
        
        for key, options in behavior_options.items():
            if key in mutated and isinstance(mutated[key], list):
                if random.random() < intensity:
                    if len(mutated[key]) < 5:
                        mutated[key].append(random.choice(options))
                    else:
                        mutated[key][random.randint(0, len(mutated[key])-1)] = random.choice(options)
        
        return mutated
    
    def _calculate_quality_metrics(self, demographics: Dict, psychographics: Dict, behaviors: Dict) -> Dict[str, float]:
        """Calculate quality metrics for generated persona"""
        return {
            "completeness": len([v for v in demographics.values() if v != "unknown"]) / len(demographics),
            "consistency": 0.8,  # Placeholder for consistency check
            "uniqueness": 0.75,  # Placeholder for uniqueness score
            "realism": 0.85  # Placeholder for realism assessment
        }
    
    async def _validate_persona(self, demographics: Dict, psychographics: Dict, behaviors: Dict, strictness: str) -> Dict[str, Any]:
        """Validate generated persona using enhanced validation service"""
        try:
            # Create persona data structure for validation
            persona_data = {
                "demographics": demographics,
                "psychographics": psychographics,
                "behavioral_patterns": behaviors,
                "id": f"temp_{hash(str(demographics) + str(psychographics) + str(behaviors))}",
                "generation_method": "persona_to_persona"
            }
            
            # Use the enhanced validation service
            validation_result = await validation_service.validate_personas([persona_data])
            
            # Extract validation information
            persona_validation = validation_result.persona_validations[0] if validation_result.persona_validations else None
            
            if persona_validation:
                # Map validation severity to boolean based on strictness
                is_valid = True
                if strictness == "strict":
                    is_valid = not any(issue.severity in ["HIGH", "CRITICAL"] for issue in persona_validation.issues)
                elif strictness == "medium":
                    is_valid = not any(issue.severity == "CRITICAL" for issue in persona_validation.issues)
                # For "low" strictness, only CRITICAL issues make it invalid
                else:
                    is_valid = not any(issue.severity == "CRITICAL" for issue in persona_validation.issues)
                
                return {
                    "is_valid": is_valid,
                    "validation_score": persona_validation.overall_score,
                    "issues": [issue.message for issue in persona_validation.issues],
                    "recommendations": [issue.suggested_fix for issue in persona_validation.issues if issue.suggested_fix],
                    "stage_scores": {
                        "structural": persona_validation.stage_scores.get("STRUCTURAL", 0.0),
                        "domain_expert": persona_validation.stage_scores.get("DOMAIN_EXPERT", 0.0),
                        "adversarial": persona_validation.stage_scores.get("ADVERSARIAL", 0.0)
                    }
                }
            else:
                # Fallback to basic validation if service fails
                return await self._basic_validate_persona(demographics, psychographics, behaviors, strictness)
                
        except Exception as e:
            logger.warning(f"Enhanced validation failed, falling back to basic validation: {e}")
            return await self._basic_validate_persona(demographics, psychographics, behaviors, strictness)
    
    async def _basic_validate_persona(self, demographics: Dict, psychographics: Dict, behaviors: Dict, strictness: str) -> Dict[str, Any]:
        """Basic fallback validation method"""
        validation_results = {
            "is_valid": True,
            "validation_score": 0.8,
            "issues": [],
            "recommendations": []
        }
        
        # Basic validation checks
        if demographics.get("age_range") == "unknown":
            validation_results["issues"].append("Age range not specified")
        
        if not psychographics.get("interests"):
            validation_results["issues"].append("No interests specified")
        
        if strictness == "strict" and len(validation_results["issues"]) > 0:
            validation_results["is_valid"] = False
            validation_results["validation_score"] = 0.6
        
        return validation_results
    
    async def _analyze_persona_bias(self, demographics: Dict, psychographics: Dict, behaviors: Dict) -> Optional[Dict[str, Any]]:
        """Analyze individual persona for bias using BiasDetectionService"""
        try:
            if bias_detection_service is None:
                return None
            
            # Create persona data structure for bias analysis
            persona_data = {
                "demographics": demographics,
                "psychographics": psychographics,
                "behaviors": behaviors
            }
            
            # Analyze bias for single persona dataset
            bias_result = await bias_detection_service.analyze_bias([persona_data])
            
            return {
                "overall_bias_score": bias_result.overall_bias_score,
                "detected_biases": [{
                    "type": bias.bias_type.value,
                    "severity": bias.severity.value,
                    "description": bias.description,
                    "confidence": bias.confidence
                } for bias in bias_result.detected_biases],
                "diversity_metrics": bias_result.diversity_metrics,
                "mitigation_strategies": [{
                    "strategy_type": strategy.strategy_type.value,
                    "description": strategy.description,
                    "implementation_steps": strategy.implementation_steps,
                    "expected_impact": strategy.expected_impact
                } for strategy in bias_result.mitigation_strategies]
            }
        except Exception as e:
            logger.error(f"Error analyzing persona bias: {e}")
            return None
    
    async def _calculate_persona_confidence(self, demographics: Dict, psychographics: Dict, behaviors: Dict, 
                                          generation_method: str, source_personas: List[Dict] = None) -> Dict[str, Any]:
        """Calculate confidence scores for generated persona using ConfidenceScoringService"""
        if not confidence_scoring_service:
            return {
                "demographics": 0.7,
                "psychographics": 0.6,
                "behaviors": 0.65,
                "overall": 0.65
            }
            
        try:
            persona_data = {
                "id": f"generated_{datetime.now().timestamp()}",
                "demographics": demographics,
                "psychographics": psychographics,
                "behaviors": behaviors
            }
            
            extraction_metadata = {
                "generation_method": generation_method,
                "source_personas": source_personas or [],
                "extraction_method": "persona_to_persona_generation",
                "generation_timestamp": datetime.now().isoformat()
            }
            
            confidence_profile = await confidence_scoring_service.calculate_persona_confidence(
                persona=persona_data,
                extraction_metadata=extraction_metadata
            )
            
            return {
                "demographics": confidence_profile.section_confidences.get("demographics", 0.7),
                "psychographics": confidence_profile.section_confidences.get("psychographics", 0.6),
                "behaviors": confidence_profile.section_confidences.get("behaviors", 0.65),
                "overall": confidence_profile.overall_confidence,
                "confidence_profile": confidence_profile.dict()
            }
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return {
                "demographics": 0.5,
                "psychographics": 0.5,
                "behaviors": 0.5,
                "overall": 0.5,
                "error": str(e)
            }
    
    # Additional helper methods (simplified implementations)
    def _find_demographic_source(self, key: str, value: str, personas: List[Dict]) -> str:
        for i, persona in enumerate(personas):
            if persona.get("demographics", {}).get(key) == value:
                return persona.get("id", f"persona_{i}")
        return "merged"
    
    def _map_trait_combinations(self, personas: List[Dict]) -> Dict[str, List[str]]:
        return {"combined_traits": ["analytical", "creative", "social"]}  # Simplified
    
    def _identify_changes(self, source: Dict, new_demo: Dict, new_psych: Dict, new_behav: Dict) -> List[str]:
        changes = []
        source_demo = source.get("demographics", {})
        for key, value in new_demo.items():
            if source_demo.get(key) != value:
                changes.append(f"demographics.{key}")
        return changes
    
    def _evolve_demographics(self, demographics: Dict, context: str) -> Dict[str, Any]:
        evolved = demographics.copy()
        # Simple evolution based on context
        if "career" in context.lower():
            evolved["occupation"] = "professional"
        return evolved
    
    def _evolve_psychographics(self, psychographics: Dict, context: str) -> Dict[str, Any]:
        evolved = {k: v.copy() if isinstance(v, list) else v for k, v in psychographics.items()}
        if "technology" in context.lower():
            if "interests" in evolved:
                evolved["interests"].append("technology")
        return evolved
    
    def _evolve_behaviors(self, behaviors: Dict, context: str) -> Dict[str, Any]:
        evolved = {k: v.copy() if isinstance(v, list) else v for k, v in behaviors.items()}
        if "digital" in context.lower():
            if "technology_usage" in evolved:
                evolved["technology_usage"].append("early adopter")
        return evolved
    
    def _identify_evolution_factors(self, context: str) -> List[str]:
        return ["technological advancement", "social changes", "economic factors"]
    
    def _weighted_mix_demographics(self, personas: List[Dict], weight: float) -> Dict[str, Any]:
        return self._merge_demographics(personas)  # Simplified
    
    def _weighted_mix_psychographics(self, personas: List[Dict], weight: float) -> Dict[str, Any]:
        return self._merge_psychographics(personas)  # Simplified
    
    def _weighted_mix_behaviors(self, personas: List[Dict], weight: float) -> Dict[str, Any]:
        return self._merge_behaviors(personas)  # Simplified
    
    def _identify_dominant_source(self, personas: List[Dict], weights: Dict) -> str:
        return personas[0].get("id", "unknown") if personas else "unknown"

# Initialize persona processor
persona_processor = PersonaProcessor()

@app.post("/api/persona-to-persona/process", response_model=PersonaToPersonaResponse)
async def process_persona_to_persona(request: PersonaToPersonaRequest):
    """Process persona-to-persona transformations"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Validate input personas
        if not request.source_personas or len(request.source_personas) == 0:
            raise ValueError("At least one source persona is required")
        
        # Convert source personas to dict format for processing
        source_personas_dict = []
        for persona in request.source_personas:
            persona_dict = {
                "id": persona.get("id", hashlib.md5(str(persona).encode()).hexdigest()[:12]),
                "name": persona.get("name", "Unknown Persona"),
                "demographics": persona.get("demographics", {}),
                "psychographics": persona.get("psychographics", {}),
                "behaviors": persona.get("behaviors", {}),
                "confidence_scores": persona.get("confidence_scores", {"demographics": 0.7, "psychographics": 0.7, "behaviors": 0.7})
            }
            source_personas_dict.append(persona_dict)
        
        logger.info(f"Processing {len(source_personas_dict)} source personas with operation: {request.operation_type}")
        
        # Process personas using the persona processor
        generated_personas = await persona_processor.process_personas(
            source_personas=source_personas_dict,
            operation_type=request.operation_type,
            output_count=request.output_count,
            validation_strictness=request.validation_strictness,
            advanced_settings=request.advanced_settings or {}
        )
        
        # Filter by validation if strict mode
        if request.validation_strictness == "strict":
            generated_personas = [
                p for p in generated_personas 
                if p.validation_results.get("is_valid", True)
            ]
        
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Calculate processing summary
        processing_summary = {
            "source_personas_count": len(request.source_personas),
            "operation_type": request.operation_type,
            "personas_generated": len(generated_personas),
            "validation_strictness": request.validation_strictness,
            "advanced_settings_applied": bool(request.advanced_settings)
        }
        
        # Calculate operation metrics
        operation_metrics = {
            "success_rate": len(generated_personas) / max(request.output_count, 1),
            "avg_confidence": float(np.mean([
                float(np.mean(list(p.confidence_scores.values())))
                for p in filtered_personas
            ])) if filtered_personas else 0.0,
            "avg_quality_score": float(np.mean([
                float(np.mean(list(p.quality_metrics.values())))
                for p in filtered_personas
            ])) if filtered_personas else 0.0,
            "validation_pass_rate": len([
                p for p in generated_personas 
                if p.validation_results.get("is_valid", True)
            ]) / max(len(generated_personas), 1)
        }
        
        # Generate comparison analysis
        comparison_analysis = {
            "demographic_diversity": _calculate_demographic_diversity(source_personas_dict, generated_personas),
            "trait_evolution": _analyze_trait_evolution(source_personas_dict, generated_personas, request.operation_type),
            "inheritance_patterns": _analyze_inheritance_patterns(generated_personas),
            "novelty_score": _calculate_novelty_score(source_personas_dict, generated_personas)
        }
        
        return PersonaToPersonaResponse(
            generated_personas=generated_personas,
            processing_summary=processing_summary,
            operation_metrics=operation_metrics,
            comparison_analysis=comparison_analysis,
            execution_time=execution_time,
            success=True,
            message=f"Successfully generated {len(generated_personas)} personas using {request.operation_type} operation"
        )
        
    except Exception as e:
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"Error in persona-to-persona processing: {str(e)}")
        
        return PersonaToPersonaResponse(
            generated_personas=[],
            processing_summary={},
            operation_metrics={},
            comparison_analysis={},
            execution_time=execution_time,
            success=False,
            message=f"Persona-to-persona processing failed: {str(e)}",
            errors=[str(e)]
        )

# Helper functions for persona-to-persona analysis
def _calculate_demographic_diversity(source_personas: List[Dict], generated_personas: List[GeneratedPersonaP2P]) -> Dict[str, float]:
    """Calculate demographic diversity metrics"""
    try:
        # Extract demographic values from source and generated personas
        source_demographics = []
        for persona in source_personas:
            demo = persona.get("demographics", {})
            source_demographics.append(tuple(demo.values()))
        
        generated_demographics = []
        for persona in generated_personas:
            demo = persona.demographics
            generated_demographics.append(tuple(demo.values()))
        
        # Calculate diversity scores
        source_unique = len(set(source_demographics))
        generated_unique = len(set(generated_demographics))
        
        return {
            "source_diversity": source_unique / max(len(source_personas), 1),
            "generated_diversity": generated_unique / max(len(generated_personas), 1),
            "diversity_improvement": (generated_unique - source_unique) / max(source_unique, 1)
        }
    except Exception:
        return {"source_diversity": 0.0, "generated_diversity": 0.0, "diversity_improvement": 0.0}

def _analyze_trait_evolution(source_personas: List[Dict], generated_personas: List[GeneratedPersonaP2P], operation_type: str) -> Dict[str, Any]:
    """Analyze how traits evolved during processing"""
    try:
        evolution_analysis = {
            "operation_type": operation_type,
            "trait_changes": [],
            "preservation_rate": 0.0,
            "innovation_rate": 0.0
        }
        
        # Collect all traits from source personas
        source_traits = set()
        for persona in source_personas:
            psych = persona.get("psychographics", {})
            for trait_list in psych.values():
                if isinstance(trait_list, list):
                    source_traits.update(trait_list)
        
        # Collect all traits from generated personas
        generated_traits = set()
        for persona in generated_personas:
            psych = persona.psychographics
            for trait_list in psych.values():
                if isinstance(trait_list, list):
                    generated_traits.update(trait_list)
        
        # Calculate preservation and innovation rates
        preserved_traits = source_traits.intersection(generated_traits)
        new_traits = generated_traits - source_traits
        
        evolution_analysis["preservation_rate"] = len(preserved_traits) / max(len(source_traits), 1)
        evolution_analysis["innovation_rate"] = len(new_traits) / max(len(generated_traits), 1)
        evolution_analysis["trait_changes"] = {
            "preserved": list(preserved_traits)[:5],
            "new": list(new_traits)[:5],
            "lost": list(source_traits - generated_traits)[:5]
        }
        
        return evolution_analysis
    except Exception:
        return {"operation_type": operation_type, "trait_changes": [], "preservation_rate": 0.0, "innovation_rate": 0.0}

def _analyze_inheritance_patterns(generated_personas: List[GeneratedPersonaP2P]) -> Dict[str, Any]:
    """Analyze inheritance patterns in generated personas"""
    try:
        patterns = {
            "source_distribution": {},
            "method_distribution": {},
            "avg_sources_per_persona": 0.0
        }
        
        # Analyze source persona distribution
        all_sources = []
        for persona in generated_personas:
            all_sources.extend(persona.source_personas)
            patterns["method_distribution"][persona.generation_method] = patterns["method_distribution"].get(persona.generation_method, 0) + 1
        
        # Count source usage
        from collections import Counter
        source_counts = Counter(all_sources)
        patterns["source_distribution"] = dict(source_counts.most_common(10))
        
        # Calculate average sources per persona
        patterns["avg_sources_per_persona"] = len(all_sources) / max(len(generated_personas), 1)
        
        return patterns
    except Exception:
        return {"source_distribution": {}, "method_distribution": {}, "avg_sources_per_persona": 0.0}

def _calculate_novelty_score(source_personas: List[Dict], generated_personas: List[GeneratedPersonaP2P]) -> float:
    """Calculate how novel the generated personas are compared to source"""
    try:
        # Simple novelty calculation based on attribute combinations
        source_combinations = set()
        for persona in source_personas:
            demo = persona.get("demographics", {})
            combo = tuple(sorted(demo.items()))
            source_combinations.add(combo)
        
        generated_combinations = set()
        for persona in generated_personas:
            demo = persona.demographics
            combo = tuple(sorted(demo.items()))
            generated_combinations.add(combo)
        
        # Calculate novelty as percentage of new combinations
        new_combinations = generated_combinations - source_combinations
        novelty_score = len(new_combinations) / max(len(generated_combinations), 1)
        
        return min(1.0, max(0.0, novelty_score))
    except Exception:
        return 0.5  # Default moderate novelty score

@app.post("/api/text-to-persona/process", response_model=TextToPersonaResponse)
async def process_text_to_persona(request: TextToPersonaRequest):
    """Process text input and extract personas using advanced NLP and LLM pipeline"""
    start_time = asyncio.get_event_loop().time()
    warnings = []
    errors = []
    
    try:
        # Combine text content and file content if provided
        full_text = request.text_content
        if request.file_content:
            full_text += "\n\n" + request.file_content
        
        logger.info(f"Processing text of length {len(full_text)} characters...")
        
        # Step 1: Advanced NLP Analysis
        logger.info("Performing advanced NLP analysis...")
        if not advanced_nlp_service:
            raise HTTPException(status_code=503, detail="Advanced NLP service not initialized")
        
        nlp_result = await advanced_nlp_service.extract_entities_advanced(
            text=full_text
        )
        
        # Step 2: Sophisticated Demographic Extraction
        logger.info("Extracting demographic information with ML models...")
        if not demographic_extraction_service:
            raise HTTPException(status_code=503, detail="Demographic extraction service not initialized")
        
        # Convert entities dict to list format for demographic service
        entities_list = []
        if nlp_result.entities:
            for entity_type, entity_list in nlp_result.entities.items():
                for entity in entity_list:
                    entity_with_label = entity.copy()
                    entity_with_label['label'] = entity_type
                    entities_list.append(entity_with_label)
        
        demographic_result = await demographic_extraction_service.extract_demographics_advanced(
            text=full_text,
            nlp_features=nlp_result.linguistic_features,
            entities=entities_list,
            focus_areas=request.demographic_focus or []
        )
        
        # Extract preprocessing data from NLP analysis
        preprocessed = {
            "word_count": len(full_text.split()),
            "sentence_count": len([s for s in full_text.split('.') if s.strip()]),
            "character_count": len(full_text)
        }
        
        entities = nlp_result.entities
        sentiment = nlp_result.sentiment_analysis
        topics = nlp_result.topic_modeling
        demographics = {pred.attribute: pred.value for pred in demographic_result.predictions}
        
        # Generate personas using advanced LLM integration
        logger.info("Generating personas with advanced LLM integration...")
        if not llm_persona_service:
            raise HTTPException(status_code=503, detail="LLM persona service not initialized")
        
        generated_personas = []
        
        for i in range(request.persona_count):
            try:
                persona_id = hashlib.md5(f"{full_text}_{i}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
                
                # Extract persona using LLM
                llm_result = await llm_persona_service.extract_personas(
                    text_content=full_text,
                    persona_count=1,  # Generate one persona per iteration
                    domain=request.domain,
                    custom_attributes=request.custom_attributes,
                    demographic_focus=request.demographic_focus,
                    confidence_threshold=request.confidence_threshold
                )
                
                # Step 4: Calculate confidence scores
                logger.info(f"Calculating confidence scores for persona {i+1}...")
                if confidence_scoring_service and llm_result.personas:
                    # Extract the first persona from the result
                    first_persona = llm_result.personas[0]
                    persona_data = {
                        "id": f"persona_{i+1}",
                        "demographics": first_persona.get("demographics", {}),
                        "psychographics": first_persona.get("psychographics", {}),
                        "behaviors": first_persona.get("behaviors", {})
                    }
                    extraction_metadata = {
                        "nlp_analysis": nlp_result.dict(),
                        "demographic_extraction": demographic_result.dict(),
                        "llm_extraction": llm_result.dict(),
                        "text_length": len(full_text),
                        "extraction_method": "hybrid_llm_nlp"
                    }
                    
                    # Transform extraction_metadata using data adapter
                    transformed_metadata = data_adapter.transform_extraction_metadata(
                        extraction_metadata, full_text
                    )
                    
                    confidence_profile = await confidence_scoring_service.calculate_persona_confidence(
                        persona=persona_data,
                        extraction_metadata=transformed_metadata
                    )
                    # Convert numpy.float32 to Python float
                    confidence_scores = {
                        k: float(v) for k, v in confidence_profile.section_confidences.items()
                    }
                else:
                    # Fallback confidence scores
                    base_confidence = llm_result.confidence_scores.get("overall", 0.7) if llm_result.confidence_scores else 0.7
                    confidence_scores = {
                        "demographics": float(base_confidence * 0.9),
                        "psychographics": float(base_confidence * 0.85),
                        "behaviors": float(base_confidence * 0.8)
                    }
                
                # Step 5: Validation (if enabled)
                validation_result = None
                if validation_service and request.confidence_threshold > 0.5 and llm_result.personas:
                    logger.info(f"Validating persona {i+1}...")
                    first_persona = llm_result.personas[0]
                    
                    # Create persona data for validation
                    persona_data = {
                        "id": f"temp_persona_{i+1}",
                        "name": first_persona.get("name", f"Persona {i+1}"),
                        "demographics": first_persona.get("demographics", {}),
                        "psychographics": first_persona.get("psychographics", {}),
                        "behaviors": first_persona.get("behaviors", {}),
                        "confidence_scores": confidence_scores
                    }
                    
                    validation_result = await validation_service.validate_personas([persona_data])
                    
                    if not validation_result.is_valid:
                        # Add recommendations as warnings
                        warnings.extend(validation_result.recommendations)
                        # Add critical issues as errors
                        critical_issues = [issue.description for issue in validation_result.issues 
                                         if issue.severity.value == "critical"]
                        if critical_issues:
                            errors.extend(critical_issues)
                
                # Step 6: Bias Detection (if enabled)
                bias_analysis_result = None
                if bias_detection_service and request.confidence_threshold > 0.6 and llm_result.personas:
                    logger.info(f"Analyzing bias for persona {i+1}...")
                    first_persona = llm_result.personas[0]
                    persona_data = {
                        "demographics": first_persona.get("demographics", {}),
                        "psychographics": first_persona.get("psychographics", {}),
                        "behaviors": first_persona.get("behaviors", {})
                    }
                    bias_analysis_result = await bias_detection_service.analyze_bias([persona_data])
                    
                    if bias_analysis_result.overall_bias_score > 0.3:  # Moderate bias threshold
                        bias_warnings = [f"Bias detected: {bias.description}" for bias in bias_analysis_result.detected_biases[:3]]
                        warnings.extend(bias_warnings)
                        
                        if bias_analysis_result.overall_bias_score > 0.7:  # High bias threshold
                            errors.append(f"High bias score ({bias_analysis_result.overall_bias_score:.2f}) detected in persona {i+1}")
                
                # Build comprehensive persona
                if llm_result.personas:
                    first_persona = llm_result.personas[0]
                    persona_name = first_persona.get("name", f"Extracted Persona {i+1}")
                    persona_demographics = first_persona.get("demographics", {})
                    persona_psychographics = first_persona.get("psychographics", {})
                    persona_behaviors = first_persona.get("behaviors", {})
                    persona_evidence = first_persona.get("evidence", {})
                else:
                    persona_name = f"Extracted Persona {i+1}"
                    persona_demographics = {}
                    persona_psychographics = {}
                    persona_behaviors = {}
                    persona_evidence = {}
                
                persona = ExtractedPersona(
                    id=persona_id,
                    name=persona_name,
                    demographics=convert_numpy_types(persona_demographics),
                    psychographics=convert_numpy_types(persona_psychographics),
                    behaviors=convert_numpy_types(persona_behaviors),
                    confidence_scores=convert_numpy_types(confidence_scores),
                    source_evidence={
                        "demographics": persona_evidence.get("demographics", []),
                        "psychographics": persona_evidence.get("psychographics", []),
                        "behaviors": persona_evidence.get("behaviors", []),
                        "nlp_entities": [f"{k}: {v}" for k, v in nlp_result.entities.items()],
                        "demographic_predictions": [f"{pred.attribute}: {pred.value} (confidence: {pred.confidence:.2f})" for pred in demographic_result.predictions]
                    },
                    processing_metadata=convert_numpy_types({
                        "model_version": "text-to-persona-advanced-v2.0",
                        "processing_time": 0.0,  # Will be updated
                        "llm_used": True,
                        "llm_provider": llm_result.extraction_metadata.get("provider", "unknown") if llm_result.extraction_metadata else "unknown",
                        "confidence_threshold": request.confidence_threshold,
                        "domain_context": request.domain,
                        "text_length": len(full_text),
                        "entities_found": len([item for sublist in nlp_result.entities.values() for item in sublist]),
                        "validation_passed": validation_result.is_valid if validation_result else True,
                        "demographic_ml_used": True,
                        "advanced_nlp_used": True,
                        "bias_analysis_performed": bias_analysis_result is not None,
                        "bias_score": bias_analysis_result.overall_bias_score if bias_analysis_result else 0.0,
                        "biases_detected": len(bias_analysis_result.detected_biases) if bias_analysis_result else 0
                    })
                )
                
                # Filter by confidence threshold
                overall_confidence = sum(confidence_scores.values()) / len(confidence_scores)
                if overall_confidence >= request.confidence_threshold:
                    generated_personas.append(persona)
                else:
                    warnings.append(f"Persona {i+1} filtered out due to low confidence ({overall_confidence:.2f} < {request.confidence_threshold})")
                    
            except Exception as e:
                logger.error(f"Error generating persona {i+1}: {str(e)}")
                continue
        
        # Use generated_personas directly (already filtered above)
        filtered_personas = generated_personas

        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Update processing time in metadata
        for persona in filtered_personas:
            persona.processing_metadata["processing_time"] = execution_time / len(filtered_personas) if filtered_personas else 0
            
        response_data = {
            "generated_personas": filtered_personas,
            "processing_summary": {
                "input_text_length": len(full_text),
                "personas_requested": request.persona_count,
                "personas_generated": len(generated_personas),
                "personas_after_filtering": len(filtered_personas),
                "confidence_threshold": request.confidence_threshold,
                "domain_context": request.domain,
                "batch_processing": request.batch_processing
            },
            "text_analysis": {
                "word_count": preprocessed["word_count"],
                "sentence_count": preprocessed["sentence_count"],
                "entities_found": entities,
                "sentiment_analysis": sentiment,
                "key_topics": topics,
                "demographic_indicators": demographics
            },
            "quality_metrics": {
                "avg_confidence": float(np.mean([max(p.confidence_scores.values()) for p in filtered_personas])) if filtered_personas else 0.0,
                "entity_coverage": float(len([item for sublist in entities.values() for item in sublist]) / max(preprocessed["word_count"] / 100, 1)),
                "topic_diversity": float(len(set(topics)) / max(len(topics), 1)),
                "demographic_completeness": float(len([v for v in demographics.values() if v != "unknown"]) / len(demographics))
            },
            "execution_time": execution_time,
            "success": True,
            "message": f"Successfully generated {len(filtered_personas)} personas using advanced LLM and NLP pipeline",
            "warnings": warnings if warnings else None
        }
        
        # Apply convert_numpy_types to the entire response to ensure no numpy types remain
        response_data = convert_numpy_types(response_data)
        
        return TextToPersonaResponse(**response_data)
        
    except Exception as e:
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"Error in text-to-persona processing: {str(e)}")
        
        return TextToPersonaResponse(
            generated_personas=[],
            processing_summary={},
            text_analysis={},
            quality_metrics={},
            execution_time=execution_time,
            success=False,
            message=f"Text-to-persona processing failed: {str(e)}",
            errors=[str(e)]
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)