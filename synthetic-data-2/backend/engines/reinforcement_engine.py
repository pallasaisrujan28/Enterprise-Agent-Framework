import numpy as np
import pandas as pd
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import pickle
import os

@dataclass
class ReinforcementFeedback:
    """Feedback data for reinforcement learning"""
    silhouette_score: float
    cluster_separation: float
    demographic_adherence: float
    generation_parameters: Dict[str, Any]
    persona_features: List[Dict[str, Any]]
    timestamp: str
    success_rate: float

class ReinforcementLearningEngine:
    """Reinforcement learning engine to improve persona generation based on feedback"""
    
    def __init__(self, feedback_storage_path: str = "data/rl_feedback"):
        self.feedback_storage_path = feedback_storage_path
        self.feedback_history: List[ReinforcementFeedback] = []
        self.parameter_weights = {
            'diversity_weight': 0.3,
            'llm_weight': 0.4,
            'rule_weight': 0.3,
            'quality_threshold': 0.3,
            'age_tolerance': 1.0,
            'clustering_preference': 0.5
        }
        self.learning_rate = 0.1
        self.exploration_rate = 0.2
        self.min_feedback_samples = 5
        
        # Ensure storage directory exists
        os.makedirs(feedback_storage_path, exist_ok=True)
        self._load_feedback_history()
    
    def record_feedback(self, 
                       personas: List[Dict[str, Any]], 
                       clustering_results: Dict[str, Any],
                       generation_config: Dict[str, Any],
                       demographic_profiles: List[Any]) -> ReinforcementFeedback:
        """Record feedback from a generation session"""
        try:
            # Calculate silhouette score
            silhouette = clustering_results.get('silhouette_score', 0.0)
            
            # Calculate cluster separation (average distance between cluster centers)
            cluster_separation = self._calculate_cluster_separation(clustering_results)
            
            # Calculate demographic adherence rate
            demographic_adherence = self._calculate_demographic_adherence(personas, demographic_profiles)
            
            # Extract persona features for learning
            persona_features = self._extract_persona_features(personas)
            
            # Calculate overall success rate
            success_rate = self._calculate_success_rate(silhouette, cluster_separation, demographic_adherence)
            
            feedback = ReinforcementFeedback(
                silhouette_score=silhouette,
                cluster_separation=cluster_separation,
                demographic_adherence=demographic_adherence,
                generation_parameters=generation_config.copy(),
                persona_features=persona_features,
                timestamp=str(pd.Timestamp.now()),
                success_rate=success_rate
            )
            
            self.feedback_history.append(feedback)
            self._save_feedback(feedback)
            
            logger.info(f"Recorded RL feedback: silhouette={silhouette:.3f}, separation={cluster_separation:.3f}, adherence={demographic_adherence:.3f}")
            return feedback
            
        except Exception as e:
            logger.error(f"Error recording RL feedback: {e}")
            return None
    
    def optimize_parameters(self) -> Dict[str, Any]:
        """Optimize generation parameters based on feedback history"""
        try:
            if len(self.feedback_history) < self.min_feedback_samples:
                logger.info(f"Insufficient feedback samples ({len(self.feedback_history)}) for optimization")
                return self.parameter_weights.copy()
            
            # Analyze successful vs unsuccessful generations
            successful_feedback = [f for f in self.feedback_history if f.success_rate > 0.6]
            unsuccessful_feedback = [f for f in self.feedback_history if f.success_rate <= 0.6]
            
            if not successful_feedback:
                logger.warning("No successful generations found for optimization")
                return self.parameter_weights.copy()
            
            # Calculate optimal parameter ranges from successful generations
            optimized_params = self._calculate_optimal_parameters(successful_feedback)
            
            # Apply learning rate to gradually adjust parameters
            for param, optimal_value in optimized_params.items():
                if param in self.parameter_weights:
                    current_value = self.parameter_weights[param]
                    adjusted_value = current_value + self.learning_rate * (optimal_value - current_value)
                    self.parameter_weights[param] = max(0.1, min(1.0, adjusted_value))  # Clamp values
            
            # Add exploration noise
            if np.random.random() < self.exploration_rate:
                self._add_exploration_noise()
            
            logger.info(f"Optimized parameters: {self.parameter_weights}")
            return self.parameter_weights.copy()
            
        except Exception as e:
            logger.error(f"Error optimizing parameters: {e}")
            return self.parameter_weights.copy()
    
    def get_adaptive_config(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get adaptive configuration based on learned parameters"""
        try:
            optimized_params = self.optimize_parameters()
            
            # Apply optimized parameters to base config
            adaptive_config = base_config.copy()
            
            if 'diversity_weight' in optimized_params:
                adaptive_config['diversity_weight'] = optimized_params['diversity_weight']
            if 'llm_weight' in optimized_params:
                adaptive_config['llm_weight'] = optimized_params['llm_weight']
            if 'rule_weight' in optimized_params:
                adaptive_config['rule_weight'] = optimized_params['rule_weight']
            if 'quality_threshold' in optimized_params:
                adaptive_config['quality_threshold'] = optimized_params['quality_threshold']
            
            return adaptive_config
            
        except Exception as e:
            logger.error(f"Error creating adaptive config: {e}")
            return base_config
    
    def _calculate_cluster_separation(self, clustering_results: Dict[str, Any]) -> float:
        """Calculate average separation between cluster centers"""
        try:
            if 'cluster_centers' not in clustering_results:
                return 0.0
            
            centers = clustering_results['cluster_centers']
            if len(centers) < 2:
                return 0.0
            
            distances = []
            for i in range(len(centers)):
                for j in range(i + 1, len(centers)):
                    dist = np.linalg.norm(np.array(centers[i]) - np.array(centers[j]))
                    distances.append(dist)
            
            return float(np.mean(distances)) if distances else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating cluster separation: {e}")
            return 0.0
    
    def _calculate_demographic_adherence(self, personas: List[Dict[str, Any]], 
                                       demographic_profiles: List[Any]) -> float:
        """Calculate how well personas adhere to demographic constraints"""
        try:
            if not personas or not demographic_profiles:
                return 0.0
            
            adherent_count = 0
            total_count = min(len(personas), len(demographic_profiles))
            
            for i in range(total_count):
                persona = personas[i]
                expected_profile = demographic_profiles[i]
                
                # Check age adherence
                narrative = persona.get('narrative', '')
                age_matches = re.findall(r'(\d+)\s*years?\s*old', narrative, re.IGNORECASE)
                
                if age_matches:
                    generated_age = int(age_matches[0])
                    expected_age = expected_profile.age
                    
                    if abs(generated_age - expected_age) <= 1:  # Allow 1 year tolerance
                        adherent_count += 1
            
            return adherent_count / total_count if total_count > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating demographic adherence: {e}")
            return 0.0
    
    def _extract_persona_features(self, personas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract key features from personas for learning"""
        try:
            features = []
            
            for persona in personas:
                feature_dict = {
                    'confidence_score': persona.get('confidence_score', 0.0),
                    'narrative_length': len(persona.get('narrative', '')),
                    'has_demographics': 'demographics' in persona,
                    'has_psychographics': 'psychographics' in persona,
                    'has_behavioral_patterns': 'behavioral_patterns' in persona,
                    'generation_method': persona.get('generation_method', 'unknown')
                }
                
                # Extract component scores if available
                if 'component_scores' in persona:
                    component_scores = persona['component_scores']
                    feature_dict.update({
                        'rule_based_score': component_scores.get('rule_based', 0.0),
                        'diversity_score': component_scores.get('diversity_engine', 0.0),
                        'llm_score': component_scores.get('llm_engine', 0.0)
                    })
                
                features.append(feature_dict)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting persona features: {e}")
            return []
    
    def _calculate_success_rate(self, silhouette: float, separation: float, adherence: float) -> float:
        """Calculate overall success rate from metrics"""
        try:
            # Weighted combination of metrics
            weights = {'silhouette': 0.4, 'separation': 0.3, 'adherence': 0.3}
            
            # Normalize metrics to 0-1 range
            normalized_silhouette = max(0, min(1, (silhouette + 1) / 2))  # silhouette is -1 to 1
            normalized_separation = max(0, min(1, separation / 10))  # assume max separation of 10
            normalized_adherence = adherence  # already 0-1
            
            success_rate = (
                weights['silhouette'] * normalized_silhouette +
                weights['separation'] * normalized_separation +
                weights['adherence'] * normalized_adherence
            )
            
            return success_rate
            
        except Exception as e:
            logger.error(f"Error calculating success rate: {e}")
            return 0.0
    
    def _calculate_optimal_parameters(self, successful_feedback: List[ReinforcementFeedback]) -> Dict[str, float]:
        """Calculate optimal parameters from successful generations"""
        try:
            param_values = {
                'diversity_weight': [],
                'llm_weight': [],
                'rule_weight': [],
                'quality_threshold': []
            }
            
            for feedback in successful_feedback:
                params = feedback.generation_parameters
                for param in param_values.keys():
                    if param in params:
                        param_values[param].append(params[param])
            
            # Calculate mean of successful parameter values
            optimal_params = {}
            for param, values in param_values.items():
                if values:
                    optimal_params[param] = float(np.mean(values))
            
            return optimal_params
            
        except Exception as e:
            logger.error(f"Error calculating optimal parameters: {e}")
            return {}
    
    def _add_exploration_noise(self):
        """Add small random noise to parameters for exploration"""
        try:
            noise_scale = 0.05
            for param in self.parameter_weights:
                noise = np.random.normal(0, noise_scale)
                self.parameter_weights[param] += noise
                self.parameter_weights[param] = max(0.1, min(1.0, self.parameter_weights[param]))
            
        except Exception as e:
            logger.error(f"Error adding exploration noise: {e}")
    
    def _save_feedback(self, feedback: ReinforcementFeedback):
        """Save feedback to persistent storage"""
        try:
            filename = f"feedback_{feedback.timestamp.replace(':', '-').replace(' ', '_')}.json"
            filepath = os.path.join(self.feedback_storage_path, filename)
            
            feedback_dict = {
                'silhouette_score': feedback.silhouette_score,
                'cluster_separation': feedback.cluster_separation,
                'demographic_adherence': feedback.demographic_adherence,
                'generation_parameters': feedback.generation_parameters,
                'persona_features': feedback.persona_features,
                'timestamp': feedback.timestamp,
                'success_rate': feedback.success_rate
            }
            
            with open(filepath, 'w') as f:
                json.dump(feedback_dict, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
    
    def _load_feedback_history(self):
        """Load feedback history from persistent storage"""
        try:
            if not os.path.exists(self.feedback_storage_path):
                return
            
            for filename in os.listdir(self.feedback_storage_path):
                if filename.startswith('feedback_') and filename.endswith('.json'):
                    filepath = os.path.join(self.feedback_storage_path, filename)
                    
                    try:
                        with open(filepath, 'r') as f:
                            feedback_dict = json.load(f)
                        
                        feedback = ReinforcementFeedback(
                            silhouette_score=feedback_dict['silhouette_score'],
                            cluster_separation=feedback_dict['cluster_separation'],
                            demographic_adherence=feedback_dict['demographic_adherence'],
                            generation_parameters=feedback_dict['generation_parameters'],
                            persona_features=feedback_dict['persona_features'],
                            timestamp=feedback_dict['timestamp'],
                            success_rate=feedback_dict['success_rate']
                        )
                        
                        self.feedback_history.append(feedback)
                        
                    except Exception as e:
                        logger.warning(f"Error loading feedback file {filename}: {e}")
            
            logger.info(f"Loaded {len(self.feedback_history)} feedback records")
            
        except Exception as e:
            logger.error(f"Error loading feedback history: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of performance metrics"""
        try:
            if not self.feedback_history:
                return {'status': 'no_data'}
            
            recent_feedback = self.feedback_history[-10:]  # Last 10 generations
            
            avg_silhouette = float(np.mean([f.silhouette_score for f in recent_feedback]))
            avg_separation = float(np.mean([f.cluster_separation for f in recent_feedback]))
            avg_adherence = float(np.mean([f.demographic_adherence for f in recent_feedback]))
            avg_success = float(np.mean([f.success_rate for f in recent_feedback]))
            
            return {
                'status': 'active',
                'total_feedback_records': len(self.feedback_history),
                'recent_performance': {
                    'avg_silhouette_score': avg_silhouette,
                    'avg_cluster_separation': avg_separation,
                    'avg_demographic_adherence': avg_adherence,
                    'avg_success_rate': avg_success
                },
                'current_parameters': self.parameter_weights.copy(),
                'learning_rate': self.learning_rate,
                'exploration_rate': self.exploration_rate
            }
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {e}")
            return {'status': 'error', 'message': str(e)}