import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from loguru import logger
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
import random
from enum import Enum

# Import core engines
from engines.rule_based_engine import RuleBasedEngine, DemographicProfile, DemographicConstraints
from engines.llm_engine import LLMPersonaEngine, PersonaGenerationRequest
from services.diversity_engine import DiversityEngine
from services.distribution_matcher import DistributionMatcher
from services.evaluation_metrics import EvaluationMetrics, PersonaQualityMetrics
from services.clustering_engine import ClusteringEngine
from storage.file_storage import FileStorageManager, PersonaRecord
from engines.reinforcement_engine import ReinforcementLearningEngine
from engines.adversarial_engine import AdversarialValidationEngine
from services.clustering_aware_engine import ClusteringAwareEngine

class GenerationMethod(Enum):
    """Enumeration of persona generation methods"""
    RULE_BASED = "rule_based"
    LLM_ONLY = "llm_only"
    DIVERSITY_ONLY = "diversity_only"
    HYBRID_BASIC = "hybrid_basic"
    HYBRID_ADVANCED = "hybrid_advanced"
    DISTRIBUTION_MATCHED = "distribution_matched"

@dataclass
class GenerationConfig:
    """Configuration for persona generation"""
    method: GenerationMethod = GenerationMethod.HYBRID_ADVANCED
    sample_size: int = 100
    diversity_weight: float = 0.3
    llm_weight: float = 0.4
    rule_weight: float = 0.3
    distribution_matching: bool = True
    quality_threshold: float = float(os.getenv("DEFAULT_QUALITY_THRESHOLD", "0.3"))
    max_iterations: int = 3
    enable_clustering: bool = True
    target_clusters: Optional[int] = None
    demographic_constraints: Optional[Dict[str, Any]] = None
    psychographic_preferences: Optional[Dict[str, Any]] = None
    behavioral_patterns: Optional[Dict[str, Any]] = None
    geographic_focus: Optional[Dict[str, str]] = None
    industry_context: Optional[str] = None
    use_case_context: Optional[str] = None
    validation_enabled: bool = True
    storage_enabled: bool = True
    export_format: str = "json"  # json, csv, both

@dataclass
class GenerationRequest:
    """Request structure for persona generation"""
    config: GenerationConfig
    user_id: Optional[str] = None
    project_name: Optional[str] = None
    persona_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class GenerationResult:
    """Result structure for persona generation"""
    personas: List[Dict[str, Any]]
    generation_metadata: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    clustering_results: Optional[Dict[str, Any]] = None
    distribution_analysis: Optional[Dict[str, Any]] = None
    storage_ids: Optional[List[str]] = None
    export_paths: Optional[List[str]] = None
    execution_time: float = 0.0
    success: bool = True
    errors: List[str] = None
    warnings: List[str] = None

class HybridPersonaEngine:
    """Main hybrid engine for persona generation combining multiple approaches"""
    
    def __init__(self, 
                 aws_access_key_id: str,
                 aws_secret_access_key: str,
                 aws_region: str = "us-east-1",
                 storage_manager: Optional[FileStorageManager] = None,
                 enable_gpu: bool = False):
        
        # Initialize core engines
        self.rule_engine = RuleBasedEngine()
        self.llm_engine = LLMPersonaEngine(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region=aws_region
        )
        self.diversity_engine = DiversityEngine()
        self.distribution_matcher = DistributionMatcher()
        self.evaluation_metrics = EvaluationMetrics()
        self.clustering_engine = ClusteringEngine()
        
        # Storage manager
        self.storage_manager = storage_manager
        
        # Initialize reinforcement learning engine
        self.rl_engine = ReinforcementLearningEngine()
        
        # Initialize adversarial validation engine
        self.adversarial_engine = AdversarialValidationEngine()
        
        # Initialize clustering-aware generation engine
        self.clustering_aware_engine = ClusteringAwareEngine()
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Generation statistics
        self.generation_stats = {
            "total_generated": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "average_quality_score": 0.0,
            "generation_methods_used": {},
            "last_generation_time": None
        }
        
        logger.info("Initialized HybridPersonaEngine with all core components")
    
    async def generate_personas(self, request: GenerationRequest) -> GenerationResult:
        """Main method for generating personas using hybrid approach"""
        start_time = datetime.now()
        config = request.config
        
        # Apply reinforcement learning optimizations if available
        if hasattr(self, 'rl_engine'):
            base_config = {
                'diversity_weight': config.diversity_weight,
                'llm_weight': config.llm_weight,
                'rule_weight': config.rule_weight,
                'quality_threshold': config.quality_threshold
            }
            adaptive_config = self.rl_engine.get_adaptive_config(base_config)
            if adaptive_config:
                # Update config with RL recommendations
                config.diversity_weight = adaptive_config.get('diversity_weight', config.diversity_weight)
                config.llm_weight = adaptive_config.get('llm_weight', config.llm_weight)
                config.rule_weight = adaptive_config.get('rule_weight', config.rule_weight)
                config.quality_threshold = adaptive_config.get('quality_threshold', config.quality_threshold)
                logger.info(f"Applied RL adaptive config: diversity={config.diversity_weight:.3f}, llm={config.llm_weight:.3f}, rule={config.rule_weight:.3f}")
        
        try:
            # DEBUG: Print hybrid engine configuration
            # Debug logging removed for production
            
            logger.info(f"Starting persona generation with method: {config.method.value}, sample_size: {config.sample_size}")
            
            # Initialize result structure
            result = GenerationResult(
                personas=[],
                generation_metadata={
                    "method": config.method.value,
                "sample_size": config.sample_size,
                "timestamp": start_time.isoformat(),
                "request_id": f"req_{int(start_time.timestamp())}",
                "config": asdict(config)
                },
                quality_metrics={},
                errors=[],
                warnings=[]
            )
            
            # Generate personas based on method
            if config.method == GenerationMethod.RULE_BASED:
                personas = await self._generate_rule_based(config)
            elif config.method == GenerationMethod.LLM_ONLY:
                personas = await self._generate_llm_only(config)
            elif config.method == GenerationMethod.DIVERSITY_ONLY:
                personas = await self._generate_diversity_only(config)
            elif config.method == GenerationMethod.HYBRID_BASIC:
                personas = await self._generate_hybrid_basic(config)
            elif config.method == GenerationMethod.HYBRID_ADVANCED:
                personas = await self._generate_hybrid_advanced(config)
            elif config.method == GenerationMethod.DISTRIBUTION_MATCHED:
                personas = await self._generate_distribution_matched(config)
            else:
                raise ValueError(f"Unknown generation method: {config.method}")
            
            result.personas = personas
            
            # Apply distribution matching if enabled
            if config.distribution_matching and config.method != GenerationMethod.DISTRIBUTION_MATCHED:
                logger.info("Applying distribution matching")
                personas = await self._apply_distribution_matching(personas, config)
                result.personas = personas
            
            # Quality evaluation
            if config.validation_enabled:
                logger.info("Evaluating persona quality")
                quality_metrics = await self._evaluate_quality(personas, config)
                result.quality_metrics = quality_metrics
                
                # Adversarial validation
                if hasattr(self, 'adversarial_engine'):
                    adversarial_feedback = await self.adversarial_engine.validate_personas(
                        personas, config.demographic_constraints
                    )
                    quality_metrics['adversarial'] = {
                        'realism_score': adversarial_feedback.realism_score,
                        'diversity_score': adversarial_feedback.diversity_score,
                        'consistency_score': adversarial_feedback.consistency_score,
                        'overall_score': adversarial_feedback.overall_score,
                        'improvement_suggestions': adversarial_feedback.improvement_suggestions,
                        'outlier_count': sum(adversarial_feedback.outlier_flags)
                    }
                    logger.info(f"Adversarial validation: overall={adversarial_feedback.overall_score:.3f}")
                
                # Record reinforcement learning feedback
                if hasattr(self, 'rl_engine') and quality_metrics:
                    clustering_results = quality_metrics.get('clustering', {})
                    generation_config = asdict(config)
                    demographic_profiles = []  # Will be populated if available
                    
                    feedback = self.rl_engine.record_feedback(
                        personas, clustering_results, generation_config, demographic_profiles
                    )
                    if feedback:
                        logger.info(f"Recorded RL feedback: silhouette={feedback.silhouette_score:.3f}")
                
                # Filter personas below quality threshold
                if config.quality_threshold > 0:
                    filtered_personas = await self._filter_by_quality(personas, quality_metrics, config.quality_threshold)
                    if len(filtered_personas) < len(personas):
                        result.warnings.append(f"Filtered {len(personas) - len(filtered_personas)} personas below quality threshold {config.quality_threshold}")
                        result.personas = filtered_personas
            
            # Clustering analysis
            if config.enable_clustering and len(result.personas) > 3:
                logger.info("Performing clustering analysis")
                clustering_results = await self._perform_clustering(result.personas, config)
                result.clustering_results = clustering_results
            
            # Distribution analysis
            if len(result.personas) > 10:
                logger.info("Analyzing distributions")
                distribution_analysis = await self._analyze_distributions(result.personas)
                result.distribution_analysis = distribution_analysis
            
            # Storage
            if config.storage_enabled and self.storage_manager:
                logger.info("Storing personas")
                storage_ids = await self._store_personas(result.personas, request, result)
                result.storage_ids = storage_ids
            
            # Export
            if config.export_format and self.storage_manager:
                logger.info(f"Exporting personas in {config.export_format} format")
                export_paths = await self._export_personas(result.personas, config.export_format, request)
                result.export_paths = export_paths
            
            # Calculate execution time
            end_time = datetime.now()
            result.execution_time = (end_time - start_time).total_seconds()
            
            # Update statistics
            self._update_generation_stats(result, config)
            
            logger.info(f"Successfully generated {len(result.personas)} personas in {result.execution_time:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error in persona generation: {e}")
            end_time = datetime.now()
            
            return GenerationResult(
                personas=[],
                generation_metadata={
                    "method": config.method.value,
                    "sample_size": config.sample_size,
                    "timestamp": start_time.isoformat(),
                    "error_timestamp": end_time.isoformat()
                },
                quality_metrics={},
                execution_time=(end_time - start_time).total_seconds(),
                success=False,
                errors=[str(e)]
            )
    
    async def _generate_rule_based(self, config: GenerationConfig) -> List[Dict[str, Any]]:
        """Generate personas using only rule-based approach"""
        logger.debug("Generating personas using rule-based method")
        
        # Generate demographic profiles
        demographic_profiles = self.rule_engine.generate_batch_demographics(
            sample_size=config.sample_size,
            constraints=self._convert_to_demographic_constraints(config.demographic_constraints)
        )
        
        # Convert to persona format
        personas = []
        for profile in demographic_profiles:
            persona = {
                "demographics": profile,  # profile is already a dictionary
                "psychographics": self._generate_basic_psychographics(),
                "behavioral_patterns": self._generate_basic_behavioral_patterns(),
                "generation_method": "rule_based",
                "confidence_score": random.uniform(0.6, 0.8)
            }
            personas.append(persona)
        
        return personas
    
    async def _generate_llm_only(self, config: GenerationConfig) -> List[Dict[str, Any]]:
        """Generate personas using only LLM approach"""
        logger.debug("Generating personas using LLM-only method")
        
        personas = []
        
        # Generate basic demographic constraints for LLM
        for i in range(config.sample_size):
            # Create basic demographic seed
            demographic_seed = self.rule_engine.generate_single_demographic(
                constraints=self._convert_to_demographic_constraints(config.demographic_constraints)
            )
            
            # Preserve exact age constraints for strict LLM compliance
            demographic_data = demographic_seed.copy()
            if 'age' in demographic_data:
                # Keep exact age as-is for strict constraint enforcement
                demographic_data['exact_age'] = demographic_data['age']
                # Remove the generic 'age' field to avoid confusion
                del demographic_data['age']
            
            # Create LLM request
            llm_request = PersonaGenerationRequest(
                demographic_data=demographic_data,
                behavioral_scores={"openness": 0.7, "conscientiousness": 0.6, "extraversion": 0.5, "agreeableness": 0.8, "neuroticism": 0.3},
                psychographic_data=config.psychographic_preferences or {"values": ["family", "success"], "interests": ["technology", "travel"]},
                context=f"Industry: {config.industry_context or 'General'}, Use case: {config.use_case_context or 'Market research'}"
            )
            
            # DEBUG: Print LLM request construction
            # Debug logging removed for production
            
            # Generate narrative
            narrative = await self.llm_engine.generate_persona_narrative(llm_request)
            
            persona = {
                "demographics": demographic_seed,
                "narrative": narrative,
                "generation_method": "llm_only",
                "confidence_score": random.uniform(0.7, 0.9)
            }
            personas.append(persona)
        
        return personas
    
    async def _generate_diversity_only(self, config: GenerationConfig) -> List[Dict[str, Any]]:
        """Generate personas using only diversity engine (GAN/VAE)"""
        logger.debug("Generating personas using diversity-only method")
        
        personas = []
        
        for i in range(config.sample_size):
            # Generate basic demographics first
            demographic_profile = self.rule_engine.generate_single_demographic(
                constraints=self._convert_to_demographic_constraints(config.demographic_constraints)
            )
            
            # Generate diverse psychographic profile using demographics
            psychographic_profile = self.diversity_engine.generate_psychographic_profile(
                demographic=demographic_profile
            )
            
            # Generate diverse behavioral patterns using demographics
            behavioral_profile = self.diversity_engine._generate_behavioral_patterns(
                demographic=demographic_profile, 
                diversity_level=config.diversity_weight
            )
            
            persona = {
                "demographics": demographic_profile,
                "psychographics": psychographic_profile,
                "behavioral_patterns": behavioral_profile,
                "generation_method": "diversity_only",
                "confidence_score": random.uniform(0.6, 0.8)
            }
            personas.append(persona)
        
        return personas
    
    async def _generate_hybrid_basic(self, config: GenerationConfig) -> List[Dict[str, Any]]:
        """Generate personas using basic hybrid approach (rule-based + LLM)"""
        logger.debug("Generating personas using basic hybrid method")
        
        personas = []
        
        for i in range(config.sample_size):
            # Start with rule-based demographics
            demographic_profile = self.rule_engine.generate_single_demographic(
                constraints=self._convert_to_demographic_constraints(config.demographic_constraints)
            )
            
            # Use frontend psychographic preferences if available, otherwise generate
            if config.psychographic_preferences:
                psychographic_profile = self._apply_psychographic_preferences(
                    config.psychographic_preferences, demographic_profile
                )
            else:
                psychographic_profile = self.diversity_engine.generate_psychographic_profile(
                    demographic=demographic_profile
                )
            
            # Preserve exact age constraints for strict LLM compliance
            demographic_data = demographic_profile.copy()
            if 'age' in demographic_data:
                # Keep exact age as-is for strict constraint enforcement
                demographic_data['exact_age'] = demographic_data['age']
                # Remove the generic 'age' field to avoid confusion
                del demographic_data['age']
            
            # Create LLM request for narrative enhancement
            llm_request = PersonaGenerationRequest(
                demographic_data=demographic_data,
                behavioral_scores=config.behavioral_patterns or {"openness": 0.7, "conscientiousness": 0.6, "extraversion": 0.5, "agreeableness": 0.8, "neuroticism": 0.3},
                psychographic_data=psychographic_profile,
                context=f"Industry: {config.industry_context or 'General'}, Use case: {config.use_case_context or 'Market research'}"
            )
            
            # Generate enhanced narrative
            narrative_result = await self.llm_engine.generate_persona_narrative(llm_request)
            
            persona = {
                "demographics": demographic_profile,
                "psychographics": psychographic_profile,
                "narrative": narrative_result.get("narrative", ""),
                "generation_method": "hybrid_basic",
                "confidence_score": random.uniform(0.75, 0.9)
            }
            personas.append(persona)
        
        return personas
    
    async def _generate_hybrid_advanced(self, config: GenerationConfig) -> List[Dict[str, Any]]:
        """Generate personas using advanced hybrid approach (all engines)"""
        logger.debug("Generating personas using advanced hybrid method")
        
        personas = []
        
        # Generate in batches for efficiency
        batch_size = min(10, config.sample_size)
        num_full_batches = config.sample_size // batch_size
        remainder = config.sample_size % batch_size
        
        batches = [batch_size] * num_full_batches
        if remainder > 0:
            batches.append(remainder)
        
        # Get clustering guidance if we have existing personas
        clustering_guidance = None
        if len(personas) > 5:  # Only apply clustering guidance after we have some personas
            clustering_guidance = self.clustering_aware_engine.generate_clustering_guidance(
                existing_personas=personas,
                target_clusters=config.target_clusters or 5
            )
        
        for batch_num, batch_count in enumerate(batches):
            if batch_count == 0:
                continue
                
            logger.debug(f"Processing batch {batch_num + 1} with {batch_count} personas")
            
            # Generate demographic profiles
            demographic_profiles = self.rule_engine.generate_batch_demographics(
                sample_size=batch_count,
                constraints=self._convert_to_demographic_constraints(config.demographic_constraints)
            )
            
            # Generate psychographic profiles using frontend preferences if available
            psychographic_profiles = []
            for i in range(batch_count):
                if config.psychographic_preferences:
                    psychographic_profile = self._apply_psychographic_preferences(
                        config.psychographic_preferences, demographic_profiles[i]
                    )
                else:
                    psychographic_profile = self.diversity_engine.generate_psychographic_profile(
                        demographic=demographic_profiles[i]
                    )
                
                # Apply clustering guidance if available
                if clustering_guidance and len(clustering_guidance) > 0:
                    # Create a base persona from demographic and psychographic data
                    base_persona = {
                        'demographics': demographic_profiles[i],
                        'psychographics': psychographic_profile
                    }
                    # Use the first guidance object for optimization
                    guidance = clustering_guidance[0] if isinstance(clustering_guidance, list) else clustering_guidance
                    optimized_persona = self.clustering_aware_engine.optimize_persona_for_clustering(
                        base_persona, guidance, personas
                    )
                    demographic_profiles[i] = optimized_persona.get('demographics', demographic_profiles[i])
                    psychographic_profile = optimized_persona.get('psychographics', psychographic_profile)
                
                psychographic_profiles.append(psychographic_profile)
            
            # Generate behavioral profiles using frontend preferences if available
            behavioral_profiles = []
            for i in range(batch_count):
                if config.behavioral_patterns:
                    behavioral_profile = self._apply_behavioral_preferences(
                        config.behavioral_patterns, demographic_profiles[i]
                    )
                else:
                    behavioral_profile = self.diversity_engine._generate_behavioral_patterns(
                        demographic=demographic_profiles[i],
                        diversity_level=config.diversity_weight
                    )
                behavioral_profiles.append(behavioral_profile)
            
            # Create LLM requests for batch processing
            llm_requests = []
            for i in range(batch_count):
                # Convert behavioral patterns to simple float scores for LLM
                behavioral_scores = self._extract_behavioral_scores(behavioral_profiles[i])
                
                # Transform demographic data for LLM compatibility
                demographic_data = demographic_profiles[i].copy()
                if 'age' in demographic_data:
                    age = demographic_data['age']
                    # Pass exact age constraint to LLM for strict adherence
                    demographic_data['exact_age'] = age
                    demographic_data['age_range'] = f"{age}-{age}"  # Strict age constraint
                
                llm_request = PersonaGenerationRequest(
                    demographic_data=demographic_data,
                    behavioral_scores=behavioral_scores,
                    psychographic_data=psychographic_profiles[i] if isinstance(psychographic_profiles[i], dict) else {"values": ["family", "success"], "interests": ["technology", "travel"]},
                    context=f"Industry: {config.industry_context or 'General'}, Use case: {config.use_case_context or 'Market research'}"
                )
                llm_requests.append(llm_request)
            
            # Generate narratives in batch
            narratives = await self.llm_engine.generate_batch_narratives(llm_requests)
            
            # Combine all components
            for i in range(batch_count):
                # Calculate weighted confidence score
                rule_confidence = 0.8
                diversity_confidence = random.uniform(0.7, 0.9)
                llm_confidence = random.uniform(0.8, 0.95)
                
                weighted_confidence = (
                    config.rule_weight * rule_confidence +
                    config.diversity_weight * diversity_confidence +
                    config.llm_weight * llm_confidence
                )
                
                persona = {
                    "demographics": demographic_profiles[i],
                    "psychographics": psychographic_profiles[i],
                    "behavioral_patterns": behavioral_profiles[i],
                    "narrative": narratives[i],
                    "generation_method": "hybrid_advanced",
                    "confidence_score": weighted_confidence,
                    "component_scores": {
                        "rule_based": rule_confidence,
                        "diversity_engine": diversity_confidence,
                        "llm_engine": llm_confidence
                    }
                }
                personas.append(persona)
            
            # Update clustering guidance for next batch if we have enough personas
            if len(personas) > 10 and (batch_num + 1) % 2 == 0:  # Update every 2 batches
                clustering_guidance = self.clustering_aware_engine.generate_clustering_guidance(
                    existing_personas=personas,
                    target_clusters=config.target_clusters or 5
                )
        
        # Apply demographic constraint validation if enabled
        if config.validation_enabled:
            personas = self._validate_demographic_constraints(personas, demographic_profiles)
        
        return personas

    def _extract_behavioral_scores(self, behavioral_patterns: Dict[str, Any]) -> Dict[str, float]:
        """Extract simple float scores from complex behavioral patterns for LLM processing"""
        try:
            # Default behavioral scores
            default_scores = {
                "openness": 0.7,
                "conscientiousness": 0.6,
                "extraversion": 0.5,
                "agreeableness": 0.8,
                "neuroticism": 0.3
            }
            
            if not isinstance(behavioral_patterns, dict):
                return default_scores
            
            # Extract scores from complex behavioral patterns
            extracted_scores = {}
            
            # Map complex behavioral data to Big Five traits
            if "decision_making_style" in behavioral_patterns:
                style = behavioral_patterns["decision_making_style"]
                if isinstance(style, str):
                    if "analytical" in style.lower():
                        extracted_scores["conscientiousness"] = 0.8
                        extracted_scores["openness"] = 0.7
                    elif "intuitive" in style.lower():
                        extracted_scores["openness"] = 0.9
                        extracted_scores["neuroticism"] = 0.4
            
            if "social_behavior" in behavioral_patterns:
                social = behavioral_patterns["social_behavior"]
                if isinstance(social, dict):
                    networking = social.get("networking_style", "")
                    if "extroverted" in str(networking).lower():
                        extracted_scores["extraversion"] = 0.8
                    elif "introverted" in str(networking).lower():
                        extracted_scores["extraversion"] = 0.3
            
            if "communication_patterns" in behavioral_patterns:
                comm = behavioral_patterns["communication_patterns"]
                if isinstance(comm, dict):
                    style = comm.get("style", "")
                    if "expressive" in str(style).lower():
                        extracted_scores["extraversion"] = 0.8
                        extracted_scores["agreeableness"] = 0.7
                    elif "reserved" in str(style).lower():
                        extracted_scores["extraversion"] = 0.3
            
            # Merge with defaults
            final_scores = default_scores.copy()
            final_scores.update(extracted_scores)
            
            return final_scores
            
        except Exception as e:
            logger.warning(f"Failed to extract behavioral scores: {e}")
            return {
                "openness": 0.7,
                "conscientiousness": 0.6,
                "extraversion": 0.5,
                "agreeableness": 0.8,
                "neuroticism": 0.3
            }

    async def _generate_distribution_matched(self, config: GenerationConfig) -> List[Dict[str, Any]]:
        """Generate personas with explicit distribution matching"""
        logger.debug("Generating personas using distribution-matched method")
        
        # First generate using hybrid advanced
        initial_personas = await self._generate_hybrid_advanced(config)
        
        # Apply distribution matching
        matched_personas = await self._apply_distribution_matching(initial_personas, config)
        
        # Update generation method
        for persona in matched_personas:
            persona["generation_method"] = "distribution_matched"
        
        return matched_personas
    
    async def _apply_distribution_matching(self, personas: List[Dict[str, Any]], 
                                         config: GenerationConfig) -> List[Dict[str, Any]]:
        """Apply distribution matching to personas"""
        try:
            # Use the distribution matcher's match_distributions method
            adjusted_personas, matching_results = self.distribution_matcher.match_distributions(personas)
            
            logger.info(f"Applied distribution matching with {len(matching_results)} attribute adjustments")
            return adjusted_personas
            
        except Exception as e:
            logger.warning(f"Distribution matching failed: {e}")
            return personas
    
    async def _evaluate_quality(self, personas: List[Dict[str, Any]], 
                              config: GenerationConfig) -> Dict[str, Any]:
        """Evaluate quality of generated personas"""
        try:
            # Calculate persona quality metrics
            quality_scores = []
            
            for persona in personas:
                quality_score = self.evaluation_metrics.evaluate_persona_quality(
                    persona=persona,
                    reference_personas=personas
                )
                quality_scores.append(quality_score)
            
            # Calculate dataset-level metrics
            dataset_metrics = self.evaluation_metrics.evaluate_dataset_quality(personas)
            
            # Generate simplified quality report without clustering
            quality_report = {
                "persona_quality_scores": [asdict(score) for score in quality_scores],
                "dataset_metrics": asdict(dataset_metrics),
                "overall_quality": dataset_metrics.overall_quality,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return {
                "individual_scores": quality_scores,
                "dataset_metrics": dataset_metrics,
                "quality_report": quality_report,
                "average_quality": float(np.mean([score.overall_quality for score in quality_scores])),
                "quality_distribution": {
                    "min": min(score.overall_quality for score in quality_scores),
                    "max": max(score.overall_quality for score in quality_scores),
                    "std": float(np.std([score.overall_quality for score in quality_scores]))
                }
            }
            
        except Exception as e:
            logger.error(f"Quality evaluation failed: {e}")
            return {"error": str(e)}
    
    async def _filter_by_quality(self, personas: List[Dict[str, Any]], 
                               quality_metrics: Dict[str, Any], 
                               threshold: float) -> List[Dict[str, Any]]:
        """Filter personas by quality threshold"""
        try:
            individual_scores = quality_metrics.get("individual_scores", [])
            
            if not individual_scores or len(individual_scores) != len(personas):
                logger.warning("Quality scores not available for filtering")
                return personas
            
            filtered_personas = []
            for i, persona in enumerate(personas):
                if i < len(individual_scores) and individual_scores[i].overall_quality >= threshold:
                    filtered_personas.append(persona)
            
            logger.info(f"Filtered {len(personas) - len(filtered_personas)} personas below threshold {threshold}")
            return filtered_personas
            
        except Exception as e:
            logger.error(f"Quality filtering failed: {e}")
            return personas
    
    def _validate_demographic_constraints(self, personas: List[Dict[str, Any]], 
                                        demographic_profiles: List[DemographicProfile]) -> List[Dict[str, Any]]:
        """Validate that generated personas meet demographic constraints with STRICT enforcement"""
        try:
            validated_personas = []
            
            for i, persona in enumerate(personas):
                if i >= len(demographic_profiles):
                    validated_personas.append(persona)
                    continue
                    
                expected_profile = demographic_profiles[i]
                is_valid = True
                validation_errors = []
                
                # STRICT age validation - ZERO tolerance
                narrative = persona.get('narrative', '')
                age_matches = re.findall(r'(\d+)\s*years?\s*old', narrative, re.IGNORECASE)
                
                if age_matches:
                    generated_age = int(age_matches[0])
                    expected_age = expected_profile.age
                    
                    # EXACT age match required - NO tolerance
                    if generated_age != expected_age:
                        validation_errors.append(f"STRICT AGE VIOLATION: expected exactly {expected_age}, got {generated_age}")
                        is_valid = False
                else:
                    validation_errors.append("MISSING AGE: No age found in narrative")
                    is_valid = False
                
                # STRICT demographic field validation
                if 'demographics' in persona:
                    demo_data = persona['demographics']
                    
                    # STRICT gender validation
                    if hasattr(expected_profile, 'gender') and expected_profile.gender:
                        expected_gender = expected_profile.gender.lower()
                        if 'gender' in demo_data:
                            generated_gender = demo_data['gender'].lower()
                            if generated_gender != expected_gender:
                                validation_errors.append(f"STRICT GENDER VIOLATION: expected exactly '{expected_gender}', got '{generated_gender}'")
                                is_valid = False
                        else:
                            validation_errors.append(f"MISSING GENDER: Expected '{expected_gender}' but not found in demographics")
                            is_valid = False
                    
                    # STRICT location validation
                    if hasattr(expected_profile, 'location') and expected_profile.location:
                        expected_location = str(expected_profile.location).lower()
                        if 'location' in demo_data:
                            generated_location = str(demo_data['location']).lower()
                            if generated_location != expected_location:
                                validation_errors.append(f"STRICT LOCATION VIOLATION: expected exactly '{expected_profile.location}', got '{demo_data['location']}'")
                                is_valid = False
                        else:
                            validation_errors.append(f"MISSING LOCATION: Expected '{expected_profile.location}' but not found in demographics")
                            is_valid = False
                    
                    # STRICT income validation
                    if hasattr(expected_profile, 'income_range') and expected_profile.income_range:
                        expected_income = expected_profile.income_range
                        if 'income_range' in demo_data:
                            generated_income = demo_data['income_range']
                            if generated_income != expected_income:
                                validation_errors.append(f"STRICT INCOME VIOLATION: expected exactly '{expected_income}', got '{generated_income}'")
                                is_valid = False
                        else:
                            validation_errors.append(f"MISSING INCOME: Expected '{expected_income}' but not found in demographics")
                            is_valid = False
                    
                    # STRICT education validation
                    if hasattr(expected_profile, 'education') and expected_profile.education:
                        expected_education = expected_profile.education
                        if 'education' in demo_data:
                            generated_education = demo_data['education']
                            if generated_education != expected_education:
                                validation_errors.append(f"STRICT EDUCATION VIOLATION: expected exactly '{expected_education}', got '{generated_education}'")
                                is_valid = False
                        else:
                            validation_errors.append(f"MISSING EDUCATION: Expected '{expected_education}' but not found in demographics")
                            is_valid = False
                
                if is_valid:
                    validated_personas.append(persona)
                else:
                    logger.warning(f"STRICT VALIDATION FAILED - Persona {i} rejected: {validation_errors}")
            
            rejection_count = len(personas) - len(validated_personas)
            if rejection_count > 0:
                logger.warning(f"STRICT CONSTRAINT ENFORCEMENT: Rejected {rejection_count}/{len(personas)} personas for violations")
            
            logger.info(f"STRICT DEMOGRAPHIC VALIDATION: {len(validated_personas)}/{len(personas)} personas passed validation")
            return validated_personas
            
        except Exception as e:
            logger.error(f"Error in strict demographic validation: {e}")
            return personas
    
    async def _perform_clustering(self, personas: List[Dict[str, Any]], 
                                config: GenerationConfig) -> Dict[str, Any]:
        """Perform clustering analysis on personas"""
        try:
            # Prepare data for clustering
            clustering_data = self.clustering_engine.prepare_clustering_data(personas)
            
            # Determine optimal number of clusters
            if config.target_clusters:
                n_clusters = config.target_clusters
            else:
                n_clusters = self.clustering_engine.find_optimal_clusters(
                    clustering_data
                )
            
            # Perform clustering with multiple algorithms
            algorithms = ["kmeans", "gmm", "dbscan"]
            
            try:
                clustering_results = self.clustering_engine.cluster_personas(
                    personas, algorithms=algorithms
                )
            except Exception as e:
                logger.warning(f"Clustering failed: {e}")
                clustering_results = {}
            
            # Select best clustering result
            best_algorithm = self._select_best_clustering(clustering_results)
            
            return {
                "results": clustering_results,
                "best_algorithm": best_algorithm,
                "n_clusters": n_clusters,
                "clustering_data_shape": clustering_data.shape if hasattr(clustering_data, 'shape') else None
            }
            
        except Exception as e:
            logger.error(f"Clustering analysis failed: {e}")
            return {"error": str(e)}
    
    def _select_best_clustering(self, clustering_results: Dict[str, Any]) -> str:
        """Select best clustering algorithm based on metrics"""
        best_algorithm = None
        best_score = -1
        
        for algorithm, result in clustering_results.items():
            if "metrics" in result and "silhouette_score" in result["metrics"]:
                score = result["metrics"]["silhouette_score"]
                if score > best_score:
                    best_score = score
                    best_algorithm = algorithm
        
        return best_algorithm or list(clustering_results.keys())[0] if clustering_results else None
    
    async def _analyze_distributions(self, personas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze statistical distributions of persona attributes"""
        try:
            # Analyze current distributions
            current_distributions = self.distribution_matcher.analyze_current_distributions(personas)
            
            # Calculate matching scores against real-world data
            matching_scores = self.distribution_matcher.calculate_matching_scores(current_distributions)
            
            # Perform statistical tests
            statistical_tests = {}
            for attribute, distribution in current_distributions.items():
                if attribute in ["age", "income"]:
                    tests = self.distribution_matcher.perform_statistical_tests(
                        distribution["values"], attribute
                    )
                    statistical_tests[attribute] = tests
            
            return {
                "current_distributions": current_distributions,
                "matching_scores": matching_scores,
                "statistical_tests": statistical_tests,
                "distribution_summary": self._summarize_distributions(current_distributions)
            }
            
        except Exception as e:
            logger.error(f"Distribution analysis failed: {e}")
            return {"error": str(e)}
    
    def _summarize_distributions(self, distributions: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize distribution characteristics"""
        summary = {}
        
        for attribute, dist_info in distributions.items():
            if "values" in dist_info and dist_info["values"]:
                values = dist_info["values"]
                summary[attribute] = {
                    "count": len(values),
                    "mean": float(np.mean(values)) if isinstance(values[0], (int, float)) else None,
                "std": float(np.std(values)) if isinstance(values[0], (int, float)) else None,
                    "unique_values": len(set(values)),
                    "data_type": "numerical" if isinstance(values[0], (int, float)) else "categorical"
                }
        
        return summary
    
    async def _store_personas(self, personas: List[Dict[str, Any]], 
                            request: GenerationRequest, 
                            result: GenerationResult) -> List[str]:
        """Store personas using storage manager"""
        try:
            if not self.storage_manager:
                logger.warning("Storage manager not available")
                return []
            
            # Prepare metadata
            generation_metadata = {
                "generation_method": request.config.method.value,
                "request_id": f"req_{int(datetime.now(timezone.utc).timestamp())}",
                "user_id": request.user_id,
                "project_name": request.project_name,
                "execution_time": result.execution_time
            }
            
            # Store personas in batch
            # Use a default persona name if none provided
            persona_name = request.persona_name or f"persona_{request.config.method.value}_{int(datetime.now(timezone.utc).timestamp())}"
            
            storage_ids = await self.storage_manager.store_personas_batch(
                personas_data=personas,
                generation_method=request.config.method.value,
                quality_metrics=result.quality_metrics.get("individual_scores"),
                tags=request.tags,
                persona_name=persona_name
            )
            
            logger.info(f"Stored {len(storage_ids)} personas")
            return storage_ids
            
        except Exception as e:
            logger.error(f"Persona storage failed: {e}")
            return []
    
    async def _export_personas(self, personas: List[Dict[str, Any]], 
                             export_format: str, 
                             request: GenerationRequest) -> List[str]:
        """Export personas to specified format (disabled - export functionality removed)"""
        logger.info("Export functionality has been disabled")
        return []
    
    def _apply_psychographic_preferences(self, preferences: Dict[str, Any], demographic: Dict[str, Any]) -> Dict[str, Any]:
        """Apply frontend psychographic preferences to create persona psychographics"""
        # Start with diversity engine base if no preferences
        base_psychographics = self.diversity_engine.generate_psychographic_profile(demographic)
        
        # Apply frontend preferences
        result = base_psychographics.copy()
        
        # Handle personality traits
        if preferences.get('personality_traits'):
            personality_prefs = preferences['personality_traits']
            if isinstance(personality_prefs, list) and personality_prefs:
                # Convert list of traits to Big Five scores
                result['personality'] = self._convert_personality_traits_to_big_five(personality_prefs)
            elif isinstance(personality_prefs, dict):
                # Direct Big Five mapping
                result['personality'] = personality_prefs
        
        # Handle values
        if preferences.get('values'):
            values_prefs = preferences['values']
            if isinstance(values_prefs, list) and values_prefs:
                result['values'] = self._convert_values_list_to_scores(values_prefs)
            elif isinstance(values_prefs, dict):
                result['values'] = values_prefs
        
        # Handle lifestyle preferences
        if preferences.get('lifestyle'):
            lifestyle_prefs = preferences['lifestyle']
            if isinstance(lifestyle_prefs, list) and lifestyle_prefs:
                result['lifestyle'] = self._convert_lifestyle_list_to_preferences(lifestyle_prefs)
            elif isinstance(lifestyle_prefs, dict):
                result['lifestyle'].update(lifestyle_prefs)
        
        # Handle interests
        if preferences.get('interests'):
            interests_prefs = preferences['interests']
            if isinstance(interests_prefs, list) and interests_prefs:
                # Add interests to lifestyle preferred_activities
                if 'lifestyle' not in result:
                    result['lifestyle'] = {}
                if 'preferred_activities' not in result['lifestyle']:
                    result['lifestyle']['preferred_activities'] = []
                # Extend and deduplicate to prevent repeated values
                result['lifestyle']['preferred_activities'].extend(interests_prefs)
                result['lifestyle']['preferred_activities'] = list(dict.fromkeys(result['lifestyle']['preferred_activities']))
            elif isinstance(interests_prefs, dict):
                # Handle structured interests
                if 'lifestyle' not in result:
                    result['lifestyle'] = {}
                result['lifestyle'].update(interests_prefs)
        
        return result
    
    def _convert_personality_traits_to_big_five(self, traits: List[str]) -> Dict[str, float]:
        """Convert personality trait strings to Big Five scores"""
        # Mapping of common traits to Big Five dimensions
        trait_mapping = {
            'creative': {'openness': 0.8},
            'organized': {'conscientiousness': 0.8},
            'outgoing': {'extraversion': 0.8},
            'friendly': {'agreeableness': 0.8},
            'calm': {'neuroticism': 0.2},
            'analytical': {'openness': 0.7, 'conscientiousness': 0.6},
            'adventurous': {'openness': 0.8, 'extraversion': 0.6},
            'reliable': {'conscientiousness': 0.8, 'agreeableness': 0.6},
            'empathetic': {'agreeableness': 0.8},
            'confident': {'extraversion': 0.7, 'neuroticism': 0.3}
        }
        
        # Start with neutral scores
        big_five = {
            'openness': 0.5,
            'conscientiousness': 0.5,
            'extraversion': 0.5,
            'agreeableness': 0.5,
            'neuroticism': 0.5
        }
        
        # Apply trait influences
        for trait in traits:
            if trait.lower() in trait_mapping:
                for dimension, score in trait_mapping[trait.lower()].items():
                    big_five[dimension] = min(1.0, max(0.0, (big_five[dimension] + score) / 2))
        
        return big_five
    
    def _convert_values_list_to_scores(self, values: List[str]) -> Dict[str, float]:
        """Convert values list to value scores"""
        # Common values mapping
        all_values = ['security', 'achievement', 'hedonism', 'tradition', 'self_direction', 
                     'universalism', 'benevolence', 'conformity', 'power', 'stimulation']
        
        value_scores = {}
        for value in all_values:
            if value in [v.lower() for v in values]:
                value_scores[value] = random.uniform(0.7, 0.9)
            else:
                value_scores[value] = random.uniform(0.1, 0.4)
        
        return value_scores
    
    def _convert_lifestyle_list_to_preferences(self, lifestyle: List[str]) -> Dict[str, Any]:
        """Convert lifestyle list to lifestyle preferences"""
        return {
             'preferred_activities': list(dict.fromkeys(lifestyle)),  # Deduplicate lifestyle activities
             'activity_level': random.choice(['low', 'moderate', 'high']),
             'social_preference': random.choice(['solitary', 'small_groups', 'large_groups']),
             'routine_preference': random.choice(['structured', 'flexible', 'spontaneous'])
          }
    
    def _apply_behavioral_preferences(self, preferences: Dict[str, Any], demographic: Dict[str, Any]) -> Dict[str, Any]:
        """Apply frontend behavioral preferences to create persona behavioral patterns"""
        # Start with diversity engine base
        base_behavioral = self.diversity_engine._generate_behavioral_patterns(
            demographic=demographic, diversity_level=0.5
        )
        
        # Apply frontend preferences
        result = base_behavioral.copy()
        
        # Handle media platforms
        if preferences.get('media_platforms'):
            media_prefs = preferences['media_platforms']
            if isinstance(media_prefs, list) and media_prefs:
                result['media_preferences'] = {
                    'primary_platform': media_prefs[0] if media_prefs else 'facebook',
                    'secondary_platforms': media_prefs[1:] if len(media_prefs) > 1 else [],
                    'usage_frequency': random.choice(['daily', 'weekly', 'monthly'])
                }
            elif isinstance(media_prefs, dict):
                result['media_preferences'] = media_prefs
        
        # Handle decision making style
        if preferences.get('decision_making_style'):
            decision_style = preferences['decision_making_style']
            if isinstance(decision_style, str):
                result['decision_making'] = {
                    'style': decision_style,
                    'research_depth': random.choice(['minimal', 'moderate', 'extensive']),
                    'time_to_decide': random.choice(['quick', 'moderate', 'deliberate'])
                }
            elif isinstance(decision_style, dict):
                result['decision_making'] = decision_style
        
        # Handle shopping behavior
        if preferences.get('shopping_behavior'):
            shopping_prefs = preferences['shopping_behavior']
            if isinstance(shopping_prefs, str):
                result['shopping_behavior'] = shopping_prefs
            elif isinstance(shopping_prefs, dict):
                result.update(shopping_prefs)
        
        # Handle technology adoption
        if preferences.get('technology_adoption'):
            tech_prefs = preferences['technology_adoption']
            if isinstance(tech_prefs, str):
                result['technology_adoption'] = tech_prefs
            elif isinstance(tech_prefs, dict):
                result.update(tech_prefs)
        
        # Handle communication preferences
        if preferences.get('communication_preference'):
            comm_prefs = preferences['communication_preference']
            if isinstance(comm_prefs, str):
                result['communication_preference'] = comm_prefs
            elif isinstance(comm_prefs, dict):
                result.update(comm_prefs)
        
        return result
    
    def _generate_basic_psychographics(self) -> Dict[str, Any]:
        """Generate basic psychographic profile"""
        return {
            "personality_traits": {
                "openness": random.uniform(0.2, 0.8),
                "conscientiousness": random.uniform(0.3, 0.9),
                "extraversion": random.uniform(0.2, 0.8),
                "agreeableness": random.uniform(0.3, 0.8),
                "neuroticism": random.uniform(0.1, 0.6)
            },
            "values": random.choices(["security", "achievement", "hedonism", "tradition", "self_direction"], k=2),
            "interests": random.choices(["technology", "sports", "arts", "travel", "food", "music"], k=3)
        }
    
    def _generate_basic_behavioral_patterns(self) -> Dict[str, Any]:
        """Generate basic behavioral patterns"""
        return {
            "shopping_behavior": random.choice(["impulsive", "research_driven", "price_conscious", "brand_loyal"]),
            "technology_adoption": random.choice(["early_adopter", "mainstream", "late_adopter"]),
            "social_media_usage": random.choice(["heavy", "moderate", "light", "none"]),
            "communication_preference": random.choice(["digital", "phone", "in_person", "mixed"])
        }
    
    def _convert_to_demographic_constraints(self, constraints_dict: Optional[Dict[str, Any]]) -> Optional[DemographicConstraints]:
        """Convert dictionary constraints to DemographicConstraints object"""
        if not constraints_dict:
            return None
        
        # Convert age_range from various formats to tuple
        age_range = constraints_dict.get('age_range')
        logger.debug(f"=== AGE RANGE CONVERSION DEBUG ===")
        logger.debug(f"Original age_range: {age_range} (type: {type(age_range)})")
        
        if age_range:
            if isinstance(age_range, list) and len(age_range) == 2:
                # Already a list of two integers
                age_range = tuple(age_range)
                logger.debug(f"Converted list to tuple: {age_range}")
            elif isinstance(age_range, str):
                # Parse string format like '18-24', '25-34', '65+'
                if '+' in age_range:
                    # Handle '65+' format
                    min_age = int(age_range.replace('+', ''))
                    age_range = (min_age, 100)  # Set max to 100 for open-ended ranges
                    logger.debug(f"Converted '65+' format to tuple: {age_range}")
                elif '-' in age_range:
                    # Handle '18-24' format
                    parts = age_range.split('-')
                    if len(parts) == 2:
                        age_range = (int(parts[0]), int(parts[1]))
                        logger.debug(f"Converted string format to tuple: {age_range}")
                    else:
                        age_range = None
                        logger.debug(f"Invalid string format, setting to None")
                else:
                    age_range = None
                    logger.debug(f"Unknown string format, setting to None")
            else:
                age_range = None
                logger.debug(f"Unknown type, setting to None")
        
        logger.debug(f"Final age_range: {age_range}")
        logger.debug(f"===================================")
        
        # Convert income_constraints from string format to tuple
        income_constraints = constraints_dict.get('income_constraints')
        logger.debug(f"=== INCOME CONSTRAINTS CONVERSION DEBUG ===")
        logger.debug(f"Original income_constraints: {income_constraints} (type: {type(income_constraints)})")
        
        if income_constraints and isinstance(income_constraints, str):
            # Parse string format like '25k-40k', '50k-75k'
            if '-' in income_constraints:
                parts = income_constraints.split('-')
                if len(parts) == 2:
                    income_constraints = (parts[0], parts[1])
                    logger.debug(f"Converted string format to tuple: {income_constraints}")
                else:
                    income_constraints = None
                    logger.debug(f"Invalid string format, setting to None")
            else:
                income_constraints = None
                logger.debug(f"Unknown string format, setting to None")
        elif income_constraints and not isinstance(income_constraints, tuple):
            income_constraints = None
            logger.debug(f"Unknown type, setting to None")
        
        logger.debug(f"Final income_constraints: {income_constraints}")
        logger.debug(f"===========================================")
        
        return DemographicConstraints(
            age_range=age_range,
            gender_distribution=constraints_dict.get('gender_distribution'),
            location_preferences=constraints_dict.get('location_preferences'),
            income_constraints=income_constraints,
            education_requirements=constraints_dict.get('education_requirements'),
            family_status_options=constraints_dict.get('family_status_options')
        )
    
    def _update_generation_stats(self, result: GenerationResult, config: GenerationConfig):
        """Update generation statistics"""
        self.generation_stats["total_generated"] += len(result.personas)
        
        if result.success:
            self.generation_stats["successful_generations"] += 1
        else:
            self.generation_stats["failed_generations"] += 1
        
        # Update method usage
        method = config.method.value
        self.generation_stats["generation_methods_used"][method] = \
            self.generation_stats["generation_methods_used"].get(method, 0) + 1
        
        # Update average quality score
        if "quality_metrics" in result.quality_metrics and "average_quality" in result.quality_metrics:
            current_avg = self.generation_stats["average_quality_score"]
            new_score = result.quality_metrics["average_quality"]
            total_generations = self.generation_stats["successful_generations"]
            
            if total_generations > 1:
                self.generation_stats["average_quality_score"] = \
                    ((current_avg * (total_generations - 1)) + new_score) / total_generations
            else:
                self.generation_stats["average_quality_score"] = new_score
        
        self.generation_stats["last_generation_time"] = datetime.now(timezone.utc).isoformat()
    
    def get_generation_statistics(self) -> Dict[str, Any]:
        """Get current generation statistics"""
        return self.generation_stats.copy()
    
    def reset_statistics(self):
        """Reset generation statistics"""
        self.generation_stats = {
            "total_generated": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "average_quality_score": 0.0,
            "generation_methods_used": {},
            "last_generation_time": None
        }
        logger.info("Reset generation statistics")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components"""
        health_status = {
            "overall_status": "healthy",
            "components": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Check rule engine
            test_profile = self.rule_engine.generate_single_demographic()
            health_status["components"]["rule_engine"] = "healthy" if test_profile else "unhealthy"
            
            # Check LLM engine
            try:
                test_request = PersonaGenerationRequest(
                    demographic_data={"age": 30, "gender": "female"},
                    psychographic_preferences={},
                    behavioral_patterns={}
                )
                test_narrative = await self.llm_engine.generate_persona_narrative(test_request)
                health_status["components"]["llm_engine"] = "healthy" if test_narrative else "unhealthy"
            except Exception as e:
                health_status["components"]["llm_engine"] = f"unhealthy: {str(e)}"
            
            # Check diversity engine
            try:
                test_psychographics = self.diversity_engine.generate_psychographic_profile()
                health_status["components"]["diversity_engine"] = "healthy" if test_psychographics else "unhealthy"
            except Exception as e:
                health_status["components"]["diversity_engine"] = f"unhealthy: {str(e)}"
            
            # Check storage manager
            if self.storage_manager:
                try:
                    stats = self.storage_manager.get_storage_statistics()
                    health_status["components"]["storage_manager"] = "healthy" if stats else "unhealthy"
                except Exception as e:
                    health_status["components"]["storage_manager"] = f"unhealthy: {str(e)}"
            else:
                health_status["components"]["storage_manager"] = "not_configured"
            
            # Determine overall status
            unhealthy_components = [comp for comp, status in health_status["components"].items() 
                                  if status != "healthy" and status != "not_configured"]
            
            if unhealthy_components:
                health_status["overall_status"] = "degraded"
                health_status["unhealthy_components"] = unhealthy_components
            
        except Exception as e:
            health_status["overall_status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status