import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.preprocessing import StandardScaler
import random
import asyncio

@dataclass
class ClusterGuidance:
    """Guidance for generating personas to improve clustering"""
    target_cluster_id: int
    demographic_targets: Dict[str, Any]
    psychographic_targets: Dict[str, Any]
    behavioral_targets: Dict[str, Any]
    separation_weight: float
    diversity_requirements: Dict[str, float]

class ClusteringAwareEngine:
    """Engine for clustering-aware persona generation to improve silhouette scores"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.existing_clusters = []
        self.cluster_centroids = {}
        self.feature_importance = {}
        self.generation_history = []
        
        logger.info("Initialized ClusteringAwareEngine")
    
    def analyze_existing_clusters(self, personas: List[Dict[str, Any]], 
                                clustering_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze existing persona clusters to guide new generation"""
        try:
            if not personas:
                return {"status": "No existing personas to analyze"}
            
            # Extract features from existing personas
            features = self._extract_clustering_features(personas)
            
            if clustering_result and 'labels' in clustering_result:
                labels = clustering_result['labels']
                self._update_cluster_analysis(features, labels, personas)
            else:
                # Perform basic clustering analysis
                self._perform_basic_clustering_analysis(features, personas)
            
            # Identify gaps and opportunities
            gaps = self._identify_cluster_gaps()
            
            return {
                "cluster_count": len(self.cluster_centroids),
                "cluster_sizes": {str(k): len(v) for k, v in self.existing_clusters},
                "identified_gaps": gaps,
                "feature_importance": self.feature_importance,
                "recommendations": self._generate_cluster_recommendations(gaps)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing existing clusters: {e}")
            return {"status": "Analysis failed", "error": str(e)}
    
    def generate_cluster_guidance(self, target_cluster_count: int, 
                                existing_personas: List[Dict[str, Any]],
                                demographic_constraints: Optional[Dict[str, Any]] = None) -> List[ClusterGuidance]:
        """Generate guidance for creating personas that improve clustering"""
        guidance_list = []
        
        try:
            # Analyze current state
            analysis = self.analyze_existing_clusters(existing_personas)
            
            # Determine how many new personas needed per cluster
            current_clusters = len(self.cluster_centroids)
            personas_per_cluster = max(1, len(existing_personas) // target_cluster_count)
            
            # Generate guidance for each target cluster
            for cluster_id in range(target_cluster_count):
                guidance = self._create_cluster_guidance(
                    cluster_id, personas_per_cluster, demographic_constraints
                )
                guidance_list.append(guidance)
            
            logger.info(f"Generated {len(guidance_list)} cluster guidance entries")
            return guidance_list
            
        except Exception as e:
            logger.error(f"Error generating cluster guidance: {e}")
            return []
    
    def optimize_persona_for_clustering(self, base_persona: Dict[str, Any], 
                                      guidance: ClusterGuidance,
                                      existing_personas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize a persona to improve clustering metrics"""
        try:
            optimized_persona = base_persona.copy()
            
            # Apply demographic targets
            if guidance.demographic_targets:
                optimized_persona['demographics'] = self._apply_demographic_targets(
                    optimized_persona.get('demographics', {}), guidance.demographic_targets
                )
            
            # Apply psychographic targets
            if guidance.psychographic_targets:
                optimized_persona['psychographics'] = self._apply_psychographic_targets(
                    optimized_persona.get('psychographics', {}), guidance.psychographic_targets
                )
            
            # Apply behavioral targets
            if guidance.behavioral_targets:
                optimized_persona['behavioral_patterns'] = self._apply_behavioral_targets(
                    optimized_persona.get('behavioral_patterns', {}), guidance.behavioral_targets
                )
            
            # Ensure separation from other clusters
            optimized_persona = self._ensure_cluster_separation(
                optimized_persona, guidance, existing_personas
            )
            
            # Record optimization
            self.generation_history.append({
                'guidance_used': guidance,
                'optimization_applied': True,
                'target_cluster': guidance.target_cluster_id
            })
            
            return optimized_persona
            
        except Exception as e:
            logger.error(f"Error optimizing persona for clustering: {e}")
            return base_persona
    
    def evaluate_clustering_improvement(self, new_personas: List[Dict[str, Any]], 
                                      existing_personas: List[Dict[str, Any]]) -> Dict[str, float]:
        """Evaluate how new personas improve clustering metrics"""
        try:
            # Combine all personas
            all_personas = existing_personas + new_personas
            
            # Extract features
            all_features = self._extract_clustering_features(all_personas)
            existing_features = self._extract_clustering_features(existing_personas)
            
            # Calculate improvement metrics
            improvement = {
                'feature_diversity_improvement': self._calculate_diversity_improvement(
                    existing_features, all_features
                ),
                'separation_improvement': self._calculate_separation_improvement(
                    existing_features, all_features
                ),
                'balance_improvement': self._calculate_balance_improvement(
                    existing_personas, all_personas
                )
            }
            
            return improvement
            
        except Exception as e:
            logger.error(f"Error evaluating clustering improvement: {e}")
            return {'error': str(e)}
    
    def _extract_clustering_features(self, personas: List[Dict[str, Any]]) -> np.ndarray:
        """Extract numerical features for clustering analysis"""
        features = []
        
        for persona in personas:
            feature_vector = []
            
            # Demographic features
            demo = persona.get('demographics', {})
            feature_vector.extend([
                demo.get('age', 30),
                demo.get('income', 50000) / 100000,  # Normalize
                1 if demo.get('gender') == 'Male' else 0,
                1 if demo.get('education', '').lower() in ['bachelor', 'master', 'phd'] else 0
            ])
            
            # Psychographic features
            psycho = persona.get('psychographics', {})
            personality = psycho.get('personality_traits', {})
            feature_vector.extend([
                personality.get('openness', 0.5),
                personality.get('conscientiousness', 0.5),
                personality.get('extraversion', 0.5),
                personality.get('agreeableness', 0.5),
                personality.get('neuroticism', 0.5)
            ])
            
            # Behavioral features
            behavioral = persona.get('behavioral_patterns', {})
            feature_vector.extend([
                behavioral.get('tech_adoption_score', 0.5),
                behavioral.get('social_media_usage', 0.5),
                behavioral.get('shopping_frequency', 0.5)
            ])
            
            features.append(feature_vector)
        
        return np.array(features)
    
    def _update_cluster_analysis(self, features: np.ndarray, labels: List[int], 
                               personas: List[Dict[str, Any]]):
        """Update cluster analysis with new data"""
        self.existing_clusters = {}
        self.cluster_centroids = {}
        
        for cluster_id in set(labels):
            if cluster_id == -1:  # Skip noise
                continue
            
            cluster_indices = [i for i, label in enumerate(labels) if label == cluster_id]
            cluster_features = features[cluster_indices]
            cluster_personas = [personas[i] for i in cluster_indices]
            
            self.existing_clusters[cluster_id] = cluster_personas
            self.cluster_centroids[cluster_id] = np.mean(cluster_features, axis=0).tolist()
    
    def _perform_basic_clustering_analysis(self, features: np.ndarray, personas: List[Dict[str, Any]]):
        """Perform basic clustering analysis when no clustering result provided"""
        # Simple k-means-like analysis
        from sklearn.cluster import KMeans
        
        n_clusters = min(5, max(2, len(personas) // 10))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(features)
        
        self._update_cluster_analysis(features, labels.tolist(), personas)
    
    def _identify_cluster_gaps(self) -> List[Dict[str, Any]]:
        """Identify gaps in current clustering"""
        gaps = []
        
        if not self.cluster_centroids:
            return [{"type": "no_clusters", "description": "No existing clusters found"}]
        
        # Check for imbalanced clusters
        cluster_sizes = [len(personas) for personas in self.existing_clusters.values()]
        avg_size = float(np.mean(cluster_sizes))
        
        for cluster_id, size in enumerate(cluster_sizes):
            if size < avg_size * 0.5:
                gaps.append({
                    "type": "undersized_cluster",
                    "cluster_id": cluster_id,
                    "current_size": size,
                    "recommended_size": int(avg_size)
                })
        
        # Check for feature space gaps
        centroids = list(self.cluster_centroids.values())
        if len(centroids) > 1:
            distances = euclidean_distances(centroids)
            min_distance = float(np.min(distances[distances > 0]))
            
            if min_distance < 0.5:  # Clusters too close
                gaps.append({
                    "type": "clusters_too_close",
                    "min_distance": min_distance,
                    "recommendation": "Increase separation between clusters"
                })
        
        return gaps
    
    def _generate_cluster_recommendations(self, gaps: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations based on identified gaps"""
        recommendations = []
        
        for gap in gaps:
            if gap["type"] == "undersized_cluster":
                recommendations.append(
                    f"Generate {gap['recommended_size'] - gap['current_size']} more personas for cluster {gap['cluster_id']}"
                )
            elif gap["type"] == "clusters_too_close":
                recommendations.append(
                    "Create personas with more diverse characteristics to improve cluster separation"
                )
            elif gap["type"] == "no_clusters":
                recommendations.append(
                    "Generate initial diverse personas to establish distinct clusters"
                )
        
        return recommendations
    
    def _create_cluster_guidance(self, cluster_id: int, target_size: int, 
                               constraints: Optional[Dict[str, Any]]) -> ClusterGuidance:
        """Create guidance for a specific cluster"""
        # Define diverse demographic targets for different clusters
        demographic_variations = [
            {"age_range": (25, 35), "income_range": (40000, 80000), "education": "bachelor"},
            {"age_range": (35, 50), "income_range": (60000, 120000), "education": "master"},
            {"age_range": (18, 30), "income_range": (25000, 50000), "education": "high_school"},
            {"age_range": (45, 65), "income_range": (80000, 150000), "education": "phd"},
            {"age_range": (30, 45), "income_range": (50000, 90000), "education": "bachelor"}
        ]
        
        # Psychographic variations
        psychographic_variations = [
            {"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.7},
            {"openness": 0.4, "conscientiousness": 0.8, "extraversion": 0.3},
            {"openness": 0.6, "conscientiousness": 0.4, "extraversion": 0.8},
            {"openness": 0.9, "conscientiousness": 0.5, "extraversion": 0.5},
            {"openness": 0.3, "conscientiousness": 0.9, "extraversion": 0.4}
        ]
        
        # Behavioral variations
        behavioral_variations = [
            {"tech_adoption_score": 0.9, "social_media_usage": 0.8, "shopping_frequency": 0.6},
            {"tech_adoption_score": 0.3, "social_media_usage": 0.2, "shopping_frequency": 0.4},
            {"tech_adoption_score": 0.7, "social_media_usage": 0.9, "shopping_frequency": 0.8},
            {"tech_adoption_score": 0.5, "social_media_usage": 0.4, "shopping_frequency": 0.3},
            {"tech_adoption_score": 0.8, "social_media_usage": 0.6, "shopping_frequency": 0.7}
        ]
        
        variation_index = cluster_id % len(demographic_variations)
        
        return ClusterGuidance(
            target_cluster_id=cluster_id,
            demographic_targets=demographic_variations[variation_index],
            psychographic_targets=psychographic_variations[variation_index],
            behavioral_targets=behavioral_variations[variation_index],
            separation_weight=0.7,
            diversity_requirements={"min_distance": 0.3, "max_similarity": 0.8}
        )
    
    def _apply_demographic_targets(self, current_demo: Dict[str, Any], 
                                 targets: Dict[str, Any]) -> Dict[str, Any]:
        """Apply demographic targets to persona"""
        updated_demo = current_demo.copy()
        
        if "age_range" in targets:
            age_min, age_max = targets["age_range"]
            updated_demo["age"] = random.randint(age_min, age_max)
        
        if "income_range" in targets:
            income_min, income_max = targets["income_range"]
            updated_demo["income"] = random.randint(income_min, income_max)
        
        if "education" in targets:
            updated_demo["education"] = targets["education"]
        
        return updated_demo
    
    def _apply_psychographic_targets(self, current_psycho: Dict[str, Any], 
                                   targets: Dict[str, Any]) -> Dict[str, Any]:
        """Apply psychographic targets to persona"""
        updated_psycho = current_psycho.copy()
        
        if "personality_traits" not in updated_psycho:
            updated_psycho["personality_traits"] = {}
        
        for trait, value in targets.items():
            updated_psycho["personality_traits"][trait] = value
        
        return updated_psycho
    
    def _apply_behavioral_targets(self, current_behavioral: Dict[str, Any], 
                                targets: Dict[str, Any]) -> Dict[str, Any]:
        """Apply behavioral targets to persona"""
        updated_behavioral = current_behavioral.copy()
        
        for behavior, value in targets.items():
            updated_behavioral[behavior] = value
        
        return updated_behavioral
    
    def _ensure_cluster_separation(self, persona: Dict[str, Any], 
                                 guidance: ClusterGuidance,
                                 existing_personas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ensure persona maintains good separation from other clusters"""
        if not self.cluster_centroids or len(self.cluster_centroids) <= 1:
            return persona
        
        # Extract features for the new persona
        persona_features = self._extract_clustering_features([persona])[0]
        
        # Check distance to other cluster centroids
        for other_cluster_id, centroid in self.cluster_centroids.items():
            if other_cluster_id == guidance.target_cluster_id:
                continue
            
            distance = euclidean_distances([persona_features], [centroid])[0][0]
            
            if distance < guidance.diversity_requirements.get("min_distance", 0.3):
                # Adjust persona to increase separation
                persona = self._adjust_for_separation(persona, centroid, persona_features)
        
        return persona
    
    def _adjust_for_separation(self, persona: Dict[str, Any], 
                             other_centroid: np.ndarray,
                             persona_features: np.ndarray) -> Dict[str, Any]:
        """Adjust persona characteristics to increase separation from other clusters"""
        # Simple adjustment: modify the most different features
        diff = persona_features - other_centroid
        max_diff_idx = np.argmax(np.abs(diff))
        
        # Map feature index back to persona attribute and adjust
        if max_diff_idx < 4:  # Demographic features
            if max_diff_idx == 0:  # Age
                current_age = persona.get('demographics', {}).get('age', 30)
                persona['demographics']['age'] = max(18, min(65, current_age + (10 if diff[0] > 0 else -10)))
        
        return persona
    
    def _calculate_diversity_improvement(self, old_features: np.ndarray, 
                                       new_features: np.ndarray) -> float:
        """Calculate improvement in feature diversity"""
        old_std = float(np.std(old_features, axis=0).mean())
        new_std = float(np.std(new_features, axis=0).mean())
        return (new_std - old_std) / max(old_std, 0.001)
    
    def _calculate_separation_improvement(self, old_features: np.ndarray, 
                                        new_features: np.ndarray) -> float:
        """Calculate improvement in cluster separation"""
        if len(old_features) < 2 or len(new_features) < 2:
            return 0.0
        
        old_distances = euclidean_distances(old_features)
        new_distances = euclidean_distances(new_features)
        
        old_avg_distance = float(np.mean(old_distances[old_distances > 0]))
        new_avg_distance = float(np.mean(new_distances[new_distances > 0]))
        
        return (new_avg_distance - old_avg_distance) / max(old_avg_distance, 0.001)
    
    def _calculate_balance_improvement(self, old_personas: List[Dict[str, Any]], 
                                     new_personas: List[Dict[str, Any]]) -> float:
        """Calculate improvement in cluster balance"""
        # Simple balance metric based on demographic distribution
        old_ages = [p.get('demographics', {}).get('age', 30) for p in old_personas]
        new_ages = [p.get('demographics', {}).get('age', 30) for p in new_personas]
        
        old_age_std = float(np.std(old_ages))
        new_age_std = float(np.std(new_ages))
        
        return (new_age_std - old_age_std) / max(old_age_std, 0.001)
    
    def generate_clustering_guidance(self, existing_personas: List[Dict[str, Any]],
                                   target_clusters: int = 5,
                                   demographic_constraints: Optional[Dict[str, Any]] = None) -> List[ClusterGuidance]:
        """Generate clustering guidance for persona generation"""
        try:
            return self.generate_cluster_guidance(
                target_cluster_count=target_clusters,
                existing_personas=existing_personas,
                demographic_constraints=demographic_constraints
            )
        except Exception as e:
            logger.error(f"Error generating clustering guidance: {e}")
            return []
    
    def get_clustering_performance(self) -> Dict[str, Any]:
        """Get performance metrics of clustering-aware generation"""
        return {
            "total_optimizations": len(self.generation_history),
            "cluster_count": len(self.cluster_centroids),
            "average_cluster_size": float(np.mean([len(personas) for personas in self.existing_clusters.values()])) if self.existing_clusters else 0,
            "optimization_history": self.generation_history[-10:]  # Last 10 optimizations
        }