import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import json
import re
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import asyncio

@dataclass
class AdversarialFeedback:
    """Feedback from adversarial validation"""
    realism_score: float
    diversity_score: float
    consistency_score: float
    overall_score: float
    improvement_suggestions: List[str]
    outlier_flags: List[bool]

class AdversarialValidationEngine:
    """GAN-inspired adversarial validation system for persona generation"""
    
    def __init__(self):
        self.discriminator_history = []
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.scaler = StandardScaler()
        self.outlier_detector = IsolationForest(contamination=0.1, random_state=42)
        self.is_fitted = False
        
        # Thresholds for quality assessment
        self.realism_threshold = 0.7
        self.diversity_threshold = 0.6
        self.consistency_threshold = 0.8
        
        logger.info("Initialized AdversarialValidationEngine")
    
    async def validate_personas(self, personas: List[Dict[str, Any]], 
                              demographic_constraints: Optional[Dict[str, Any]] = None) -> AdversarialFeedback:
        """Main validation method that acts as discriminator"""
        try:
            # Extract features for analysis
            features = self._extract_features(personas)
            
            # Calculate realism score
            realism_score = await self._calculate_realism_score(personas, features)
            
            # Calculate diversity score
            diversity_score = await self._calculate_diversity_score(personas, features)
            
            # Calculate consistency score
            consistency_score = await self._calculate_consistency_score(personas, demographic_constraints)
            
            # Detect outliers
            outlier_flags = self._detect_outliers(features)
            
            # Calculate overall score
            overall_score = (realism_score * 0.4 + diversity_score * 0.3 + consistency_score * 0.3)
            
            # Generate improvement suggestions
            suggestions = self._generate_improvement_suggestions(
                realism_score, diversity_score, consistency_score, outlier_flags
            )
            
            feedback = AdversarialFeedback(
                realism_score=realism_score,
                diversity_score=diversity_score,
                consistency_score=consistency_score,
                overall_score=overall_score,
                improvement_suggestions=suggestions,
                outlier_flags=outlier_flags
            )
            
            # Store feedback for learning
            self.discriminator_history.append({
                'feedback': feedback,
                'personas_count': len(personas),
                'timestamp': pd.Timestamp.now()
            })
            
            logger.info(f"Adversarial validation completed: overall={overall_score:.3f}, realism={realism_score:.3f}, diversity={diversity_score:.3f}")
            return feedback
            
        except Exception as e:
            logger.error(f"Error in adversarial validation: {e}")
            return AdversarialFeedback(
                realism_score=0.5, diversity_score=0.5, consistency_score=0.5,
                overall_score=0.5, improvement_suggestions=["Validation failed"], outlier_flags=[]
            )
    
    def _extract_features(self, personas: List[Dict[str, Any]]) -> np.ndarray:
        """Extract numerical features from personas for analysis"""
        features = []
        
        for persona in personas:
            feature_vector = []
            
            # Age feature
            age = self._extract_age_from_narrative(persona.get('narrative', ''))
            feature_vector.append(age if age else 30)  # Default age
            
            # Income feature (normalized)
            income = persona.get('demographics', {}).get('income', 50000)
            feature_vector.append(income / 100000)  # Normalize to 0-1 range
            
            # Text length features
            narrative = persona.get('narrative', '')
            feature_vector.extend([
                len(narrative),
                len(narrative.split()),
                len(set(narrative.lower().split()))
            ])
            
            # Demographic consistency features
            demo = persona.get('demographics', {})
            feature_vector.extend([
                1 if demo.get('gender') in ['Male', 'Female', 'Other'] else 0,
                1 if demo.get('location') else 0,
                1 if demo.get('education') else 0
            ])
            
            features.append(feature_vector)
        
        return np.array(features)
    
    async def _calculate_realism_score(self, personas: List[Dict[str, Any]], features: np.ndarray) -> float:
        """Calculate how realistic the personas appear"""
        realism_scores = []
        
        for persona in personas:
            score = 0.0
            
            # Check narrative quality
            narrative = persona.get('narrative', '')
            if len(narrative) > 100:  # Minimum length
                score += 0.3
            if self._has_coherent_structure(narrative):
                score += 0.3
            if self._has_realistic_details(narrative):
                score += 0.4
            
            realism_scores.append(min(score, 1.0))
        
        return float(np.mean(realism_scores)) if realism_scores else 0.0
    
    async def _calculate_diversity_score(self, personas: List[Dict[str, Any]], features: np.ndarray) -> float:
        """Calculate diversity within the persona set"""
        if len(personas) < 2:
            return 0.0
        
        # Text diversity using TF-IDF
        narratives = [persona.get('narrative', '') for persona in personas]
        try:
            if not self.is_fitted:
                tfidf_matrix = self.vectorizer.fit_transform(narratives)
                self.is_fitted = True
            else:
                tfidf_matrix = self.vectorizer.transform(narratives)
            
            # Calculate pairwise similarities
            similarities = cosine_similarity(tfidf_matrix)
            
            # Diversity is inverse of average similarity (excluding diagonal)
            mask = np.ones_like(similarities, dtype=bool)
            np.fill_diagonal(mask, False)
            avg_similarity = similarities[mask].mean()
            text_diversity = 1 - avg_similarity
            
        except Exception:
            text_diversity = 0.5
        
        # Feature diversity
        if features.shape[0] > 1:
            feature_std = float(np.std(features, axis=0).mean())
            feature_diversity = min(feature_std / 10, 1.0)  # Normalize
        else:
            feature_diversity = 0.0
        
        return (text_diversity * 0.7 + feature_diversity * 0.3)
    
    async def _calculate_consistency_score(self, personas: List[Dict[str, Any]], 
                                         constraints: Optional[Dict[str, Any]]) -> float:
        """Calculate consistency with demographic constraints"""
        if not constraints:
            return 1.0
        
        consistency_scores = []
        
        for persona in personas:
            score = 0.0
            checks = 0
            
            # Age consistency
            if 'age_range' in constraints:
                age_range = constraints['age_range']
                narrative_age = self._extract_age_from_narrative(persona.get('narrative', ''))
                if narrative_age and age_range[0] <= narrative_age <= age_range[1]:
                    score += 1
                checks += 1
            
            # Gender consistency
            if 'gender' in constraints:
                expected_gender = constraints['gender']
                persona_gender = persona.get('demographics', {}).get('gender')
                if persona_gender == expected_gender:
                    score += 1
                checks += 1
            
            # Location consistency
            if 'location' in constraints:
                expected_location = constraints['location']
                persona_location = persona.get('demographics', {}).get('location', '')
                if expected_location.lower() in persona_location.lower():
                    score += 1
                checks += 1
            
            consistency_scores.append(score / max(checks, 1))
        
        return float(np.mean(consistency_scores)) if consistency_scores else 1.0
    
    def _detect_outliers(self, features: np.ndarray) -> List[bool]:
        """Detect outlier personas using isolation forest"""
        if features.shape[0] < 3:
            return [False] * features.shape[0]
        
        try:
            # Fit and predict outliers
            outlier_predictions = self.outlier_detector.fit_predict(features)
            return [pred == -1 for pred in outlier_predictions]
        except Exception:
            return [False] * features.shape[0]
    
    def _generate_improvement_suggestions(self, realism: float, diversity: float, 
                                        consistency: float, outliers: List[bool]) -> List[str]:
        """Generate actionable improvement suggestions"""
        suggestions = []
        
        if realism < self.realism_threshold:
            suggestions.append("Improve narrative realism by adding more specific details and coherent structure")
        
        if diversity < self.diversity_threshold:
            suggestions.append("Increase persona diversity by varying demographics, backgrounds, and narrative styles")
        
        if consistency < self.consistency_threshold:
            suggestions.append("Improve demographic consistency by ensuring narratives match specified constraints")
        
        if any(outliers):
            outlier_count = sum(outliers)
            suggestions.append(f"Review {outlier_count} outlier personas that may need refinement")
        
        if not suggestions:
            suggestions.append("Personas meet quality standards - consider minor refinements for optimization")
        
        return suggestions
    
    def _extract_age_from_narrative(self, narrative: str) -> Optional[int]:
        """Extract age from narrative text"""
        age_patterns = [
            r'(\d+)\s*years?\s*old',
            r'age\s*(\d+)',
            r'(\d+)\s*year\s*old',
            r'I\s*am\s*(\d+)'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, narrative, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                if 18 <= age <= 100:  # Reasonable age range
                    return age
        return None
    
    def _has_coherent_structure(self, narrative: str) -> bool:
        """Check if narrative has coherent structure"""
        sentences = narrative.split('.')
        return len(sentences) >= 3 and len(narrative.split()) >= 50
    
    def _has_realistic_details(self, narrative: str) -> bool:
        """Check if narrative contains realistic details"""
        realistic_indicators = [
            r'\b(work|job|career|profession)\b',
            r'\b(family|spouse|children|parents)\b',
            r'\b(hobby|interest|enjoy|love)\b',
            r'\b(live|lives|home|house)\b',
            r'\b(education|school|university|college)\b'
        ]
        
        matches = sum(1 for pattern in realistic_indicators 
                     if re.search(pattern, narrative, re.IGNORECASE))
        return matches >= 3
    
    def get_discriminator_performance(self) -> Dict[str, Any]:
        """Get performance metrics of the discriminator"""
        if not self.discriminator_history:
            return {"status": "No validation history available"}
        
        recent_feedback = [entry['feedback'] for entry in self.discriminator_history[-10:]]
        
        return {
            "total_validations": len(self.discriminator_history),
            "avg_realism_score": float(np.mean([f.realism_score for f in recent_feedback])),
            "avg_diversity_score": float(np.mean([f.diversity_score for f in recent_feedback])),
            "avg_consistency_score": float(np.mean([f.consistency_score for f in recent_feedback])),
            "avg_overall_score": float(np.mean([f.overall_score for f in recent_feedback])),
            "improvement_trend": self._calculate_improvement_trend()
        }
    
    def _calculate_improvement_trend(self) -> str:
        """Calculate if scores are improving over time"""
        if len(self.discriminator_history) < 5:
            return "Insufficient data"
        
        recent_scores = [entry['feedback'].overall_score for entry in self.discriminator_history[-5:]]
        older_scores = [entry['feedback'].overall_score for entry in self.discriminator_history[-10:-5]]
        
        if not older_scores:
            return "Insufficient data"
        
        recent_avg = float(np.mean(recent_scores))
        older_avg = float(np.mean(older_scores))
        
        if recent_avg > older_avg + 0.05:
            return "Improving"
        elif recent_avg < older_avg - 0.05:
            return "Declining"
        else:
            return "Stable"