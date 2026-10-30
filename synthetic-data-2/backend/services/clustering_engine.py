import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional, Union
from dataclasses import dataclass
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, Birch
from sklearn.mixture import GaussianMixture
from sklearn.decomposition import NMF, PCA
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import seaborn as sns
from loguru import logger
import json
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

@dataclass
class ClusteringConfig:
    """Configuration for clustering algorithms"""
    max_clusters: int = 10
    min_clusters: int = 2
    random_state: int = 42
    n_components_pca: int = 10
    eps_dbscan: float = 0.5
    min_samples_dbscan: int = 5
    linkage_hierarchical: str = "ward"
    n_components_nmf: int = 5

@dataclass
class ClusterResult:
    """Result of clustering analysis"""
    algorithm: str
    n_clusters: int
    labels: List[int]
    cluster_centers: Optional[np.ndarray]
    silhouette_score: float
    calinski_harabasz_score: float
    davies_bouldin_score: float
    inertia: Optional[float]
    cluster_summary: Dict[int, Dict[str, Any]]
    feature_importance: Dict[str, float]

@dataclass
class PersonaCluster:
    """Represents a cluster of personas"""
    cluster_id: int
    personas: List[Dict[str, Any]]
    centroid: Dict[str, Any]
    characteristics: Dict[str, Any]
    diversity_metrics: Dict[str, float]
    size: int

class ClusteringEngine:
    """Engine for clustering persona data using multiple algorithms"""
    
    def __init__(self, config: ClusteringConfig = None):
        self.config = config or ClusteringConfig()
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names = []
        self.clustering_history = []
        
        # Initialize clustering algorithms
        self.algorithms = {
            "kmeans": self._setup_kmeans,
            "gmm": self._setup_gmm,
            "dbscan": self._setup_dbscan,
            "hierarchical": self._setup_hierarchical,
            "birch": self._setup_birch
        }
        
        logger.info("Initialized Clustering Engine with multiple algorithms")
    
    def cluster_personas(self, personas: List[Dict[str, Any]], 
                        algorithms: Optional[List[str]] = None,
                        feature_selection: Optional[List[str]] = None) -> Dict[str, ClusterResult]:
        """Cluster personas using specified algorithms"""
        if not personas:
            return {}
        
        # Prepare data for clustering
        feature_matrix, feature_names = self._prepare_clustering_data(personas, feature_selection)
        self.feature_names = feature_names
        
        # Use all algorithms if none specified
        algorithms = algorithms or list(self.algorithms.keys())
        
        results = {}
        
        for algorithm in algorithms:
            try:
                logger.info(f"Running {algorithm} clustering")
                result = self._run_clustering_algorithm(algorithm, feature_matrix, personas)
                results[algorithm] = result
                
            except Exception as e:
                logger.error(f"Error in {algorithm} clustering: {str(e)}")
                continue
        
        # Find optimal clustering
        optimal_result = self._find_optimal_clustering(results)
        
        # Store clustering history
        self.clustering_history.append({
            "timestamp": pd.Timestamp.now(),
            "n_personas": len(personas),
            "algorithms_used": algorithms,
            "optimal_algorithm": optimal_result[0] if optimal_result else None,
            "results": results
        })
        
        logger.info(f"Clustering completed. Optimal algorithm: {optimal_result[0] if optimal_result else 'None'}")
        return results
    
    def prepare_clustering_data(self, personas: List[Dict[str, Any]], 
                               feature_selection: Optional[List[str]] = None) -> Tuple[np.ndarray, List[str]]:
        """Public method to prepare persona data for clustering"""
        return self._prepare_clustering_data(personas, feature_selection)
    
    def find_optimal_clusters(self, feature_matrix: np.ndarray, algorithm: str = "kmeans") -> int:
        """Public method to find optimal number of clusters"""
        optimal_k, _ = self._find_optimal_k(algorithm, feature_matrix)
        return optimal_k
     
    def _prepare_clustering_data(self, personas: List[Dict[str, Any]], 
                               feature_selection: Optional[List[str]] = None) -> Tuple[np.ndarray, List[str]]:
        """Prepare persona data for clustering"""
        # Extract and flatten all features
        feature_data = []
        all_features = set()
        
        # First pass: collect all possible features
        for persona in personas:
            flattened = self._flatten_persona_features(persona)
            all_features.update(flattened.keys())
        
        # Filter features if selection provided
        if feature_selection:
            all_features = set(feature_selection) & all_features
        
        feature_names = sorted(list(all_features))
        
        # Second pass: create feature matrix
        for persona in personas:
            flattened = self._flatten_persona_features(persona)
            feature_vector = []
            
            for feature_name in feature_names:
                value = flattened.get(feature_name, None)
                
                # Handle different data types
                if isinstance(value, (int, float)):
                    feature_vector.append(float(value))
                elif isinstance(value, str):
                    # Encode categorical variables
                    if feature_name not in self.label_encoders:
                        self.label_encoders[feature_name] = LabelEncoder()
                        # Fit on all possible values first
                        all_values = [self._flatten_persona_features(p).get(feature_name, 'unknown') 
                                    for p in personas]
                        # Add 'unknown' as a fallback for unseen values
                        if 'unknown' not in all_values:
                            all_values.append('unknown')
                        self.label_encoders[feature_name].fit(all_values)
                    
                    # Handle unseen labels gracefully
                    try:
                        encoded_value = self.label_encoders[feature_name].transform([value])[0]
                    except ValueError:
                        # If value is unseen, use 'unknown' encoding
                        logger.warning(f"Unseen label '{value}' for feature '{feature_name}', using 'unknown'")
                        encoded_value = self.label_encoders[feature_name].transform(['unknown'])[0]
                    
                    feature_vector.append(float(encoded_value))
                elif isinstance(value, bool):
                    feature_vector.append(float(value))
                else:
                    # Default value for missing/unknown types
                    feature_vector.append(0.0)
            
            feature_data.append(feature_vector)
        
        # Convert to numpy array and scale
        feature_matrix = np.array(feature_data)
        
        # Handle NaN values
        feature_matrix = np.nan_to_num(feature_matrix, nan=0.0)
        
        # Scale features
        feature_matrix = self.scaler.fit_transform(feature_matrix)
        
        logger.info(f"Prepared clustering data: {feature_matrix.shape[0]} personas, {feature_matrix.shape[1]} features")
        return feature_matrix, feature_names
    
    def _flatten_persona_features(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested persona features for clustering"""
        flattened = {}
        
        def _flatten_recursive(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, dict):
                        _flatten_recursive(value, new_key)
                    elif isinstance(value, list):
                        # Handle lists by taking length or first element
                        if value:
                            if isinstance(value[0], (str, int, float, bool)):
                                flattened[new_key] = value[0] if len(value) == 1 else len(value)
                            else:
                                flattened[new_key] = len(value)
                        else:
                            flattened[new_key] = 0
                    elif value is None:
                        flattened[new_key] = 'unknown'
                    else:
                        # Sanitize string values to handle edge cases
                        if isinstance(value, str):
                            value = value.strip().lower() if value.strip() else 'unknown'
                        flattened[new_key] = value
        
        _flatten_recursive(persona)
        
        # Add derived features
        if "age" in flattened and isinstance(flattened["age"], (int, float)):
            flattened["age_group"] = self._categorize_age(flattened["age"])
        
        return flattened
    
    def _categorize_age(self, age: Union[int, float]) -> str:
        """Categorize age into groups"""
        if age < 25:
            return "young"
        elif age < 35:
            return "young_adult"
        elif age < 50:
            return "middle_aged"
        else:
            return "senior"
    
    def _run_clustering_algorithm(self, algorithm: str, feature_matrix: np.ndarray, 
                                personas: List[Dict[str, Any]]) -> ClusterResult:
        """Run a specific clustering algorithm"""
        setup_func = self.algorithms[algorithm]
        
        if algorithm in ["kmeans", "gmm", "hierarchical", "birch"]:
            # For algorithms that need k, find optimal k
            optimal_k, best_model = self._find_optimal_k(algorithm, feature_matrix)
            labels = best_model.labels_ if hasattr(best_model, 'labels_') else best_model.predict(feature_matrix)
            n_clusters = optimal_k
            
            # Get cluster centers if available
            cluster_centers = None
            if hasattr(best_model, 'cluster_centers_'):
                cluster_centers = best_model.cluster_centers_
            elif hasattr(best_model, 'means_'):
                cluster_centers = best_model.means_
            
            # Calculate inertia if available
            inertia = getattr(best_model, 'inertia_', None)
            
        else:  # DBSCAN
            model = setup_func()
            labels = model.fit_predict(feature_matrix)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)  # Exclude noise
            cluster_centers = None
            inertia = None
        
        # Calculate clustering metrics
        silhouette = self._calculate_silhouette_score(feature_matrix, labels)
        calinski_harabasz = self._calculate_calinski_harabasz_score(feature_matrix, labels)
        davies_bouldin = self._calculate_davies_bouldin_score(feature_matrix, labels)
        
        # Generate cluster summary
        cluster_summary = self._generate_cluster_summary(personas, labels)
        
        # Calculate feature importance
        feature_importance = self._calculate_feature_importance(feature_matrix, labels)
        
        return ClusterResult(
            algorithm=algorithm,
            n_clusters=n_clusters,
            labels=labels.tolist(),
            cluster_centers=cluster_centers,
            silhouette_score=silhouette,
            calinski_harabasz_score=calinski_harabasz,
            davies_bouldin_score=davies_bouldin,
            inertia=inertia,
            cluster_summary=cluster_summary,
            feature_importance=feature_importance
        )
    
    def _find_optimal_k(self, algorithm: str, feature_matrix: np.ndarray) -> Tuple[int, Any]:
        """Find optimal number of clusters using multiple metrics"""
        # Ensure we have enough data points for clustering
        max_possible_clusters = min(self.config.max_clusters, len(feature_matrix) - 1)
        if max_possible_clusters < self.config.min_clusters:
            # Not enough data points for clustering, return single cluster
            setup_func = self.algorithms[algorithm]
            model = setup_func(n_clusters=1)
            return 1, model
            
        k_range = range(self.config.min_clusters, max_possible_clusters + 1)
        
        scores = {
            'silhouette': [],
            'calinski_harabasz': [],
            'davies_bouldin': [],
            'inertia': []
        }
        
        models = []
        
        for k in k_range:
            setup_func = self.algorithms[algorithm]
            model = setup_func(n_clusters=k)
            
            if algorithm == "gmm":
                model.fit(feature_matrix)
                labels = model.predict(feature_matrix)
            else:
                labels = model.fit_predict(feature_matrix)
            
            models.append(model)
            
            # Calculate metrics
            if len(set(labels)) > 1:  # Need at least 2 clusters for metrics
                scores['silhouette'].append(silhouette_score(feature_matrix, labels))
                scores['calinski_harabasz'].append(calinski_harabasz_score(feature_matrix, labels))
                scores['davies_bouldin'].append(davies_bouldin_score(feature_matrix, labels))
            else:
                scores['silhouette'].append(-1)
                scores['calinski_harabasz'].append(0)
                scores['davies_bouldin'].append(float('inf'))
            
            # Inertia for K-means
            if hasattr(model, 'inertia_'):
                scores['inertia'].append(model.inertia_)
            else:
                scores['inertia'].append(0)
        
        # Find optimal k using combined score
        optimal_k = self._select_optimal_k(k_range, scores)
        optimal_model = models[optimal_k - self.config.min_clusters]
        
        return optimal_k, optimal_model
    
    def _select_optimal_k(self, k_range: range, scores: Dict[str, List[float]]) -> int:
        """Select optimal k using multiple criteria"""
        # Normalize scores
        normalized_scores = {}
        
        for metric, values in scores.items():
            if metric == 'davies_bouldin':  # Lower is better
                normalized_scores[metric] = [(max(values) - v) / (max(values) - min(values) + 1e-8) for v in values]
            else:  # Higher is better (except inertia, but we'll use elbow method)
                if metric == 'inertia':
                    # Use elbow method for inertia
                    normalized_scores[metric] = self._calculate_elbow_score(values)
                else:
                    normalized_scores[metric] = [(v - min(values)) / (max(values) - min(values) + 1e-8) for v in values]
        
        # Combine scores with weights
        weights = {
            'silhouette': 0.4,
            'calinski_harabasz': 0.3,
            'davies_bouldin': 0.2,
            'inertia': 0.1
        }
        
        combined_scores = []
        for i in range(len(k_range)):
            score = sum(weights[metric] * normalized_scores[metric][i] for metric in weights)
            combined_scores.append(score)
        
        # Return k with highest combined score
        if not combined_scores:
            return list(k_range)[0] if k_range else self.config.min_clusters
            
        optimal_idx = np.argmax(combined_scores)
        return list(k_range)[optimal_idx]
    
    def _calculate_elbow_score(self, inertia_values: List[float]) -> List[float]:
        """Calculate elbow scores for inertia values"""
        if len(inertia_values) < 3:
            return [0.5] * len(inertia_values)
        
        # Calculate second derivative to find elbow
        scores = []
        for i in range(len(inertia_values)):
            if i == 0 or i == len(inertia_values) - 1:
                scores.append(0.5)
            else:
                # Second derivative approximation
                second_deriv = inertia_values[i-1] - 2*inertia_values[i] + inertia_values[i+1]
                scores.append(abs(second_deriv))
        
        # Normalize
        max_score = max(scores) if max(scores) > 0 else 1
        return [s / max_score for s in scores]
    
    def _setup_kmeans(self, n_clusters: int = None) -> KMeans:
        """Setup K-means clustering"""
        return KMeans(
            n_clusters=n_clusters or self.config.min_clusters,
            random_state=self.config.random_state,
            n_init=10
        )
    
    def _setup_gmm(self, n_clusters: int = None) -> GaussianMixture:
        """Setup Gaussian Mixture Model"""
        return GaussianMixture(
            n_components=n_clusters or self.config.min_clusters,
            random_state=self.config.random_state
        )
    
    def _setup_dbscan(self) -> DBSCAN:
        """Setup DBSCAN clustering"""
        return DBSCAN(
            eps=self.config.eps_dbscan,
            min_samples=self.config.min_samples_dbscan
        )
    
    def _setup_hierarchical(self, n_clusters: int = None) -> AgglomerativeClustering:
        """Setup Hierarchical clustering"""
        return AgglomerativeClustering(
            n_clusters=n_clusters or self.config.min_clusters,
            linkage=self.config.linkage_hierarchical
        )
    
    def _setup_birch(self, n_clusters: int = None) -> Birch:
        """Setup BIRCH clustering"""
        return Birch(
            n_clusters=n_clusters or self.config.min_clusters
        )
    
    def _calculate_silhouette_score(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate silhouette score"""
        try:
            if len(set(labels)) > 1 and len(set(labels)) < len(labels):
                return silhouette_score(feature_matrix, labels)
            else:
                return -1.0
        except:
            return -1.0
    
    def _calculate_calinski_harabasz_score(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate Calinski-Harabasz score"""
        try:
            if len(set(labels)) > 1:
                return calinski_harabasz_score(feature_matrix, labels)
            else:
                return 0.0
        except:
            return 0.0
    
    def _calculate_davies_bouldin_score(self, feature_matrix: np.ndarray, labels: np.ndarray) -> float:
        """Calculate Davies-Bouldin score"""
        try:
            if len(set(labels)) > 1:
                return davies_bouldin_score(feature_matrix, labels)
            else:
                return float('inf')
        except:
            return float('inf')
    
    def _generate_cluster_summary(self, personas: List[Dict[str, Any]], labels: np.ndarray) -> Dict[int, Dict[str, Any]]:
        """Generate summary statistics for each cluster"""
        cluster_summary = {}
        
        for cluster_id in set(labels):
            if cluster_id == -1:  # Skip noise points in DBSCAN
                continue
            
            cluster_personas = [personas[i] for i, label in enumerate(labels) if label == cluster_id]
            
            # Calculate cluster characteristics
            characteristics = self._calculate_cluster_characteristics(cluster_personas)
            
            cluster_summary[cluster_id] = {
                "size": len(cluster_personas),
                "percentage": len(cluster_personas) / len(personas) * 100,
                "characteristics": characteristics,
                "diversity_metrics": self._calculate_cluster_diversity(cluster_personas)
            }
        
        return cluster_summary
    
    def _calculate_cluster_characteristics(self, cluster_personas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate characteristics of a cluster"""
        characteristics = {
            "demographics": {},
            "psychographics": {},
            "behavioral": {}
        }
        
        # Demographic characteristics
        ages = [p.get("age", 0) for p in cluster_personas]
        if ages:
            characteristics["demographics"]["age"] = {
                "mean": float(np.mean(ages)),
            "std": float(np.std(ages)),
            "min": float(np.min(ages)),
            "max": float(np.max(ages))
            }
        
        # Gender distribution
        genders = [p.get("gender", "Unknown") for p in cluster_personas]
        gender_counts = pd.Series(genders).value_counts(normalize=True).to_dict()
        characteristics["demographics"]["gender_distribution"] = gender_counts
        
        # Income distribution
        incomes = [p.get("income_range", "Unknown") for p in cluster_personas]
        income_counts = pd.Series(incomes).value_counts(normalize=True).to_dict()
        characteristics["demographics"]["income_distribution"] = income_counts
        
        # Education distribution
        educations = [p.get("education", "Unknown") for p in cluster_personas]
        education_counts = pd.Series(educations).value_counts(normalize=True).to_dict()
        characteristics["demographics"]["education_distribution"] = education_counts
        
        # Psychographic characteristics
        personality_traits = []
        for persona in cluster_personas:
            psych = persona.get("psychographic", {})
            personality = psych.get("personality", {})
            if personality:
                personality_traits.append(personality)
        
        if personality_traits:
            for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
                trait_values = [p.get(trait, 0.5) for p in personality_traits]
                if trait_values:
                    characteristics["psychographics"][trait] = {
                        "mean": float(np.mean(trait_values)),
                "std": float(np.std(trait_values))
                    }
        
        return characteristics
    
    def _calculate_cluster_diversity(self, cluster_personas: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate diversity metrics for a cluster"""
        diversity_metrics = {}
        
        # Age diversity (coefficient of variation)
        ages = [p.get("age", 0) for p in cluster_personas if p.get("age")]
        if ages and float(np.mean(ages)) > 0:
            diversity_metrics["age_diversity"] = float(np.std(ages)) / float(np.mean(ages))
        else:
            diversity_metrics["age_diversity"] = 0.0
        
        # Gender diversity (entropy)
        genders = [p.get("gender", "Unknown") for p in cluster_personas]
        gender_probs = pd.Series(genders).value_counts(normalize=True)
        diversity_metrics["gender_entropy"] = -sum(p * np.log2(p) for p in gender_probs if p > 0)
        
        # Income diversity
        incomes = [p.get("income_range", "Unknown") for p in cluster_personas]
        income_probs = pd.Series(incomes).value_counts(normalize=True)
        diversity_metrics["income_entropy"] = -sum(p * np.log2(p) for p in income_probs if p > 0)
        
        # Overall diversity score
        diversity_metrics["overall_diversity"] = float(np.mean([
            diversity_metrics["age_diversity"],
            diversity_metrics["gender_entropy"] / 2,  # Normalize entropy
            diversity_metrics["income_entropy"] / 3   # Normalize entropy
        ]).item())
        
        return diversity_metrics
    
    def _calculate_feature_importance(self, feature_matrix: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """Calculate feature importance for clustering"""
        if len(set(labels)) <= 1:
            return {name: 0.0 for name in self.feature_names}
        
        importance_scores = {}
        
        for i, feature_name in enumerate(self.feature_names):
            feature_values = feature_matrix[:, i]
            
            # Calculate variance between clusters vs within clusters
            between_cluster_var = 0
            within_cluster_var = 0
            
            for cluster_id in set(labels):
                if cluster_id == -1:  # Skip noise
                    continue
                
                cluster_mask = labels == cluster_id
                cluster_values = feature_values[cluster_mask]
                
                if len(cluster_values) > 0:
                    cluster_mean = float(np.mean(cluster_values))
                    overall_mean = float(np.mean(feature_values))
                    
                    between_cluster_var += len(cluster_values) * (cluster_mean - overall_mean) ** 2
                    within_cluster_var += float(np.sum((cluster_values - cluster_mean) ** 2))
            
            # F-ratio as importance score
            if within_cluster_var > 0:
                f_ratio = between_cluster_var / within_cluster_var
                importance_scores[feature_name] = f_ratio
            else:
                importance_scores[feature_name] = 0.0
        
        # Normalize scores
        max_score = max(importance_scores.values()) if importance_scores.values() else 1
        if max_score > 0:
            importance_scores = {k: v / max_score for k, v in importance_scores.items()}
        
        return importance_scores
    
    def _find_optimal_clustering(self, results: Dict[str, ClusterResult]) -> Optional[Tuple[str, ClusterResult]]:
        """Find the optimal clustering result across all algorithms"""
        if not results:
            return None
        
        # Score each result
        scores = {}
        for algorithm, result in results.items():
            # Combine multiple metrics with weights
            score = (
                0.4 * max(0, result.silhouette_score) +
                0.3 * min(1, result.calinski_harabasz_score / 1000) +  # Normalize
                0.2 * max(0, 1 - result.davies_bouldin_score / 10) +   # Invert and normalize
                0.1 * min(1, result.n_clusters / 10)  # Prefer reasonable number of clusters
            )
            scores[algorithm] = score
        
        # Return algorithm with highest score
        best_algorithm = max(scores.items(), key=lambda x: x[1])
        return best_algorithm[0], results[best_algorithm[0]]
    
    def generate_persona_clusters(self, personas: List[Dict[str, Any]], 
                                clustering_result: ClusterResult) -> List[PersonaCluster]:
        """Generate PersonaCluster objects from clustering results"""
        persona_clusters = []
        
        for cluster_id in set(clustering_result.labels):
            if cluster_id == -1:  # Skip noise
                continue
            
            # Get personas in this cluster
            cluster_personas = [personas[i] for i, label in enumerate(clustering_result.labels) 
                              if label == cluster_id]
            
            # Calculate centroid
            centroid = self._calculate_cluster_centroid(cluster_personas)
            
            # Get characteristics from cluster summary
            characteristics = clustering_result.cluster_summary.get(cluster_id, {})
            
            # Calculate diversity metrics
            diversity_metrics = self._calculate_cluster_diversity(cluster_personas)
            
            persona_cluster = PersonaCluster(
                cluster_id=cluster_id,
                personas=cluster_personas,
                centroid=centroid,
                characteristics=characteristics,
                diversity_metrics=diversity_metrics,
                size=len(cluster_personas)
            )
            
            persona_clusters.append(persona_cluster)
        
        return persona_clusters
    
    def _calculate_cluster_centroid(self, cluster_personas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate the centroid (representative persona) of a cluster"""
        if not cluster_personas:
            return {}
        
        centroid = {}
        
        # Demographic centroid
        ages = [p.get("age", 0) for p in cluster_personas if p.get("age")]
        if ages:
            centroid["age"] = int(float(np.mean(ages)))
        
        # Most common categorical values
        for attr in ["gender", "education", "income_range", "family_status"]:
            values = [p.get(attr) for p in cluster_personas if p.get(attr)]
            if values:
                centroid[attr] = pd.Series(values).mode().iloc[0]
        
        # Location centroid
        locations = [p.get("location", {}) for p in cluster_personas if p.get("location")]
        if locations:
            cities = [loc.get("city") for loc in locations if loc.get("city")]
            if cities:
                centroid["location"] = {"city": pd.Series(cities).mode().iloc[0]}
        
        # Psychographic centroid
        personality_traits = []
        for persona in cluster_personas:
            psych = persona.get("psychographic", {})
            personality = psych.get("personality", {})
            if personality:
                personality_traits.append(personality)
        
        if personality_traits:
            centroid["psychographic"] = {"personality": {}}
            for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
                trait_values = [p.get(trait, 0.5) for p in personality_traits]
                if trait_values:
                    centroid["psychographic"]["personality"][trait] = float(np.mean(trait_values))
        
        return centroid
    
    def get_clustering_insights(self, clustering_results: Dict[str, ClusterResult]) -> Dict[str, Any]:
        """Generate insights from clustering results"""
        insights = {
            "algorithm_comparison": {},
            "optimal_clusters": {},
            "feature_importance": {},
            "cluster_characteristics": {},
            "recommendations": []
        }
        
        # Compare algorithms
        for algorithm, result in clustering_results.items():
            insights["algorithm_comparison"][algorithm] = {
                "n_clusters": result.n_clusters,
                "silhouette_score": result.silhouette_score,
                "calinski_harabasz_score": result.calinski_harabasz_score,
                "davies_bouldin_score": result.davies_bouldin_score
            }
        
        # Find optimal clustering
        optimal = self._find_optimal_clustering(clustering_results)
        if optimal:
            insights["optimal_clusters"] = {
                "algorithm": optimal[0],
                "n_clusters": optimal[1].n_clusters,
                "quality_score": optimal[1].silhouette_score
            }
            
            # Feature importance from optimal clustering
            insights["feature_importance"] = optimal[1].feature_importance
            
            # Cluster characteristics
            insights["cluster_characteristics"] = optimal[1].cluster_summary
        
        # Generate recommendations
        if optimal and optimal[1].silhouette_score < 0.3:
            insights["recommendations"].append("Low silhouette score suggests poor clustering quality. Consider feature engineering.")
        
        if optimal and optimal[1].n_clusters > 8:
            insights["recommendations"].append("High number of clusters detected. Consider if this granularity is useful.")
        
        return insights