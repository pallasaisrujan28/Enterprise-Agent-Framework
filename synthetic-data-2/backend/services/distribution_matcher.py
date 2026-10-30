import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from scipy import stats
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
from scipy.stats import wasserstein_distance
import json
from loguru import logger
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

@dataclass
class DistributionTarget:
    """Target distribution for a specific attribute"""
    attribute_name: str
    distribution_type: str  # 'normal', 'uniform', 'categorical', 'beta', 'gamma'
    parameters: Dict[str, Any]
    real_world_data: Optional[List[Any]] = None
    weight: float = 1.0

@dataclass
class MatchingResult:
    """Result of distribution matching"""
    attribute_name: str
    original_distribution: Dict[str, Any]
    target_distribution: Dict[str, Any]
    adjusted_distribution: Dict[str, Any]
    matching_score: float
    statistical_tests: Dict[str, float]

class DistributionMatcher:
    """System for matching generated persona distributions to real-world statistical data"""
    
    def __init__(self):
        self.target_distributions = self._load_real_world_distributions()
        self.scaler = StandardScaler()
        self.matching_history = []
        
        logger.info("Initialized Distribution Matcher with real-world statistical targets")
    
    def match_distributions(self, generated_personas: List[Dict[str, Any]], 
                          target_specs: Optional[Dict[str, DistributionTarget]] = None) -> Tuple[List[Dict[str, Any]], List[MatchingResult]]:
        """Match generated persona distributions to target distributions"""
        if not generated_personas:
            return [], []
        
        # Use provided targets or default real-world distributions
        targets = target_specs or self.target_distributions
        
        # Analyze current distributions
        current_distributions = self._analyze_current_distributions(generated_personas)
        
        # Perform matching for each attribute
        matching_results = []
        adjusted_personas = generated_personas.copy()
        
        for attr_name, target in targets.items():
            if attr_name in current_distributions:
                result = self._match_single_attribute(
                    adjusted_personas, attr_name, target, current_distributions[attr_name]
                )
                matching_results.append(result)
                
                # Apply adjustments to personas
                adjusted_personas = self._apply_distribution_adjustments(
                    adjusted_personas, attr_name, result
                )
        
        # Validate overall distribution coherence
        coherence_score = self._validate_distribution_coherence(adjusted_personas, targets)
        
        logger.info(f"Distribution matching completed. Coherence score: {coherence_score:.3f}")
        return adjusted_personas, matching_results
    
    def analyze_current_distributions(self, personas: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Public method to analyze the current distribution of attributes in generated personas"""
        return self._analyze_current_distributions(personas)
    
    def calculate_matching_scores(self, current_distributions: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate matching scores for current distributions against real-world targets"""
        targets = self._load_real_world_distributions()
        scores = {}
        
        for attr_name, current_dist in current_distributions.items():
            if attr_name in targets:
                score = self._calculate_matching_score(current_dist, targets[attr_name])
                scores[attr_name] = score
            else:
                # Default score for attributes without targets
                scores[attr_name] = 0.5
        
        return scores
    
    def generate_adjustment_strategy(self, current_dist: Dict[str, Any], target: DistributionTarget) -> Dict[str, Any]:
        """Public method to generate adjustment strategy for distribution matching"""
        return self._generate_adjustment_strategy(current_dist, target)
     
    def _analyze_current_distributions(self, personas: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Analyze the current distribution of attributes in generated personas"""
        distributions = {}
        
        # Extract all attribute values
        attribute_values = {}
        for persona in personas:
            for key, value in self._flatten_persona_attributes(persona).items():
                if key not in attribute_values:
                    attribute_values[key] = []
                attribute_values[key].append(value)
        
        # Analyze each attribute
        for attr_name, values in attribute_values.items():
            distributions[attr_name] = self._analyze_attribute_distribution(attr_name, values)
        
        return distributions
    
    def _analyze_attribute_distribution(self, attr_name: str, values: List[Any]) -> Dict[str, Any]:
        """Analyze the distribution of a single attribute"""
        # Handle empty or None values
        if not values or all(v is None for v in values):
            return {
                "type": "empty",
                "parameters": {},
                "error": "No valid values found"
            }
        
        # Handle different data types
        if self._is_numerical_attribute(values):
            result = self._analyze_numerical_distribution(values)
        else:
            result = self._analyze_categorical_distribution(values)
        
        # Ensure 'type' key is always present
        if "type" not in result:
            result["type"] = "unknown"
        
        return result
    
    def _is_numerical_attribute(self, values: List[Any]) -> bool:
        """Check if attribute values are numerical"""
        try:
            # Try to convert to float
            numeric_values = [float(v) for v in values if v is not None]
            return len(numeric_values) > len(values) * 0.8  # 80% should be numeric
        except (ValueError, TypeError):
            return False
    
    def _analyze_numerical_distribution(self, values: List[Any]) -> Dict[str, Any]:
        """Analyze numerical distribution"""
        # Convert to numeric array
        numeric_values = np.array([float(v) for v in values if v is not None])
        
        if len(numeric_values) == 0:
            return {"type": "empty", "parameters": {}}
        
        # Basic statistics
        mean = float(np.mean(numeric_values))
        std = float(np.std(numeric_values))
        median = float(np.median(numeric_values))
        
        # Test for different distributions
        distribution_tests = {
            "normal": self._test_normal_distribution(numeric_values),
            "uniform": self._test_uniform_distribution(numeric_values),
            "beta": self._test_beta_distribution(numeric_values),
            "gamma": self._test_gamma_distribution(numeric_values)
        }
        
        # Select best fitting distribution
        best_dist = max(distribution_tests.items(), key=lambda x: x[1]["p_value"])
        
        return {
            "type": "numerical",
            "best_distribution": best_dist[0],
            "parameters": {
                "mean": mean,
                "std": std,
                "median": median,
                "min": float(np.min(numeric_values)),
                "max": float(np.max(numeric_values))
            },
            "distribution_tests": distribution_tests,
            "raw_values": numeric_values.tolist()
        }
    
    def _analyze_categorical_distribution(self, values: List[Any]) -> Dict[str, Any]:
        """Analyze categorical distribution"""
        # Count frequencies
        value_counts = Counter(values)
        total_count = len(values)
        
        # Calculate proportions
        proportions = {k: v / total_count for k, v in value_counts.items()}
        
        # Calculate entropy (diversity measure)
        entropy = -sum(p * np.log2(p) for p in proportions.values() if p > 0)
        
        return {
            "type": "categorical",
            "categories": list(value_counts.keys()),
            "counts": dict(value_counts),
            "proportions": proportions,
            "entropy": entropy,
            "unique_count": len(value_counts)
        }
    
    def _test_normal_distribution(self, values: np.ndarray) -> Dict[str, float]:
        """Test if values follow normal distribution"""
        if len(values) < 8:
            return {"statistic": 0, "p_value": 0, "parameters": {}}
        
        # Shapiro-Wilk test for normality
        statistic, p_value = stats.shapiro(values)
        
        # Fit normal distribution
        mu, sigma = stats.norm.fit(values)
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "parameters": {"mu": mu, "sigma": sigma}
        }
    
    def _test_uniform_distribution(self, values: np.ndarray) -> Dict[str, float]:
        """Test if values follow uniform distribution"""
        if len(values) < 8:
            return {"statistic": 0, "p_value": 0, "parameters": {}}
        
        # Kolmogorov-Smirnov test for uniform distribution
        a, b = float(np.min(values)), float(np.max(values))
        statistic, p_value = stats.kstest(values, lambda x: stats.uniform.cdf(x, a, b-a))
        
        return {
            "statistic": statistic,
            "p_value": 1 - p_value,  # Invert for consistency
            "parameters": {"a": float(a), "b": float(b)}
        }
    
    def _test_beta_distribution(self, values: np.ndarray) -> Dict[str, float]:
        """Test if values follow beta distribution"""
        if len(values) < 8 or float(np.min(values)) < 0 or float(np.max(values)) > 1:
            return {"statistic": 0, "p_value": 0, "parameters": {}}
        
        try:
            # Fit beta distribution
            a, b, loc, scale = stats.beta.fit(values)
            
            # Kolmogorov-Smirnov test
            statistic, p_value = stats.kstest(values, lambda x: stats.beta.cdf(x, a, b, loc, scale))
            
            return {
                "statistic": statistic,
                "p_value": 1 - p_value,
                "parameters": {"a": a, "b": b, "loc": loc, "scale": scale}
            }
        except:
            return {"statistic": 0, "p_value": 0, "parameters": {}}
    
    def _test_gamma_distribution(self, values: np.ndarray) -> Dict[str, float]:
        """Test if values follow gamma distribution"""
        if len(values) < 8 or float(np.min(values)) <= 0:
            return {"statistic": 0, "p_value": 0, "parameters": {}}
        
        try:
            # Fit gamma distribution
            a, loc, scale = stats.gamma.fit(values)
            
            # Kolmogorov-Smirnov test
            statistic, p_value = stats.kstest(values, lambda x: stats.gamma.cdf(x, a, loc, scale))
            
            return {
                "statistic": statistic,
                "p_value": 1 - p_value,
                "parameters": {"a": a, "loc": loc, "scale": scale}
            }
        except:
            return {"statistic": 0, "p_value": 0, "parameters": {}}
    
    def _match_single_attribute(self, personas: List[Dict[str, Any]], 
                               attr_name: str, target: DistributionTarget, 
                               current_dist: Dict[str, Any]) -> MatchingResult:
        """Match a single attribute to its target distribution"""
        
        # Calculate matching score
        matching_score = self._calculate_matching_score(current_dist, target)
        
        # Perform statistical tests
        statistical_tests = self._perform_statistical_tests(current_dist, target)
        
        # Generate adjustment strategy
        adjusted_distribution = self._generate_adjustment_strategy(current_dist, target)
        
        return MatchingResult(
            attribute_name=attr_name,
            original_distribution=current_dist,
            target_distribution={
                "type": target.distribution_type,
                "parameters": target.parameters
            },
            adjusted_distribution=adjusted_distribution,
            matching_score=matching_score,
            statistical_tests=statistical_tests
        )
    
    def _calculate_matching_score(self, current_dist: Dict[str, Any], target: DistributionTarget) -> float:
        """Calculate how well current distribution matches target"""
        if current_dist["type"] == "numerical" and target.distribution_type in ["normal", "uniform", "beta", "gamma"]:
            return self._calculate_numerical_matching_score(current_dist, target)
        elif current_dist["type"] == "categorical" and target.distribution_type == "categorical":
            return self._calculate_categorical_matching_score(current_dist, target)
        else:
            return 0.5  # Neutral score for type mismatches
    
    def _calculate_numerical_matching_score(self, current_dist: Dict[str, Any], target: DistributionTarget) -> float:
        """Calculate matching score for numerical distributions"""
        current_params = current_dist["parameters"]
        target_params = target.parameters
        
        if target.distribution_type == "normal":
            # Compare mean and std
            mean_diff = abs(current_params["mean"] - target_params.get("mean", current_params["mean"]))
            std_diff = abs(current_params["std"] - target_params.get("std", current_params["std"]))
            
            # Normalize differences
            mean_score = max(0, 1 - mean_diff / max(abs(target_params.get("mean", 1)), 1))
            std_score = max(0, 1 - std_diff / max(target_params.get("std", 1), 1))
            
            return (mean_score + std_score) / 2
        
        # For other distributions, use a simplified approach
        return 0.7  # Assume reasonable match
    
    def _calculate_categorical_matching_score(self, current_dist: Dict[str, Any], target: DistributionTarget) -> float:
        """Calculate matching score for categorical distributions"""
        current_props = current_dist["proportions"]
        target_props = target.parameters.get("proportions", {})
        
        if not target_props:
            return 0.5
        
        # Calculate Wasserstein distance between distributions
        common_categories = set(current_props.keys()) & set(target_props.keys())
        
        if not common_categories:
            return 0.0
        
        # Calculate similarity based on proportion differences
        total_diff = sum(abs(current_props.get(cat, 0) - target_props.get(cat, 0)) 
                        for cat in set(current_props.keys()) | set(target_props.keys()))
        
        return max(0, 1 - total_diff / 2)  # Normalize to 0-1
    
    def _perform_statistical_tests(self, current_dist: Dict[str, Any], target: DistributionTarget) -> Dict[str, float]:
        """Perform statistical tests to compare distributions"""
        tests = {}
        
        if current_dist["type"] == "numerical" and target.real_world_data:
            # Perform two-sample tests
            current_values = np.array(current_dist["raw_values"])
            target_values = np.array(target.real_world_data)
            
            # Kolmogorov-Smirnov test
            ks_stat, ks_p = stats.ks_2samp(current_values, target_values)
            tests["ks_test"] = ks_p
            
            # Mann-Whitney U test
            try:
                mw_stat, mw_p = stats.mannwhitneyu(current_values, target_values, alternative='two-sided')
                tests["mann_whitney"] = mw_p
            except:
                tests["mann_whitney"] = 0.5
            
            # Wasserstein distance
            wasserstein_dist = wasserstein_distance(current_values, target_values)
            tests["wasserstein_distance"] = wasserstein_dist
        
        return tests
    
    def _generate_adjustment_strategy(self, current_dist: Dict[str, Any], target: DistributionTarget) -> Dict[str, Any]:
        """Generate strategy for adjusting distribution to match target"""
        if current_dist["type"] == "numerical":
            return self._generate_numerical_adjustment(current_dist, target)
        else:
            return self._generate_categorical_adjustment(current_dist, target)
    
    def _generate_numerical_adjustment(self, current_dist: Dict[str, Any], target: DistributionTarget) -> Dict[str, Any]:
        """Generate adjustment strategy for numerical distributions"""
        current_params = current_dist["parameters"]
        target_params = target.parameters
        
        adjustments = {
            "type": "numerical_adjustment",
            "method": "parameter_shift",
            "adjustments": {}
        }
        
        if target.distribution_type == "normal":
            target_mean = target_params.get("mean", current_params["mean"])
            target_std = target_params.get("std", current_params["std"])
            
            adjustments["adjustments"] = {
                "mean_shift": target_mean - current_params["mean"],
                "std_scale": target_std / max(current_params["std"], 0.001),
                "target_mean": target_mean,
                "target_std": target_std
            }
        
        return adjustments
    
    def _generate_categorical_adjustment(self, current_dist: Dict[str, Any], target: DistributionTarget) -> Dict[str, Any]:
        """Generate adjustment strategy for categorical distributions"""
        current_props = current_dist["proportions"]
        target_props = target.parameters.get("proportions", {})
        
        adjustments = {
            "type": "categorical_adjustment",
            "method": "resampling",
            "target_proportions": target_props,
            "current_proportions": current_props,
            "resampling_weights": {}
        }
        
        # Calculate resampling weights
        for category in set(current_props.keys()) | set(target_props.keys()):
            current_prop = current_props.get(category, 0)
            target_prop = target_props.get(category, current_prop)
            
            if current_prop > 0:
                adjustments["resampling_weights"][category] = target_prop / current_prop
            else:
                adjustments["resampling_weights"][category] = 1.0
        
        return adjustments
    
    def _apply_distribution_adjustments(self, personas: List[Dict[str, Any]], 
                                      attr_name: str, result: MatchingResult) -> List[Dict[str, Any]]:
        """Apply distribution adjustments to personas"""
        adjusted_personas = personas.copy()
        adjustment_strategy = result.adjusted_distribution
        
        if adjustment_strategy["type"] == "numerical_adjustment":
            adjusted_personas = self._apply_numerical_adjustments(
                adjusted_personas, attr_name, adjustment_strategy
            )
        elif adjustment_strategy["type"] == "categorical_adjustment":
            adjusted_personas = self._apply_categorical_adjustments(
                adjusted_personas, attr_name, adjustment_strategy
            )
        
        return adjusted_personas
    
    def _apply_numerical_adjustments(self, personas: List[Dict[str, Any]], 
                                   attr_name: str, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply numerical distribution adjustments"""
        adjustments = strategy["adjustments"]
        mean_shift = adjustments.get("mean_shift", 0)
        std_scale = adjustments.get("std_scale", 1)
        
        for persona in personas:
            # Navigate to the attribute (handle nested attributes)
            current_value = self._get_nested_attribute(persona, attr_name)
            
            if current_value is not None and isinstance(current_value, (int, float)):
                # Apply transformation: (value * scale) + shift
                adjusted_value = (float(current_value) * std_scale) + mean_shift
                self._set_nested_attribute(persona, attr_name, adjusted_value)
        
        return personas
    
    def _apply_categorical_adjustments(self, personas: List[Dict[str, Any]], 
                                     attr_name: str, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply categorical distribution adjustments through resampling"""
        target_props = strategy["target_proportions"]
        
        if not target_props:
            return personas
        
        # Extract current values
        current_values = [self._get_nested_attribute(p, attr_name) for p in personas]
        
        # Generate new values based on target distribution
        categories = list(target_props.keys())
        probabilities = list(target_props.values())
        
        # Resample values
        new_values = np.random.choice(categories, size=len(personas), p=probabilities)
        
        # Apply new values
        for i, persona in enumerate(personas):
            self._set_nested_attribute(persona, attr_name, new_values[i])
        
        return personas
    
    def _validate_distribution_coherence(self, personas: List[Dict[str, Any]], 
                                       targets: Dict[str, DistributionTarget]) -> float:
        """Validate overall coherence of adjusted distributions"""
        coherence_scores = []
        
        # Re-analyze distributions after adjustments
        adjusted_distributions = self._analyze_current_distributions(personas)
        
        for attr_name, target in targets.items():
            if attr_name in adjusted_distributions:
                score = self._calculate_matching_score(adjusted_distributions[attr_name], target)
                coherence_scores.append(score * target.weight)
        
        return float(np.mean(coherence_scores)) if coherence_scores else 0.5
    
    def _flatten_persona_attributes(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested persona attributes for analysis"""
        flattened = {}
        
        def _flatten_recursive(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, (dict, list)):
                        _flatten_recursive(value, new_key)
                    else:
                        flattened[new_key] = value
            elif isinstance(obj, list) and obj:
                # Handle lists by taking first element or length
                if isinstance(obj[0], (str, int, float)):
                    flattened[prefix] = obj[0] if len(obj) == 1 else len(obj)
        
        _flatten_recursive(persona)
        return flattened
    
    def _get_nested_attribute(self, persona: Dict[str, Any], attr_path: str) -> Any:
        """Get nested attribute value using dot notation"""
        keys = attr_path.split('.')
        value = persona
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _set_nested_attribute(self, persona: Dict[str, Any], attr_path: str, value: Any):
        """Set nested attribute value using dot notation"""
        keys = attr_path.split('.')
        current = persona
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _load_real_world_distributions(self) -> Dict[str, DistributionTarget]:
        """Load real-world demographic distributions for matching"""
        return {
            "age": DistributionTarget(
                attribute_name="age",
                distribution_type="normal",
                parameters={"mean": 38.5, "std": 22.3},
                weight=1.0
            ),
            "income_range": DistributionTarget(
                attribute_name="income_range",
                distribution_type="categorical",
                parameters={
                    "proportions": {
                        "Under $30k": 0.25,
                        "$30k-$50k": 0.20,
                        "$50k-$75k": 0.18,
                        "$75k-$100k": 0.15,
                        "$100k-$150k": 0.12,
                        "$150k+": 0.10
                    }
                },
                weight=1.0
            ),
            "education": DistributionTarget(
                attribute_name="education",
                distribution_type="categorical",
                parameters={
                    "proportions": {
                        "High School": 0.28,
                        "Some College": 0.21,
                        "Associate Degree": 0.10,
                        "Bachelor's Degree": 0.25,
                        "Master's Degree": 0.13,
                        "Doctoral Degree": 0.03
                    }
                },
                weight=1.0
            ),
            "gender": DistributionTarget(
                attribute_name="gender",
                distribution_type="categorical",
                parameters={
                    "proportions": {
                        "Male": 0.49,
                        "Female": 0.49,
                        "Non-binary": 0.02
                    }
                },
                weight=1.0
            ),
            "family_status": DistributionTarget(
                attribute_name="family_status",
                distribution_type="categorical",
                parameters={
                    "proportions": {
                        "Single": 0.35,
                        "In Relationship": 0.15,
                        "Married": 0.30,
                        "Married with Children": 0.15,
                        "Divorced": 0.04,
                        "Widowed": 0.01
                    }
                },
                weight=0.8
            )
        }
    
    def add_custom_distribution_target(self, target: DistributionTarget):
        """Add a custom distribution target"""
        self.target_distributions[target.attribute_name] = target
        logger.info(f"Added custom distribution target for {target.attribute_name}")
    
    def get_matching_report(self, matching_results: List[MatchingResult]) -> Dict[str, Any]:
        """Generate a comprehensive matching report"""
        report = {
            "overall_score": float(np.mean([r.matching_score for r in matching_results])),
            "attribute_scores": {r.attribute_name: r.matching_score for r in matching_results},
            "statistical_tests": {},
            "recommendations": []
        }
        
        # Aggregate statistical tests
        for result in matching_results:
            report["statistical_tests"][result.attribute_name] = result.statistical_tests
        
        # Generate recommendations
        for result in matching_results:
            if result.matching_score < 0.7:
                report["recommendations"].append(
                    f"Consider improving {result.attribute_name} distribution matching (score: {result.matching_score:.3f})"
                )
        
        return report