from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import os

class PersonaFormData(BaseModel):
    """Form data for persona generation requests"""
    sample_size: int = Field(default=10, ge=1, le=1000)
    generation_method: str = Field(default="hybrid")
    quality_threshold: float = Field(default=float(os.getenv("DEFAULT_QUALITY_THRESHOLD", "0.3")), ge=0.0, le=1.0)
    enable_clustering: bool = Field(default=True)
    distribution_matching: bool = Field(default=True)
    target_clusters: Optional[int] = Field(default=None, ge=2, le=20)
    industry_context: Optional[str] = Field(default=None)
    use_case_context: Optional[str] = Field(default=None)
    project_name: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)

class GeneratedPersona(BaseModel):
    """Generated persona data structure"""
    id: str
    name: str
    age: int
    gender: str
    location: str
    income: str
    education: str
    interests: List[str]
    pain_points: List[str]
    goals: List[str]
    personality_traits: List[str]
    technology_comfort: str
    communication_style: str
    narrative: str
    demographic_profile: Dict[str, Any]
    confidence_score: float = Field(ge=0.0, le=1.0)
    component_scores: Dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    project_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class EvaluationResults(BaseModel):
    """Evaluation results for generated personas"""
    total_personas: int
    quality_metrics: Dict[str, float]
    clustering_results: Dict[str, Any]
    distribution_analysis: Dict[str, Any]
    diversity_scores: Dict[str, float]
    recommendations: List[str]
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)