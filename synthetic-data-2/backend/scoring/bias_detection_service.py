"""Automated bias detection and mitigation system for demographic over-representation"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from datetime import datetime
import json
from enum import Enum
import warnings

# Statistical analysis
from scipy import stats
from scipy.stats import chi2_contingency, fisher_exact
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

# Data visualization (for analysis)
import matplotlib.pyplot as plt
import seaborn as sns

# Pydantic models
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class BiasType(Enum):
    """Types of bias that can be detected"""
    DEMOGRAPHIC_OVERREPRESENTATION = "demographic_overrepresentation"
    DEMOGRAPHIC_UNDERREPRESENTATION = "demographic_underrepresentation"
    INTERSECTIONAL_BIAS = "intersectional_bias"
    STEREOTYPICAL_ASSOCIATION = "stereotypical_association"
    CULTURAL_BIAS = "cultural_bias"
    SOCIOECONOMIC_BIAS = "socioeconomic_bias"
    AGE_BIAS = "age_bias"
    GENDER_BIAS = "gender_bias"
    GEOGRAPHIC_BIAS = "geographic_bias"
    OCCUPATIONAL_BIAS = "occupational_bias"

class BiasSeverity(Enum):
    """Severity levels for detected bias"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"

class BiasDetection(BaseModel):
    """Individual bias detection result"""
    bias_type: BiasType
    severity: BiasSeverity
    description: str
    affected_groups: List[str]
    statistical_evidence: Dict[str, float]
    confidence: float
    mitigation_suggestions: List[str]
    evidence_details: Dict[str, Any]

class BiasAnalysisResult(BaseModel):
    """Complete bias analysis result"""
    overall_bias_score: float
    detected_biases: List[BiasDetection]
    demographic_distribution: Dict[str, Dict[str, float]]
    intersectional_analysis: Dict[str, Any]
    mitigation_recommendations: List[str]
    diversity_metrics: Dict[str, float]
    analysis_metadata: Dict[str, Any]

class MitigationStrategy(BaseModel):
    """Bias mitigation strategy"""
    strategy_type: str
    target_bias: BiasType
    implementation_steps: List[str]
    expected_impact: str
    priority: str
    resources_required: List[str]

class BiasDetectionService:
    """Automated bias detection and mitigation system"""
    
    def __init__(self):
        """
        Initialize bias detection service
        """
        self.demographic_benchmarks = self._load_demographic_benchmarks()
        self.bias_patterns = self._load_bias_patterns()
        self.stereotype_associations = self._load_stereotype_associations()
        self.intersectional_rules = self._load_intersectional_rules()
        
    def _load_demographic_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """Load demographic benchmarks for comparison"""
        # These would ideally come from census data or representative samples
        return {
            'gender': {
                'male': 0.49,
                'female': 0.49,
                'non-binary': 0.02
            },
            'age_groups': {
                'teens': 0.13,
                'twenties': 0.14,
                'thirties': 0.13,
                'forties': 0.13,
                'fifties': 0.13,
                'sixties': 0.16,
                'seventies+': 0.18
            },
            'education': {
                'high_school': 0.28,
                'college': 0.20,
                'bachelors': 0.33,
                'masters': 0.15,
                'phd': 0.04
            },
            'income_level': {
                'low': 0.25,
                'medium': 0.45,
                'upper-middle': 0.25,
                'high': 0.05
            },
            'location_type': {
                'urban': 0.82,
                'suburban': 0.15,
                'rural': 0.03
            }
        }
    
    def _load_bias_patterns(self) -> Dict[str, Any]:
        """Load known bias patterns"""
        return {
            'gender_occupation': {
                'male_dominated': {
                    'occupations': ['engineer', 'developer', 'ceo', 'cto', 'architect', 'mechanic', 'pilot'],
                    'threshold': 0.8  # If >80% male, flag as potential bias
                },
                'female_dominated': {
                    'occupations': ['nurse', 'teacher', 'secretary', 'assistant', 'social_worker', 'librarian'],
                    'threshold': 0.8
                }
            },
            'age_technology': {
                'young_tech_bias': {
                    'age_threshold': 35,
                    'tech_keywords': ['social_media', 'gaming', 'apps', 'streaming', 'influencer'],
                    'threshold': 0.7
                },
                'old_tech_aversion': {
                    'age_threshold': 60,
                    'traditional_keywords': ['newspaper', 'radio', 'traditional', 'offline'],
                    'threshold': 0.7
                }
            },
            'income_lifestyle': {
                'high_income_luxury': {
                    'income_threshold': 'high',
                    'luxury_keywords': ['luxury', 'premium', 'exclusive', 'high-end', 'designer'],
                    'threshold': 0.6
                },
                'low_income_budget': {
                    'income_threshold': 'low',
                    'budget_keywords': ['budget', 'cheap', 'discount', 'sale', 'affordable'],
                    'threshold': 0.6
                }
            },
            'geographic_stereotypes': {
                'urban_liberal': {
                    'location_type': 'urban',
                    'stereotype_keywords': ['liberal', 'progressive', 'diverse', 'cosmopolitan'],
                    'threshold': 0.5
                },
                'rural_conservative': {
                    'location_type': 'rural',
                    'stereotype_keywords': ['conservative', 'traditional', 'simple', 'family-values'],
                    'threshold': 0.5
                }
            }
        }
    
    def _load_stereotype_associations(self) -> Dict[str, List[str]]:
        """Load stereotype associations to detect"""
        return {
            'gender_stereotypes': {
                'male': ['aggressive', 'competitive', 'logical', 'technical', 'leadership'],
                'female': ['nurturing', 'emotional', 'caring', 'supportive', 'collaborative']
            },
            'age_stereotypes': {
                'young': ['tech-savvy', 'energetic', 'inexperienced', 'social', 'trendy'],
                'old': ['traditional', 'experienced', 'slow', 'wise', 'conservative']
            },
            'cultural_stereotypes': {
                'asian': ['mathematical', 'studious', 'quiet', 'disciplined'],
                'hispanic': ['family-oriented', 'hardworking', 'traditional'],
                'african_american': ['athletic', 'musical', 'community-oriented']
            }
        }
    
    def _load_intersectional_rules(self) -> List[Dict[str, Any]]:
        """Load intersectional bias detection rules"""
        return [
            {
                'name': 'young_female_tech_underrepresentation',
                'conditions': {
                    'gender': 'female',
                    'age_range': ['teens', 'twenties', 'thirties'],
                    'occupation_keywords': ['tech', 'engineer', 'developer', 'programmer']
                },
                'expected_representation': 0.3,
                'bias_type': BiasType.DEMOGRAPHIC_UNDERREPRESENTATION
            },
            {
                'name': 'older_male_caregiving_underrepresentation',
                'conditions': {
                    'gender': 'male',
                    'age_range': ['forties', 'fifties', 'sixties'],
                    'occupation_keywords': ['nurse', 'teacher', 'caregiver', 'social_worker']
                },
                'expected_representation': 0.2,
                'bias_type': BiasType.DEMOGRAPHIC_UNDERREPRESENTATION
            },
            {
                'name': 'high_income_diversity_check',
                'conditions': {
                    'income_level': 'high',
                    'occupation_keywords': ['executive', 'ceo', 'director', 'vp']
                },
                'diversity_requirements': {
                    'gender_diversity': 0.4,  # At least 40% non-male
                    'age_diversity': 0.3      # At least 30% under 50
                },
                'bias_type': BiasType.INTERSECTIONAL_BIAS
            }
        ]
    
    async def analyze_bias(self, personas: List[Dict[str, Any]], 
                          analysis_config: Optional[Dict[str, Any]] = None) -> BiasAnalysisResult:
        """
        Perform comprehensive bias analysis on persona dataset
        
        Args:
            personas: List of persona dictionaries
            analysis_config: Optional configuration for analysis
            
        Returns:
            BiasAnalysisResult with detailed bias analysis
        """
        try:
            # Convert personas to DataFrame for analysis
            df = self._personas_to_dataframe(personas)
            
            detected_biases = []
            
            # 1. Demographic distribution analysis
            demographic_dist = self._analyze_demographic_distribution(df)
            demo_biases = self._detect_demographic_bias(demographic_dist)
            detected_biases.extend(demo_biases)
            
            # 2. Intersectional bias analysis
            intersectional_analysis = self._analyze_intersectional_bias(df)
            intersectional_biases = self._detect_intersectional_bias(df, intersectional_analysis)
            detected_biases.extend(intersectional_biases)
            
            # 3. Stereotypical association analysis
            stereotype_biases = self._detect_stereotypical_associations(df)
            detected_biases.extend(stereotype_biases)
            
            # 4. Occupational bias analysis
            occupational_biases = self._detect_occupational_bias(df)
            detected_biases.extend(occupational_biases)
            
            # 5. Geographic bias analysis
            geographic_biases = self._detect_geographic_bias(df)
            detected_biases.extend(geographic_biases)
            
            # Calculate overall bias score
            overall_bias_score = self._calculate_overall_bias_score(detected_biases)
            
            # Calculate diversity metrics
            diversity_metrics = self._calculate_diversity_metrics(df)
            
            # Generate mitigation recommendations
            mitigation_recommendations = self._generate_mitigation_recommendations(detected_biases)
            
            return BiasAnalysisResult(
                overall_bias_score=overall_bias_score,
                detected_biases=detected_biases,
                demographic_distribution=demographic_dist,
                intersectional_analysis=intersectional_analysis,
                mitigation_recommendations=mitigation_recommendations,
                diversity_metrics=diversity_metrics,
                analysis_metadata={
                    'total_personas': len(personas),
                    'total_biases_detected': len(detected_biases),
                    'analysis_timestamp': datetime.now().isoformat(),
                    'bias_types_found': list(set([b.bias_type.value for b in detected_biases]))
                }
            )
            
        except Exception as e:
            logger.error(f"Bias analysis failed: {e}")
            return BiasAnalysisResult(
                overall_bias_score=1.0,  # Assume high bias if analysis fails
                detected_biases=[
                    BiasDetection(
                        bias_type=BiasType.DEMOGRAPHIC_OVERREPRESENTATION,
                        severity=BiasSeverity.CRITICAL,
                        description=f"Bias analysis failed: {str(e)}",
                        affected_groups=[],
                        statistical_evidence={},
                        confidence=1.0,
                        mitigation_suggestions=["Fix bias analysis system"],
                        evidence_details={'error': str(e)}
                    )
                ],
                demographic_distribution={},
                intersectional_analysis={},
                mitigation_recommendations=["Resolve bias analysis errors"],
                diversity_metrics={},
                analysis_metadata={'error': str(e)}
            )
    
    def _personas_to_dataframe(self, personas: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert personas to pandas DataFrame for analysis"""
        rows = []
        
        for i, persona in enumerate(personas):
            row = {'persona_id': i}
            
            # Extract demographics
            demographics = persona.get('demographics', {})
            for key, value in demographics.items():
                row[f'demo_{key}'] = value
            
            # Extract psychographics
            psychographics = persona.get('psychographics', {})
            for key, value in psychographics.items():
                if isinstance(value, list):
                    row[f'psycho_{key}'] = ' '.join(value) if value else ''
                else:
                    row[f'psycho_{key}'] = value or ''
            
            # Extract behaviors
            behaviors = persona.get('behaviors', {})
            for key, value in behaviors.items():
                if isinstance(value, list):
                    row[f'behavior_{key}'] = ' '.join(value) if value else ''
                else:
                    row[f'behavior_{key}'] = value or ''
            
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def _analyze_demographic_distribution(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Analyze demographic distribution"""
        distribution = {}
        
        # Analyze each demographic attribute
        demographic_columns = [col for col in df.columns if col.startswith('demo_')]
        
        for col in demographic_columns:
            attr_name = col.replace('demo_', '')
            if col in df.columns:
                value_counts = df[col].value_counts(normalize=True, dropna=True)
                distribution[attr_name] = value_counts.to_dict()
        
        return distribution
    
    def _detect_demographic_bias(self, demographic_dist: Dict[str, Dict[str, float]]) -> List[BiasDetection]:
        """Detect demographic bias by comparing to benchmarks"""
        biases = []
        
        for attr_name, distribution in demographic_dist.items():
            if attr_name in self.demographic_benchmarks:
                benchmark = self.demographic_benchmarks[attr_name]
                
                for value, observed_freq in distribution.items():
                    expected_freq = benchmark.get(value, 0.1)  # Default 10% if not in benchmark
                    
                    # Calculate deviation
                    deviation = abs(observed_freq - expected_freq)
                    relative_deviation = deviation / expected_freq if expected_freq > 0 else 1.0
                    
                    # Determine if this is significant bias
                    if relative_deviation > 0.5:  # More than 50% deviation
                        severity = self._calculate_bias_severity(relative_deviation)
                        bias_type = BiasType.DEMOGRAPHIC_OVERREPRESENTATION if observed_freq > expected_freq else BiasType.DEMOGRAPHIC_UNDERREPRESENTATION
                        
                        biases.append(BiasDetection(
                            bias_type=bias_type,
                            severity=severity,
                            description=f"{attr_name.title()} '{value}' is {'over' if observed_freq > expected_freq else 'under'}represented: {observed_freq:.1%} vs expected {expected_freq:.1%}",
                            affected_groups=[f"{attr_name}:{value}"],
                            statistical_evidence={
                                'observed_frequency': observed_freq,
                                'expected_frequency': expected_freq,
                                'relative_deviation': relative_deviation,
                                'absolute_deviation': deviation
                            },
                            confidence=min(0.9, relative_deviation),
                            mitigation_suggestions=[
                                f"Adjust sampling to better represent {attr_name} '{value}'",
                                f"Review data sources for {attr_name} bias"
                            ],
                            evidence_details={
                                'benchmark_source': 'demographic_benchmarks',
                                'sample_size': len(distribution)
                            }
                        ))
        
        return biases
    
    def _analyze_intersectional_bias(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze intersectional bias patterns"""
        intersectional_analysis = {}
        
        # Gender-occupation intersections
        if 'demo_gender' in df.columns and 'demo_occupation' in df.columns:
            gender_occupation = pd.crosstab(df['demo_gender'], df['demo_occupation'], normalize='columns')
            intersectional_analysis['gender_occupation'] = gender_occupation.to_dict()
        
        # Age-income intersections
        if 'demo_age_range' in df.columns and 'demo_income_level' in df.columns:
            age_income = pd.crosstab(df['demo_age_range'], df['demo_income_level'], normalize='columns')
            intersectional_analysis['age_income'] = age_income.to_dict()
        
        # Education-occupation intersections
        if 'demo_education' in df.columns and 'demo_occupation' in df.columns:
            education_occupation = pd.crosstab(df['demo_education'], df['demo_occupation'], normalize='columns')
            intersectional_analysis['education_occupation'] = education_occupation.to_dict()
        
        return intersectional_analysis
    
    def _detect_intersectional_bias(self, df: pd.DataFrame, intersectional_analysis: Dict[str, Any]) -> List[BiasDetection]:
        """Detect intersectional bias using predefined rules"""
        biases = []
        
        for rule in self.intersectional_rules:
            try:
                # Apply rule conditions
                mask = pd.Series([True] * len(df))
                
                conditions = rule['conditions']
                for attr, expected_values in conditions.items():
                    if attr == 'occupation_keywords':
                        # Check if occupation contains any of the keywords
                        if 'demo_occupation' in df.columns:
                            occupation_mask = df['demo_occupation'].str.contains('|'.join(expected_values), case=False, na=False)
                            mask = mask & occupation_mask
                    else:
                        col_name = f'demo_{attr}'
                        if col_name in df.columns:
                            if isinstance(expected_values, list):
                                attr_mask = df[col_name].isin(expected_values)
                            else:
                                attr_mask = df[col_name] == expected_values
                            mask = mask & attr_mask
                
                # Calculate actual representation
                matching_personas = df[mask]
                actual_representation = len(matching_personas) / len(df) if len(df) > 0 else 0
                
                # Check against expected representation
                if 'expected_representation' in rule:
                    expected_rep = rule['expected_representation']
                    deviation = abs(actual_representation - expected_rep)
                    
                    if deviation > 0.1:  # 10% threshold
                        severity = self._calculate_bias_severity(deviation / expected_rep if expected_rep > 0 else 1.0)
                        
                        biases.append(BiasDetection(
                            bias_type=rule['bias_type'],
                            severity=severity,
                            description=f"Intersectional bias detected in {rule['name']}: {actual_representation:.1%} vs expected {expected_rep:.1%}",
                            affected_groups=[rule['name']],
                            statistical_evidence={
                                'actual_representation': actual_representation,
                                'expected_representation': expected_rep,
                                'deviation': deviation,
                                'sample_size': len(matching_personas)
                            },
                            confidence=0.7,
                            mitigation_suggestions=[
                                f"Increase representation of {rule['name']} group",
                                "Review intersectional sampling strategies"
                            ],
                            evidence_details={
                                'rule_name': rule['name'],
                                'conditions': conditions
                            }
                        ))
                
                # Check diversity requirements
                if 'diversity_requirements' in rule and len(matching_personas) > 0:
                    diversity_reqs = rule['diversity_requirements']
                    
                    for diversity_type, min_threshold in diversity_reqs.items():
                        if diversity_type == 'gender_diversity' and 'demo_gender' in matching_personas.columns:
                            non_male_ratio = (matching_personas['demo_gender'] != 'male').mean()
                            if non_male_ratio < min_threshold:
                                biases.append(BiasDetection(
                                    bias_type=BiasType.INTERSECTIONAL_BIAS,
                                    severity=BiasSeverity.MEDIUM,
                                    description=f"Low gender diversity in {rule['name']}: {non_male_ratio:.1%} non-male vs required {min_threshold:.1%}",
                                    affected_groups=[rule['name']],
                                    statistical_evidence={
                                        'non_male_ratio': non_male_ratio,
                                        'required_threshold': min_threshold
                                    },
                                    confidence=0.8,
                                    mitigation_suggestions=["Increase gender diversity in high-income executive roles"],
                                    evidence_details={'diversity_type': diversity_type}
                                ))
                        
                        elif diversity_type == 'age_diversity' and 'demo_age_range' in matching_personas.columns:
                            young_age_groups = ['teens', 'twenties', 'thirties', 'forties']
                            young_ratio = matching_personas['demo_age_range'].isin(young_age_groups).mean()
                            if young_ratio < min_threshold:
                                biases.append(BiasDetection(
                                    bias_type=BiasType.INTERSECTIONAL_BIAS,
                                    severity=BiasSeverity.MEDIUM,
                                    description=f"Low age diversity in {rule['name']}: {young_ratio:.1%} under 50 vs required {min_threshold:.1%}",
                                    affected_groups=[rule['name']],
                                    statistical_evidence={
                                        'young_ratio': young_ratio,
                                        'required_threshold': min_threshold
                                    },
                                    confidence=0.8,
                                    mitigation_suggestions=["Include younger professionals in executive roles"],
                                    evidence_details={'diversity_type': diversity_type}
                                ))
                
            except Exception as e:
                logger.warning(f"Intersectional bias rule {rule['name']} failed: {e}")
        
        return biases
    
    def _detect_stereotypical_associations(self, df: pd.DataFrame) -> List[BiasDetection]:
        """Detect stereotypical associations in personas"""
        biases = []
        
        # Gender stereotype detection
        if 'demo_gender' in df.columns:
            for gender, stereotypes in self.stereotype_associations['gender_stereotypes'].items():
                gender_personas = df[df['demo_gender'] == gender]
                
                if len(gender_personas) > 0:
                    # Check psychographic attributes for stereotypes
                    psycho_columns = [col for col in df.columns if col.startswith('psycho_')]
                    
                    for col in psycho_columns:
                        if col in gender_personas.columns:
                            text_content = ' '.join(gender_personas[col].fillna('').astype(str)).lower()
                            
                            stereotype_count = sum(1 for stereotype in stereotypes if stereotype.lower() in text_content)
                            stereotype_ratio = stereotype_count / len(stereotypes)
                            
                            if stereotype_ratio > 0.4:  # More than 40% of stereotypes present
                                biases.append(BiasDetection(
                                    bias_type=BiasType.STEREOTYPICAL_ASSOCIATION,
                                    severity=self._calculate_bias_severity(stereotype_ratio),
                                    description=f"High {gender} stereotype presence in {col.replace('psycho_', '')}: {stereotype_ratio:.1%} of stereotypes detected",
                                    affected_groups=[f"gender:{gender}"],
                                    statistical_evidence={
                                        'stereotype_ratio': stereotype_ratio,
                                        'stereotypes_found': stereotype_count,
                                        'total_stereotypes': len(stereotypes)
                                    },
                                    confidence=0.6,
                                    mitigation_suggestions=[
                                        f"Diversify {gender} persona attributes beyond stereotypes",
                                        f"Include counter-stereotypical traits for {gender} personas"
                                    ],
                                    evidence_details={
                                        'stereotypes_checked': stereotypes,
                                        'attribute': col
                                    }
                                ))
        
        return biases
    
    def _detect_occupational_bias(self, df: pd.DataFrame) -> List[BiasDetection]:
        """Detect occupational bias patterns"""
        biases = []
        
        if 'demo_gender' in df.columns and 'demo_occupation' in df.columns:
            # Analyze gender distribution by occupation
            occupation_gender = pd.crosstab(df['demo_occupation'], df['demo_gender'], normalize='index')
            
            for occupation in occupation_gender.index:
                if 'male' in occupation_gender.columns and 'female' in occupation_gender.columns:
                    male_ratio = occupation_gender.loc[occupation, 'male'] if 'male' in occupation_gender.loc[occupation] else 0
                    female_ratio = occupation_gender.loc[occupation, 'female'] if 'female' in occupation_gender.loc[occupation] else 0
                    
                    # Check against bias patterns
                    occupation_lower = occupation.lower()
                    
                    # Check male-dominated occupations
                    male_dominated_occs = self.bias_patterns['gender_occupation']['male_dominated']['occupations']
                    if any(occ in occupation_lower for occ in male_dominated_occs):
                        threshold = self.bias_patterns['gender_occupation']['male_dominated']['threshold']
                        if male_ratio > threshold:
                            biases.append(BiasDetection(
                                bias_type=BiasType.GENDER_BIAS,
                                severity=self._calculate_bias_severity((male_ratio - 0.5) * 2),
                                description=f"Male over-representation in {occupation}: {male_ratio:.1%} male",
                                affected_groups=[f"occupation:{occupation}", "gender:male"],
                                statistical_evidence={
                                    'male_ratio': male_ratio,
                                    'female_ratio': female_ratio,
                                    'bias_threshold': threshold
                                },
                                confidence=0.7,
                                mitigation_suggestions=[
                                    f"Increase female representation in {occupation}",
                                    "Review recruitment and sampling for gender balance"
                                ],
                                evidence_details={'occupation_category': 'male_dominated'}
                            ))
                    
                    # Check female-dominated occupations
                    female_dominated_occs = self.bias_patterns['gender_occupation']['female_dominated']['occupations']
                    if any(occ in occupation_lower for occ in female_dominated_occs):
                        threshold = self.bias_patterns['gender_occupation']['female_dominated']['threshold']
                        if female_ratio > threshold:
                            biases.append(BiasDetection(
                                bias_type=BiasType.GENDER_BIAS,
                                severity=self._calculate_bias_severity((female_ratio - 0.5) * 2),
                                description=f"Female over-representation in {occupation}: {female_ratio:.1%} female",
                                affected_groups=[f"occupation:{occupation}", "gender:female"],
                                statistical_evidence={
                                    'male_ratio': male_ratio,
                                    'female_ratio': female_ratio,
                                    'bias_threshold': threshold
                                },
                                confidence=0.7,
                                mitigation_suggestions=[
                                    f"Increase male representation in {occupation}",
                                    "Review recruitment and sampling for gender balance"
                                ],
                                evidence_details={'occupation_category': 'female_dominated'}
                            ))
        
        return biases
    
    def _detect_geographic_bias(self, df: pd.DataFrame) -> List[BiasDetection]:
        """Detect geographic bias patterns"""
        biases = []
        
        if 'demo_location' in df.columns:
            # Analyze location distribution
            location_dist = df['demo_location'].value_counts(normalize=True)
            
            # Check for over-concentration in specific areas
            for location, frequency in location_dist.items():
                if frequency > 0.3:  # More than 30% from one location
                    biases.append(BiasDetection(
                        bias_type=BiasType.GEOGRAPHIC_BIAS,
                        severity=self._calculate_bias_severity(frequency),
                        description=f"Geographic over-concentration in {location}: {frequency:.1%} of personas",
                        affected_groups=[f"location:{location}"],
                        statistical_evidence={
                            'location_frequency': frequency,
                            'concentration_threshold': 0.3
                        },
                        confidence=0.8,
                        mitigation_suggestions=[
                            "Diversify geographic representation",
                            f"Reduce over-sampling from {location}"
                        ],
                        evidence_details={'location_distribution': location_dist.to_dict()}
                    ))
        
        return biases
    
    def _calculate_bias_severity(self, deviation_ratio: float) -> BiasSeverity:
        """Calculate bias severity based on deviation ratio"""
        if deviation_ratio >= 1.0:
            return BiasSeverity.CRITICAL
        elif deviation_ratio >= 0.7:
            return BiasSeverity.HIGH
        elif deviation_ratio >= 0.4:
            return BiasSeverity.MEDIUM
        elif deviation_ratio >= 0.2:
            return BiasSeverity.LOW
        else:
            return BiasSeverity.MINIMAL
    
    def _calculate_overall_bias_score(self, detected_biases: List[BiasDetection]) -> float:
        """Calculate overall bias score (0 = no bias, 1 = maximum bias)"""
        if not detected_biases:
            return 0.0
        
        # Weight biases by severity
        severity_weights = {
            BiasSeverity.CRITICAL: 1.0,
            BiasSeverity.HIGH: 0.8,
            BiasSeverity.MEDIUM: 0.6,
            BiasSeverity.LOW: 0.4,
            BiasSeverity.MINIMAL: 0.2
        }
        
        total_weighted_score = sum(severity_weights[bias.severity] * bias.confidence for bias in detected_biases)
        max_possible_score = len(detected_biases) * 1.0  # Maximum if all were critical with 100% confidence
        
        return min(1.0, total_weighted_score / max_possible_score) if max_possible_score > 0 else 0.0
    
    def _calculate_diversity_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate diversity metrics for the persona dataset"""
        metrics = {}
        
        # Gender diversity (Simpson's diversity index)
        if 'demo_gender' in df.columns:
            gender_counts = df['demo_gender'].value_counts()
            gender_diversity = self._simpson_diversity_index(gender_counts)
            metrics['gender_diversity'] = float(gender_diversity)
        
        # Age diversity
        if 'demo_age_range' in df.columns:
            age_counts = df['demo_age_range'].value_counts()
            age_diversity = self._simpson_diversity_index(age_counts)
            metrics['age_diversity'] = float(age_diversity)
        
        # Education diversity
        if 'demo_education' in df.columns:
            education_counts = df['demo_education'].value_counts()
            education_diversity = self._simpson_diversity_index(education_counts)
            metrics['education_diversity'] = float(education_diversity)
        
        # Occupation diversity
        if 'demo_occupation' in df.columns:
            occupation_counts = df['demo_occupation'].value_counts()
            occupation_diversity = self._simpson_diversity_index(occupation_counts)
            metrics['occupation_diversity'] = float(occupation_diversity)
        
        # Overall diversity (average of individual diversities)
        if metrics:
            metrics['overall_diversity'] = float(np.mean(list(metrics.values())))
        
        return metrics
    
    def _simpson_diversity_index(self, counts: pd.Series) -> float:
        """Calculate Simpson's diversity index"""
        if len(counts) == 0:
            return 0.0
        
        total = counts.sum()
        proportions = counts / total
        simpson_index = 1 - sum(proportions ** 2)
        
        return float(simpson_index)
    
    def _generate_mitigation_recommendations(self, detected_biases: List[BiasDetection]) -> List[str]:
        """Generate mitigation recommendations based on detected biases"""
        recommendations = set()
        
        # Group biases by type
        bias_types = defaultdict(list)
        for bias in detected_biases:
            bias_types[bias.bias_type].append(bias)
        
        # Generate type-specific recommendations
        if BiasType.DEMOGRAPHIC_OVERREPRESENTATION in bias_types or BiasType.DEMOGRAPHIC_UNDERREPRESENTATION in bias_types:
            recommendations.add("Implement stratified sampling to ensure representative demographic distribution")
            recommendations.add("Review data sources for demographic bias and diversify collection methods")
        
        if BiasType.GENDER_BIAS in bias_types:
            recommendations.add("Establish gender quotas for different occupational categories")
            recommendations.add("Review and challenge gender stereotypes in persona generation")
        
        if BiasType.STEREOTYPICAL_ASSOCIATION in bias_types:
            recommendations.add("Implement counter-stereotypical attribute generation")
            recommendations.add("Use diverse training data that challenges common stereotypes")
        
        if BiasType.INTERSECTIONAL_BIAS in bias_types:
            recommendations.add("Develop intersectional sampling strategies")
            recommendations.add("Monitor and adjust for multiple demographic intersections")
        
        if BiasType.GEOGRAPHIC_BIAS in bias_types:
            recommendations.add("Diversify geographic representation in persona sampling")
            recommendations.add("Weight personas by population density to avoid urban bias")
        
        # Critical bias recommendations
        critical_biases = [b for b in detected_biases if b.severity == BiasSeverity.CRITICAL]
        if critical_biases:
            recommendations.add("Address critical biases before deploying personas")
            recommendations.add("Consider regenerating personas with bias-aware sampling")
        
        # General recommendations
        if len(detected_biases) > 5:
            recommendations.add("Implement comprehensive bias monitoring and correction pipeline")
        
        return list(recommendations)[:8]  # Limit to top 8 recommendations
    
    async def generate_mitigation_strategies(self, bias_analysis: BiasAnalysisResult) -> List[MitigationStrategy]:
        """Generate detailed mitigation strategies for detected biases"""
        strategies = []
        
        # Group biases by type for strategy generation
        bias_groups = defaultdict(list)
        for bias in bias_analysis.detected_biases:
            bias_groups[bias.bias_type].append(bias)
        
        for bias_type, biases in bias_groups.items():
            if bias_type == BiasType.DEMOGRAPHIC_OVERREPRESENTATION:
                strategies.append(MitigationStrategy(
                    strategy_type="demographic_rebalancing",
                    target_bias=bias_type,
                    implementation_steps=[
                        "Identify over-represented demographic groups",
                        "Implement weighted sampling to reduce over-representation",
                        "Increase sampling from under-represented groups",
                        "Monitor demographic distribution in real-time",
                        "Validate changes against benchmark populations"
                    ],
                    expected_impact="Reduce demographic over-representation by 50-70%",
                    priority="high",
                    resources_required=["Updated sampling algorithms", "Demographic benchmark data", "Monitoring dashboard"]
                ))
            
            elif bias_type == BiasType.GENDER_BIAS:
                strategies.append(MitigationStrategy(
                    strategy_type="gender_balance_enforcement",
                    target_bias=bias_type,
                    implementation_steps=[
                        "Establish gender quotas for each occupation category",
                        "Implement gender-aware persona generation",
                        "Review and update occupational stereotypes database",
                        "Add gender diversity checks to validation pipeline",
                        "Train models on gender-balanced datasets"
                    ],
                    expected_impact="Achieve 40-60% gender balance across occupations",
                    priority="high",
                    resources_required=["Gender quota system", "Balanced training data", "Validation rules"]
                ))
            
            elif bias_type == BiasType.STEREOTYPICAL_ASSOCIATION:
                strategies.append(MitigationStrategy(
                    strategy_type="stereotype_disruption",
                    target_bias=bias_type,
                    implementation_steps=[
                        "Identify common stereotypical associations",
                        "Generate counter-stereotypical persona attributes",
                        "Implement stereotype detection in validation",
                        "Use diverse, anti-bias training data",
                        "Regular stereotype pattern audits"
                    ],
                    expected_impact="Reduce stereotypical associations by 60-80%",
                    priority="medium",
                    resources_required=["Stereotype detection algorithms", "Counter-stereotype datasets", "Audit tools"]
                ))
        
        return strategies
    
    def create_bias_report(self, bias_analysis: BiasAnalysisResult, 
                          output_format: str = "json") -> Dict[str, Any]:
        """Create comprehensive bias report"""
        report = {
            "executive_summary": {
                "overall_bias_score": bias_analysis.overall_bias_score,
                "total_biases_detected": len(bias_analysis.detected_biases),
                "critical_biases": len([b for b in bias_analysis.detected_biases if b.severity == BiasSeverity.CRITICAL]),
                "high_biases": len([b for b in bias_analysis.detected_biases if b.severity == BiasSeverity.HIGH]),
                "recommendation_count": len(bias_analysis.mitigation_recommendations)
            },
            "detailed_findings": {
                "detected_biases": [bias.dict() for bias in bias_analysis.detected_biases],
                "demographic_distribution": bias_analysis.demographic_distribution,
                "diversity_metrics": bias_analysis.diversity_metrics
            },
            "recommendations": {
                "immediate_actions": bias_analysis.mitigation_recommendations[:3],
                "long_term_strategies": bias_analysis.mitigation_recommendations[3:],
                "priority_biases": [b.dict() for b in bias_analysis.detected_biases if b.severity in [BiasSeverity.CRITICAL, BiasSeverity.HIGH]]
            },
            "metadata": bias_analysis.analysis_metadata
        }
        
        return report