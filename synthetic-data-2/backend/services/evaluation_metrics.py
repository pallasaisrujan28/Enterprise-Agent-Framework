import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional, Union
from dataclasses import dataclass, asdict
from sklearn.metrics import (
    silhouette_score, silhouette_samples,
    calinski_harabasz_score, davies_bouldin_score,
    adjusted_rand_score, normalized_mutual_info_score,
    homogeneity_score, completeness_score, v_measure_score
)
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy import stats
from scipy.spatial.distance import pdist, squareform
from scipy.stats import entropy
import matplotlib.pyplot as plt
import seaborn as sns
from loguru import logger
import json
from collections import defaultdict, Counter
import warnings
warnings.filterwarnings('ignore')

@dataclass
class ClusteringMetrics:
    """Comprehensive clustering evaluation metrics"""
    # Internal validation metrics
    silhouette_score: float
    silhouette_samples: List[float]
    calinski_harabasz_score: float
    davies_bouldin_score: float
    
    # Elbow method metrics
    wcss: float  # Within-Cluster Sum of Squares
    elbow_score: float
    
    # Diversity metrics
    diversity_index: float
    entropy_score: float
    gini_coefficient: float
    
    # Stability metrics
    bootstrap_stability: float
    consensus_score: float
    
    # Custom persona-specific metrics
    demographic_balance: float
    psychographic_diversity: float
    behavioral_coherence: float
    
    # Quality indicators
    cluster_separation: float
    cluster_compactness: float
    noise_ratio: float
    
    # Meta information
    n_clusters: int
    n_samples: int
    algorithm_used: str
    feature_count: int

@dataclass
class PersonaQualityMetrics:
    """Quality metrics for individual personas"""
    completeness_score: float
    consistency_score: float
    realism_score: float
    uniqueness_score: float
    demographic_validity: float
    psychographic_coherence: float
    behavioral_alignment: float
    overall_quality: float

@dataclass
class DatasetMetrics:
    """Metrics for the entire persona dataset"""
    total_personas: int
    demographic_coverage: Dict[str, float]
    diversity_scores: Dict[str, float]
    distribution_quality: Dict[str, float]
    bias_indicators: Dict[str, float]
    representativeness: float
    overall_quality: float

class EvaluationMetrics:
    """Comprehensive evaluation system for persona clustering and quality assessment"""
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.evaluation_history = []
        
        # Quality thresholds
        self.quality_thresholds = {
            "silhouette_excellent": 0.7,
            "silhouette_good": 0.5,
            "silhouette_fair": 0.25,
            "diversity_high": 0.8,
            "diversity_medium": 0.5,
            "stability_high": 0.8,
            "stability_medium": 0.6
        }
        
        logger.info("Initialized Evaluation Metrics system")
    
    def evaluate_clustering(self, feature_matrix: np.ndarray, labels: np.ndarray, 
                          personas: List[Dict[str, Any]], algorithm: str = "unknown") -> ClusteringMetrics:
        """Comprehensive clustering evaluation"""
        logger.info(f"Evaluating clustering with {len(set(labels))} clusters")
        
        # Basic metrics
        silhouette_avg = self._calculate_silhouette_score(feature_matrix, labels)
        silhouette_samples_scores = self._calculate_silhouette_samples(feature_matrix, labels)
        calinski_harabasz = self._calculate_calinski_harabasz_score(feature_matrix, labels)
        davies_bouldin = self._calculate_davies_bouldin_score(feature_matrix, labels)
        
        # WCSS and elbow metrics
        wcss = self._calculate_wcss(feature_matrix, labels)
        elbow_score = self._calculate_elbow_score(feature_matrix, labels)
        
        # Diversity metrics
        diversity_index = self._calculate_diversity_index(personas, labels)
        entropy_score = self._calculate_entropy_score(labels)
        gini_coefficient = self._calculate_gini_coefficient(labels)
        
        # Stability metrics
        bootstrap_stability = self._calculate_bootstrap_stability(feature_matrix, labels, algorithm)
        consensus_score = self._calculate_consensus_score(feature_matrix, labels)
        
        # Persona-specific metrics
        demographic_balance = self._calculate_demographic_balance(personas, labels)
        psychographic_diversity = self._calculate_psychographic_diversity(personas, labels)
        behavioral_coherence = self._calculate_behavioral_coherence(personas, labels)
        
        # Quality indicators
        cluster_separation = self._calculate_cluster_separation(feature_matrix, labels)
        cluster_compactness = self._calculate_cluster_compactness(feature_matrix, labels)
        noise_ratio = self._calculate_noise_ratio(labels)
        
        metrics = ClusteringMetrics(
            silhouette_score=silhouette_avg,
            silhouette_samples=silhouette_samples_scores,
            calinski_harabasz_score=calinski_harabasz,
            davies_bouldin_score=davies_bouldin,
            wcss=wcss,
            elbow_score=elbow_score,
            diversity_index=diversity_index,
            entropy_score=entropy_score,
            gini_coefficient=gini_coefficient,
            bootstrap_stability=bootstrap_stability,
            consensus_score=consensus_score,
            demographic_balance=demographic_balance,
            psychographic_diversity=psychographic_diversity,
            behavioral_coherence=behavioral_coherence,
            cluster_separation=cluster_separation,
            cluster_compactness=cluster_compactness,
            noise_ratio=noise_ratio,
            n_clusters=len(set(labels)) - (1 if -1 in labels else 0),
            n_samples=len(labels),
            algorithm_used=algorithm,
            feature_count=feature_matrix.shape[1]
        )
        
        # Store evaluation
        self.evaluation_history.append({
            "timestamp": pd.Timestamp.now(),
            "metrics": asdict(metrics),
            "algorithm": algorithm
        })
        
        logger.info(f"Clustering evaluation completed. Silhouette score: {silhouette_avg:.3f}")
        return metrics
    
    def evaluate_persona_quality(self, persona: Dict[str, Any], 
                               reference_personas: List[Dict[str, Any]] = None) -> PersonaQualityMetrics:
        """Evaluate the quality of an individual persona"""
        # Completeness: How complete is the persona profile
        completeness_score = self._calculate_persona_completeness(persona)
        
        # Consistency: Internal consistency of attributes
        consistency_score = self._calculate_persona_consistency(persona)
        
        # Realism: How realistic are the attribute combinations
        realism_score = self._calculate_persona_realism(persona)
        
        # Uniqueness: How unique is this persona compared to others
        uniqueness_score = self._calculate_persona_uniqueness(persona, reference_personas or [])
        
        # Demographic validity
        demographic_validity = self._calculate_demographic_validity(persona)
        
        # Psychographic coherence
        psychographic_coherence = self._calculate_psychographic_coherence(persona)
        
        # Behavioral alignment
        behavioral_alignment = self._calculate_behavioral_alignment(persona)
        
        # Overall quality score
        overall_quality = float(np.mean([
            completeness_score, consistency_score, realism_score,
            demographic_validity, psychographic_coherence, behavioral_alignment
        ]))
        
        return PersonaQualityMetrics(
            completeness_score=completeness_score,
            consistency_score=consistency_score,
            realism_score=realism_score,
            uniqueness_score=uniqueness_score,
            demographic_validity=demographic_validity,
            psychographic_coherence=psychographic_coherence,
            behavioral_alignment=behavioral_alignment,
            overall_quality=overall_quality
        )
    
    def evaluate_dataset_quality(self, personas: List[Dict[str, Any]]) -> DatasetMetrics:
        """Evaluate the quality of the entire persona dataset"""
        total_personas = len(personas)
        
        # Demographic coverage
        demographic_coverage = self._calculate_demographic_coverage(personas)
        
        # Diversity scores
        diversity_scores = self._calculate_dataset_diversity(personas)
        
        # Distribution quality
        distribution_quality = self._calculate_distribution_quality(personas)
        
        # Bias indicators
        bias_indicators = self._calculate_bias_indicators(personas)
        
        # Representativeness
        representativeness = self._calculate_representativeness(personas)
        
        # Overall quality
        overall_quality = float(np.mean([
            float(np.mean(list(demographic_coverage.values()))),
        float(np.mean(list(diversity_scores.values()))),
        float(np.mean(list(distribution_quality.values()))),
        1 - float(np.mean(list(bias_indicators.values()))),  # Invert bias
            representativeness
        ]))
        
        return DatasetMetrics(
            total_personas=total_personas,
            demographic_coverage=demographic_coverage,
            diversity_scores=diversity_scores,
            distribution_quality=distribution_quality,
            bias_indicators=bias_indicators,
            representativeness=representativeness,
            overall_quality=overall_quality
        )
    
    # Internal validation metrics
    def _calculate_silhouette_score(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate average silhouette score"""
        try:
            if len(set(labels)) > 1 and len(set(labels)) < len(labels):
                return silhouette_score(feature_matrix, labels)
            else:
                return -1.0
        except Exception as e:
            logger.warning(f"Error calculating silhouette score: {e}")
            return -1.0
    
    def _calculate_silhouette_samples(self, feature_matrix: np.ndarray, labels: np.ndarray) -> List[float]:
        """Calculate silhouette score for each sample"""
        try:
            if len(set(labels)) > 1 and len(set(labels)) < len(labels):
                return silhouette_samples(feature_matrix, labels).tolist()
            else:
                return [-1.0] * len(labels)
        except Exception as e:
            logger.warning(f"Error calculating silhouette samples: {e}")
            return [-1.0] * len(labels)
    
    def _calculate_calinski_harabasz_score(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate Calinski-Harabasz score"""
        try:
            if len(set(labels)) > 1:
                return calinski_harabasz_score(feature_matrix, labels)
            else:
                return 0.0
        except Exception as e:
            logger.warning(f"Error calculating Calinski-Harabasz score: {e}")
            return 0.0
    
    def _calculate_davies_bouldin_score(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate Davies-Bouldin score"""
        try:
            if len(set(labels)) > 1:
                return davies_bouldin_score(feature_matrix, labels)
            else:
                return float('inf')
        except Exception as e:
            logger.warning(f"Error calculating Davies-Bouldin score: {e}")
            return float('inf')
    
    # WCSS and Elbow method
    def _calculate_wcss(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate Within-Cluster Sum of Squares"""
        wcss = 0.0
        
        for cluster_id in set(labels):
            if cluster_id == -1:  # Skip noise
                continue
            
            cluster_points = feature_matrix[labels == cluster_id]
            if len(cluster_points) > 0:
                centroid = np.mean(cluster_points, axis=0)
                wcss += float(np.sum((cluster_points - centroid) ** 2))
        
        return wcss
    
    def _calculate_elbow_score(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate elbow score for current clustering"""
        try:
            # Calculate WCSS for different k values around current k
            current_k = len(set(labels)) - (1 if -1 in labels else 0)
            
            if current_k < 2:
                return 0.0
            
            wcss_values = []
            k_range = range(max(2, current_k - 2), min(current_k + 3, len(feature_matrix)))
            
            for k in k_range:
                kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
                temp_labels = kmeans.fit_predict(feature_matrix)
                wcss = self._calculate_wcss(feature_matrix, temp_labels)
                wcss_values.append(wcss)
            
            # Calculate elbow score using second derivative
            if len(wcss_values) >= 3:
                # Find position of current k in the range
                current_pos = current_k - min(k_range)
                if 0 <= current_pos < len(wcss_values):
                    if current_pos > 0 and current_pos < len(wcss_values) - 1:
                        second_deriv = wcss_values[current_pos-1] - 2*wcss_values[current_pos] + wcss_values[current_pos+1]
                        return abs(second_deriv) / max(wcss_values)
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating elbow score: {e}")
            return 0.0
    
    # Diversity metrics
    def _calculate_diversity_index(self, personas: List[Dict[str, Any]], labels: np.ndarray) -> float:
        """Calculate Simpson's diversity index for clusters"""
        cluster_counts = Counter(labels)
        total = len(labels)
        
        if total == 0:
            return 0.0
        
        # Simpson's diversity index: 1 - sum(pi^2)
        diversity = 1 - sum((count / total) ** 2 for count in cluster_counts.values())
        return diversity
    
    def _calculate_entropy_score(self, labels: np.ndarray) -> float:
        """Calculate entropy of cluster distribution"""
        cluster_counts = Counter(labels)
        total = len(labels)
        
        if total == 0:
            return 0.0
        
        probabilities = [count / total for count in cluster_counts.values()]
        return entropy(probabilities, base=2)
    
    def _calculate_gini_coefficient(self, labels: np.ndarray) -> float:
        """Calculate Gini coefficient for cluster size distribution"""
        cluster_counts = list(Counter(labels).values())
        
        if len(cluster_counts) <= 1:
            return 0.0
        
        # Sort cluster sizes
        cluster_counts.sort()
        n = len(cluster_counts)
        
        # Calculate Gini coefficient
        cumsum = np.cumsum(cluster_counts)
        gini = (n + 1 - 2 * float(np.sum(cumsum)) / float(cumsum[-1])) / n
        
        return float(gini)
    
    # Stability metrics
    def _calculate_bootstrap_stability(self, feature_matrix: np.ndarray, labels: np.ndarray, 
                                     algorithm: str, n_bootstrap: int = 10) -> float:
        """Calculate clustering stability using bootstrap sampling"""
        try:
            n_samples = len(feature_matrix)
            stability_scores = []
            
            for _ in range(n_bootstrap):
                # Bootstrap sample
                indices = np.random.choice(n_samples, size=n_samples, replace=True)
                bootstrap_features = feature_matrix[indices]
                bootstrap_labels = labels[indices]
                
                # Re-cluster bootstrap sample
                if algorithm == "kmeans":
                    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                    if n_clusters > 1:
                        kmeans = KMeans(n_clusters=n_clusters, random_state=self.random_state)
                        new_labels = kmeans.fit_predict(bootstrap_features)
                        
                        # Calculate ARI between original and bootstrap clustering
                        ari = adjusted_rand_score(bootstrap_labels, new_labels)
                        stability_scores.append(max(0, ari))  # Ensure non-negative
            
            return float(np.mean(stability_scores)) if stability_scores else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating bootstrap stability: {e}")
            return 0.0
    
    def _calculate_consensus_score(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate consensus score based on cluster agreement"""
        try:
            # Calculate pairwise distances
            distances = pdist(feature_matrix)
            distance_matrix = squareform(distances)
            
            # Calculate consensus matrix
            n_samples = len(labels)
            consensus = np.zeros((n_samples, n_samples))
            
            for i in range(n_samples):
                for j in range(i + 1, n_samples):
                    if labels[i] == labels[j] and labels[i] != -1:  # Same cluster, not noise
                        consensus[i, j] = 1
                        consensus[j, i] = 1
            
            # Calculate consensus score as correlation with distance-based similarity
            distance_similarity = 1 / (1 + distance_matrix)
            
            # Flatten upper triangular matrices
            consensus_flat = consensus[np.triu_indices(n_samples, k=1)]
            similarity_flat = distance_similarity[np.triu_indices(n_samples, k=1)]
            
            if len(consensus_flat) > 0 and float(np.std(consensus_flat)) > 0:
                correlation = np.corrcoef(consensus_flat, similarity_flat)[0, 1]
                return max(0, correlation)  # Ensure non-negative
            else:
                return 0.0
                
        except Exception as e:
            logger.warning(f"Error calculating consensus score: {e}")
            return 0.0
    
    # Persona-specific metrics
    def _calculate_demographic_balance(self, personas: List[Dict[str, Any]], labels: np.ndarray) -> float:
        """Calculate demographic balance across clusters"""
        try:
            cluster_demographics = defaultdict(lambda: defaultdict(list))
            
            # Collect demographics by cluster
            for i, persona in enumerate(personas):
                cluster_id = labels[i]
                if cluster_id != -1:  # Skip noise
                    cluster_demographics[cluster_id]['age'].append(persona.get('age', 0))
                    cluster_demographics[cluster_id]['gender'].append(persona.get('gender', 'Unknown'))
                    cluster_demographics[cluster_id]['income'].append(persona.get('income_range', 'Unknown'))
            
            # Calculate balance scores
            balance_scores = []
            
            for cluster_id, demographics in cluster_demographics.items():
                # Age balance (coefficient of variation)
                ages = demographics['age']
                if ages and float(np.mean(ages)) > 0:
                    age_cv = float(np.std(ages)) / float(np.mean(ages))
                    balance_scores.append(min(1.0, age_cv))  # Normalize
                
                # Gender balance (entropy)
                genders = demographics['gender']
                if genders:
                    gender_counts = Counter(genders)
                    gender_probs = [count / len(genders) for count in gender_counts.values()]
                    gender_entropy = entropy(gender_probs, base=2)
                    max_entropy = np.log2(len(gender_counts))
                    if max_entropy > 0:
                        balance_scores.append(gender_entropy / max_entropy)
            
            return float(np.mean(balance_scores)) if balance_scores else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating demographic balance: {e}")
            return 0.0
    
    def _calculate_psychographic_diversity(self, personas: List[Dict[str, Any]], labels: np.ndarray) -> float:
        """Calculate psychographic diversity within clusters"""
        try:
            cluster_psychographics = defaultdict(list)
            
            # Collect psychographic data by cluster
            for i, persona in enumerate(personas):
                cluster_id = labels[i]
                if cluster_id != -1:  # Skip noise
                    psych = persona.get('psychographic', {})
                    personality = psych.get('personality', {})
                    if personality:
                        cluster_psychographics[cluster_id].append(personality)
            
            diversity_scores = []
            
            for cluster_id, personalities in cluster_psychographics.items():
                if len(personalities) > 1:
                    # Calculate diversity for each Big Five trait
                    trait_diversities = []
                    
                    for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
                        trait_values = [p.get(trait, 0.5) for p in personalities]
                        if trait_values:
                            trait_diversity = float(np.std(trait_values))
                            trait_diversities.append(trait_diversity)
                    
                    if trait_diversities:
                        diversity_scores.append(float(np.mean(trait_diversities)))
            
            return float(np.mean(diversity_scores)) if diversity_scores else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating psychographic diversity: {e}")
            return 0.0
    
    def _calculate_behavioral_coherence(self, personas: List[Dict[str, Any]], labels: np.ndarray) -> float:
        """Calculate behavioral coherence within clusters"""
        try:
            cluster_behaviors = defaultdict(list)
            
            # Collect behavioral data by cluster
            for i, persona in enumerate(personas):
                cluster_id = labels[i]
                if cluster_id != -1:  # Skip noise
                    behavioral = persona.get('behavioral', {})
                    if behavioral:
                        cluster_behaviors[cluster_id].append(behavioral)
            
            coherence_scores = []
            
            for cluster_id, behaviors in cluster_behaviors.items():
                if len(behaviors) > 1:
                    # Calculate coherence based on lifestyle preferences
                    lifestyle_coherence = self._calculate_lifestyle_coherence(behaviors)
                    coherence_scores.append(lifestyle_coherence)
            
            return float(np.mean(coherence_scores)) if coherence_scores else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating behavioral coherence: {e}")
            return 0.0
    
    def _calculate_lifestyle_coherence(self, behaviors: List[Dict[str, Any]]) -> float:
        """Calculate coherence of lifestyle preferences within a cluster"""
        try:
            # Extract lifestyle preferences
            lifestyle_prefs = []
            for behavior in behaviors:
                lifestyle = behavior.get('lifestyle_preferences', [])
                if lifestyle:
                    lifestyle_prefs.extend(lifestyle)
            
            if not lifestyle_prefs:
                return 0.0
            
            # Calculate preference overlap
            pref_counts = Counter(lifestyle_prefs)
            total_prefs = len(lifestyle_prefs)
            
            # Coherence as concentration of preferences
            coherence = sum((count / total_prefs) ** 2 for count in pref_counts.values())
            return coherence
            
        except Exception as e:
            logger.warning(f"Error calculating lifestyle coherence: {e}")
            return 0.0
    
    # Quality indicators
    def _calculate_cluster_separation(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate average separation between clusters"""
        try:
            cluster_centers = []
            
            for cluster_id in set(labels):
                if cluster_id != -1:  # Skip noise
                    cluster_points = feature_matrix[labels == cluster_id]
                    if len(cluster_points) > 0:
                        center = np.mean(cluster_points, axis=0)
                        cluster_centers.append(center)
            
            if len(cluster_centers) < 2:
                return 0.0
            
            # Calculate pairwise distances between centers
            center_distances = pdist(cluster_centers)
            return float(np.mean(center_distances))
            
        except Exception as e:
            logger.warning(f"Error calculating cluster separation: {e}")
            return 0.0
    
    def _calculate_cluster_compactness(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate average compactness of clusters"""
        try:
            compactness_scores = []
            
            for cluster_id in set(labels):
                if cluster_id != -1:  # Skip noise
                    cluster_points = feature_matrix[labels == cluster_id]
                    if len(cluster_points) > 1:
                        center = np.mean(cluster_points, axis=0)
                        distances = np.linalg.norm(cluster_points - center, axis=1)
                        compactness = float(np.mean(distances))
                        compactness_scores.append(compactness)
            
            return float(np.mean(compactness_scores)) if compactness_scores else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating cluster compactness: {e}")
            return 0.0
    
    def _calculate_noise_ratio(self, labels: np.ndarray) -> float:
        """Calculate ratio of noise points (for DBSCAN)"""
        noise_count = int(np.sum(labels == -1))
        return noise_count / len(labels) if len(labels) > 0 else 0.0
    
    # Persona quality metrics
    def _calculate_persona_completeness(self, persona: Dict[str, Any]) -> float:
        """Calculate completeness of persona profile"""
        # Check for persona_data wrapper first
        persona_data = persona.get('persona_data', persona)
        demographics = persona_data.get('demographics', {})
        
        required_fields = [
            ('age', demographics), ('gender', demographics), ('location', demographics), 
            ('education', demographics), ('income_range', demographics), ('family_status', demographics)
        ]
        
        # Check for psychographics/psychographic
        psychographics = persona_data.get('psychographics', persona_data.get('psychographic', {}))
        if psychographics:
            required_fields.append(('psychographics', {'psychographics': psychographics}))
            
        # Check for behavioral_patterns/behavioral
        behavioral = persona_data.get('behavioral_patterns', persona_data.get('behavioral', {}))
        if behavioral:
            required_fields.append(('behavioral_patterns', {'behavioral_patterns': behavioral}))
        
        completed_fields = 0
        for field_name, field_container in required_fields:
            if field_name in field_container and field_container[field_name] is not None:
                if isinstance(field_container[field_name], dict) and field_container[field_name]:
                    completed_fields += 1
                elif not isinstance(field_container[field_name], dict) and field_container[field_name] != "":
                    completed_fields += 1
        
        return completed_fields / len(required_fields)
    
    def _calculate_persona_consistency(self, persona: Dict[str, Any]) -> float:
        """Calculate internal consistency of persona attributes"""
        consistency_score = 1.0
        
        # Check for persona_data wrapper first
        persona_data = persona.get('persona_data', persona)
        demographics = persona_data.get('demographics', {})
        
        # Age-related consistency checks
        age = demographics.get('age', 0)
        education = demographics.get('education', '')
        
        # Check age-education consistency
        if age < 22 and education in ['Masters', 'PhD', 'Professional']:
            consistency_score -= 0.2
        
        # Income-education consistency
        income = demographics.get('income_range', '')
        if education == 'PhD' and income in ['Under $25k', '$25k-$35k']:
            consistency_score -= 0.2
        
        # Family status-age consistency
        family_status = demographics.get('family_status', '')
        if age < 18 and family_status in ['Married', 'Divorced', 'Widowed']:
            consistency_score -= 0.3
        
        return max(0.0, consistency_score)
    
    def _calculate_persona_realism(self, persona: Dict[str, Any]) -> float:
        """Calculate realism of persona attributes"""
        realism_score = 1.0
        
        # Check for persona_data wrapper first
        persona_data = persona.get('persona_data', persona)
        demographics = persona_data.get('demographics', {})
        
        # Check for unrealistic combinations
        age = demographics.get('age', 0)
        
        # Psychographic realism
        psych = persona_data.get('psychographics', persona_data.get('psychographic', {}))
        personality = psych.get('personality', {})
        
        if personality:
            # Check for extreme personality combinations
            extraversion = personality.get('extraversion', 0.5)
            neuroticism = personality.get('neuroticism', 0.5)
            
            # Very high extraversion with very high neuroticism is less common
            if extraversion > 0.8 and neuroticism > 0.8:
                realism_score -= 0.1
        
        return max(0.0, realism_score)
    
    def _calculate_persona_uniqueness(self, persona: Dict[str, Any], 
                                    reference_personas: List[Dict[str, Any]]) -> float:
        """Calculate uniqueness of persona compared to reference set"""
        if not reference_personas:
            return 1.0
        
        # Calculate similarity to each reference persona
        similarities = []
        
        for ref_persona in reference_personas:
            similarity = self._calculate_persona_similarity(persona, ref_persona)
            similarities.append(similarity)
        
        # Uniqueness is inverse of maximum similarity
        max_similarity = max(similarities) if similarities else 0
        return 1.0 - max_similarity
    
    def _calculate_persona_similarity(self, persona1: Dict[str, Any], persona2: Dict[str, Any]) -> float:
        """Calculate similarity between two personas"""
        similarity_scores = []
        
        # Demographic similarity
        demo_fields = ['age', 'gender', 'education', 'income_range']
        demo_matches = 0
        
        for field in demo_fields:
            if persona1.get(field) == persona2.get(field):
                demo_matches += 1
        
        demo_similarity = demo_matches / len(demo_fields)
        similarity_scores.append(demo_similarity)
        
        # Psychographic similarity
        psych1 = persona1.get('psychographic', {}).get('personality', {})
        psych2 = persona2.get('psychographic', {}).get('personality', {})
        
        if psych1 and psych2:
            trait_similarities = []
            for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
                val1 = psych1.get(trait, 0.5)
                val2 = psych2.get(trait, 0.5)
                trait_sim = 1 - abs(val1 - val2)  # Similarity as inverse of difference
                trait_similarities.append(trait_sim)
            
            psych_similarity = float(np.mean(trait_similarities))
            similarity_scores.append(psych_similarity)
        
        return float(np.mean(similarity_scores))
    
    def _calculate_demographic_validity(self, persona: Dict[str, Any]) -> float:
        """Calculate validity of demographic attributes"""
        validity_score = 1.0
        
        # Check for persona_data wrapper first
        persona_data = persona.get('persona_data', persona)
        demographics = persona_data.get('demographics', {})
        
        # Age validity
        age = demographics.get('age', 0)
        if not (0 <= age <= 120):
            validity_score -= 0.3
        
        # Gender validity
        gender = demographics.get('gender', '')
        valid_genders = ['Male', 'Female', 'Non-binary', 'Other', 'Prefer not to say']
        if gender not in valid_genders:
            validity_score -= 0.2
        
        # Education validity
        education = demographics.get('education', '')
        valid_educations = ['High School', 'Some College', 'Bachelors', 'Masters', 'PhD', 'Professional']
        if education not in valid_educations:
            validity_score -= 0.2
        
        return max(0.0, validity_score)
    
    def _calculate_psychographic_coherence(self, persona: Dict[str, Any]) -> float:
        """Calculate coherence of psychographic profile"""
        # Try both 'psychographics' and 'psychographic' for compatibility
        psych = persona.get('psychographics', persona.get('psychographic', {}))
        personality = psych.get('personality', {})
        
        if not personality:
            return 0.0
        
        # Check if personality traits are within valid range [0, 1]
        coherence_score = 1.0
        
        for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
            value = personality.get(trait, 0.5)
            if not (0 <= value <= 1):
                coherence_score -= 0.2
        
        return max(0.0, coherence_score)
    
    def _calculate_behavioral_alignment(self, persona: Dict[str, Any]) -> float:
        """Calculate alignment between personality and behavior"""
        # Try both 'psychographics' and 'psychographic' for compatibility
        psych = persona.get('psychographics', persona.get('psychographic', {}))
        personality = psych.get('personality', {})
        # Try both 'behavioral_patterns' and 'behavioral' for compatibility
        behavioral = persona.get('behavioral_patterns', persona.get('behavioral', {}))
        
        if not personality or not behavioral:
            return 0.5  # Neutral score if data missing
        
        alignment_score = 1.0
        
        # Check personality-behavior alignment
        extraversion = personality.get('extraversion', 0.5)
        lifestyle_prefs = behavioral.get('lifestyle_preferences', [])
        
        # High extraversion should align with social activities
        if extraversion > 0.7:
            social_activities = ['socializing', 'parties', 'networking', 'group_activities']
            has_social = any(pref in social_activities for pref in lifestyle_prefs)
            if not has_social:
                alignment_score -= 0.2
        
        # Low extraversion should align with solitary activities
        if extraversion < 0.3:
            solitary_activities = ['reading', 'meditation', 'solo_hobbies', 'quiet_activities']
            has_solitary = any(pref in solitary_activities for pref in lifestyle_prefs)
            if not has_solitary:
                alignment_score -= 0.2
        
        return max(0.0, alignment_score)
    
    # Dataset quality metrics
    def _calculate_demographic_coverage(self, personas: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate coverage of different demographic segments"""
        coverage = {}
        
        # Age coverage
        ages = [p.get('age', 0) for p in personas if p.get('age')]
        if ages:
            age_ranges = {
                '18-25': sum(1 for age in ages if 18 <= age <= 25),
                '26-35': sum(1 for age in ages if 26 <= age <= 35),
                '36-50': sum(1 for age in ages if 36 <= age <= 50),
                '51-65': sum(1 for age in ages if 51 <= age <= 65),
                '65+': sum(1 for age in ages if age > 65)
            }
            total_ages = len(ages)
            coverage['age_coverage'] = min(1.0, len([r for r in age_ranges.values() if r > 0]) / 5)
        else:
            coverage['age_coverage'] = 0.0
        
        # Gender coverage
        genders = [p.get('gender') for p in personas if p.get('gender')]
        unique_genders = len(set(genders))
        coverage['gender_coverage'] = min(1.0, unique_genders / 3)  # Expect at least 3 gender categories
        
        # Education coverage
        educations = [p.get('education') for p in personas if p.get('education')]
        unique_educations = len(set(educations))
        coverage['education_coverage'] = min(1.0, unique_educations / 6)  # Expect 6 education levels
        
        return coverage
    
    def _calculate_dataset_diversity(self, personas: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate diversity scores for the dataset"""
        diversity = {}
        
        # Demographic diversity
        genders = [p.get('gender') for p in personas if p.get('gender')]
        if genders:
            gender_counts = Counter(genders)
            gender_probs = [count / len(genders) for count in gender_counts.values()]
            diversity['gender_diversity'] = entropy(gender_probs, base=2) / np.log2(len(gender_counts))
        else:
            diversity['gender_diversity'] = 0.0
        
        # Age diversity
        ages = [p.get('age', 0) for p in personas if p.get('age')]
        if ages:
            diversity['age_diversity'] = float(np.std(ages)) / float(np.mean(ages)) if float(np.mean(ages)) > 0 else 0.0
        else:
            diversity['age_diversity'] = 0.0
        
        # Removed occupation diversity calculation
        
        return diversity
    
    def _calculate_distribution_quality(self, personas: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate quality of attribute distributions"""
        quality = {}
        
        # Age distribution quality (should be somewhat normal)
        ages = [p.get('age', 0) for p in personas if p.get('age')]
        if len(ages) > 10:
            # Test for normality using Shapiro-Wilk test
            try:
                _, p_value = stats.shapiro(ages)
                quality['age_distribution'] = min(1.0, p_value * 2)  # Scale p-value
            except:
                quality['age_distribution'] = 0.5
        else:
            quality['age_distribution'] = 0.5
        
        # Income distribution quality (should be realistic)
        incomes = [p.get('income_range') for p in personas if p.get('income_range')]
        if incomes:
            income_counts = Counter(incomes)
            # Check if distribution is reasonable (not too skewed)
            max_count = max(income_counts.values())
            min_count = min(income_counts.values())
            skew_ratio = max_count / min_count if min_count > 0 else float('inf')
            quality['income_distribution'] = max(0.0, 1.0 - (skew_ratio - 1) / 10)
        else:
            quality['income_distribution'] = 0.0
        
        return quality
    
    def _calculate_bias_indicators(self, personas: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate bias indicators in the dataset"""
        bias = {}
        
        # Gender bias
        genders = [p.get('gender') for p in personas if p.get('gender')]
        if genders:
            gender_counts = Counter(genders)
            total = len(genders)
            # Calculate deviation from equal distribution
            expected_prob = 1.0 / len(gender_counts)
            bias_score = sum(abs(count / total - expected_prob) for count in gender_counts.values())
            bias['gender_bias'] = bias_score / 2  # Normalize
        else:
            bias['gender_bias'] = 0.0
        
        # Age bias (check for concentration in specific age groups)
        ages = [p.get('age', 0) for p in personas if p.get('age')]
        if ages:
            age_groups = {
                'young': sum(1 for age in ages if age < 30),
                'middle': sum(1 for age in ages if 30 <= age < 60),
                'senior': sum(1 for age in ages if age >= 60)
            }
            total = len(ages)
            expected_prob = 1.0 / 3
            bias_score = sum(abs(count / total - expected_prob) for count in age_groups.values())
            bias['age_bias'] = bias_score / 2  # Normalize
        else:
            bias['age_bias'] = 0.0
        
        return bias
    
    def _calculate_representativeness(self, personas: List[Dict[str, Any]]) -> float:
        """Calculate how representative the dataset is of real populations"""
        # This is a simplified calculation - in practice, you'd compare against census data
        representativeness_scores = []
        
        # Gender representativeness (assuming roughly 50-50 split)
        genders = [p.get('gender') for p in personas if p.get('gender')]
        if genders:
            gender_counts = Counter(genders)
            if 'Male' in gender_counts and 'Female' in gender_counts:
                male_ratio = gender_counts['Male'] / len(genders)
                female_ratio = gender_counts['Female'] / len(genders)
                # Score based on how close to 50-50 split
                gender_score = 1.0 - abs(male_ratio - 0.5) - abs(female_ratio - 0.5)
                representativeness_scores.append(max(0.0, gender_score))
        
        # Age representativeness (should cover all adult age groups)
        ages = [p.get('age', 0) for p in personas if p.get('age')]
        if ages:
            age_ranges = [18, 30, 45, 60, 75]
            covered_ranges = sum(1 for i in range(len(age_ranges)-1) 
                               if any(age_ranges[i] <= age < age_ranges[i+1] for age in ages))
            age_score = covered_ranges / (len(age_ranges) - 1)
            representativeness_scores.append(age_score)
        
        return float(np.mean(representativeness_scores)) if representativeness_scores else 0.0
    
    def generate_quality_report(self, clustering_metrics: ClusteringMetrics, 
                              dataset_metrics: DatasetMetrics) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        report = {
            "overall_quality": {
                "clustering_quality": self._assess_clustering_quality(clustering_metrics),
                "dataset_quality": dataset_metrics.overall_quality,
                "combined_score": (self._assess_clustering_quality(clustering_metrics) + 
                                 dataset_metrics.overall_quality) / 2
            },
            "clustering_assessment": {
                "silhouette_assessment": self._assess_silhouette_score(clustering_metrics.silhouette_score),
                "stability_assessment": self._assess_stability(clustering_metrics.bootstrap_stability),
                "diversity_assessment": self._assess_diversity(clustering_metrics.diversity_index)
            },
            "recommendations": self._generate_recommendations(clustering_metrics, dataset_metrics),
            "quality_thresholds": self.quality_thresholds,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        
        return report
    
    def _assess_clustering_quality(self, metrics: ClusteringMetrics) -> float:
        """Assess overall clustering quality"""
        scores = [
            max(0, metrics.silhouette_score),
            min(1, metrics.calinski_harabasz_score / 1000),
            max(0, 1 - metrics.davies_bouldin_score / 10),
            metrics.diversity_index,
            metrics.bootstrap_stability,
            metrics.demographic_balance
        ]
        
        return float(np.mean([s for s in scores if not np.isnan(s) and not np.isinf(s)]))
    
    def _assess_silhouette_score(self, silhouette_score: float) -> str:
        """Assess silhouette score quality"""
        if silhouette_score >= self.quality_thresholds["silhouette_excellent"]:
            return "Excellent"
        elif silhouette_score >= self.quality_thresholds["silhouette_good"]:
            return "Good"
        elif silhouette_score >= self.quality_thresholds["silhouette_fair"]:
            return "Fair"
        else:
            return "Poor"
    
    def _assess_stability(self, stability_score: float) -> str:
        """Assess clustering stability"""
        if stability_score >= self.quality_thresholds["stability_high"]:
            return "High"
        elif stability_score >= self.quality_thresholds["stability_medium"]:
            return "Medium"
        else:
            return "Low"
    
    def _assess_diversity(self, diversity_score: float) -> str:
        """Assess diversity quality"""
        if diversity_score >= self.quality_thresholds["diversity_high"]:
            return "High"
        elif diversity_score >= self.quality_thresholds["diversity_medium"]:
            return "Medium"
        else:
            return "Low"
    
    def _generate_recommendations(self, clustering_metrics: ClusteringMetrics, 
                                dataset_metrics: DatasetMetrics) -> List[str]:
        """Generate recommendations for improvement"""
        recommendations = []
        
        # Clustering recommendations
        if clustering_metrics.silhouette_score < self.quality_thresholds["silhouette_fair"]:
            recommendations.append("Consider feature engineering or different clustering algorithm for better cluster quality")
        
        if clustering_metrics.bootstrap_stability < self.quality_thresholds["stability_medium"]:
            recommendations.append("Clustering is unstable. Consider increasing sample size or adjusting parameters")
        
        if clustering_metrics.diversity_index < self.quality_thresholds["diversity_medium"]:
            recommendations.append("Low cluster diversity. Consider generating more varied personas")
        
        # Dataset recommendations
        if dataset_metrics.overall_quality < 0.6:
            recommendations.append("Dataset quality is below acceptable threshold. Review persona generation process")
        
        if any(bias > 0.3 for bias in dataset_metrics.bias_indicators.values()):
            recommendations.append("High bias detected in demographic distributions. Review sampling strategy")
        
        if dataset_metrics.representativeness < 0.7:
            recommendations.append("Dataset may not be representative of target population. Consider demographic adjustments")
        
        return recommendations