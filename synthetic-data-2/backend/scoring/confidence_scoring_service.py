"""Probability-based confidence scoring system for extracted persona attributes"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import defaultdict
from datetime import datetime
import json
import re
from enum import Enum
import math

# Statistical libraries
from scipy import stats
from scipy.special import softmax
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV

# NLP libraries
import spacy
from textblob import TextBlob
from transformers import pipeline

# Pydantic models
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ConfidenceLevel(Enum):
    """Confidence levels for persona attributes"""
    VERY_HIGH = "very_high"  # 0.9-1.0
    HIGH = "high"            # 0.7-0.9
    MEDIUM = "medium"        # 0.5-0.7
    LOW = "low"              # 0.3-0.5
    VERY_LOW = "very_low"    # 0.0-0.3

class AttributeType(Enum):
    """Types of persona attributes"""
    DEMOGRAPHIC = "demographic"
    PSYCHOGRAPHIC = "psychographic"
    BEHAVIORAL = "behavioral"
    CONTEXTUAL = "contextual"

class EvidenceType(Enum):
    """Types of evidence for confidence scoring"""
    DIRECT_MENTION = "direct_mention"
    INFERENCE = "inference"
    PATTERN_MATCHING = "pattern_matching"
    STATISTICAL_CORRELATION = "statistical_correlation"
    LLM_EXTRACTION = "llm_extraction"
    EXPERT_VALIDATION = "expert_validation"

class ConfidenceEvidence(BaseModel):
    """Evidence supporting a confidence score"""
    evidence_type: EvidenceType
    source_text: str
    extraction_method: str
    reliability_score: float
    supporting_data: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)

class AttributeConfidence(BaseModel):
    """Confidence assessment for a single attribute"""
    attribute_name: str
    attribute_type: AttributeType
    extracted_value: Any
    confidence_score: float
    confidence_level: ConfidenceLevel
    evidence: List[ConfidenceEvidence]
    uncertainty_factors: List[str]
    alternative_values: List[Tuple[Any, float]] = []  # Alternative values with their probabilities
    calibration_info: Dict[str, float] = {}

class PersonaConfidenceProfile(BaseModel):
    """Complete confidence profile for a persona"""
    persona_id: str
    overall_confidence: float
    attribute_confidences: List[AttributeConfidence]
    section_confidences: Dict[str, float]  # demographics, psychographics, behaviors
    reliability_metrics: Dict[str, float]
    quality_indicators: Dict[str, Any]
    confidence_metadata: Dict[str, Any]

class ConfidenceScoringService:
    """Probability-based confidence scoring system for persona attributes"""
    
    def __init__(self, nlp_model: str = "en_core_web_sm"):
        """
        Initialize confidence scoring service
        
        Args:
            nlp_model: spaCy model name for NLP processing
        """
        try:
            self.nlp = spacy.load(nlp_model)
        except OSError:
            logger.warning(f"spaCy model {nlp_model} not found, using basic model")
            self.nlp = None
        
        # Initialize confidence calibration models
        self.calibration_models = {}
        self.confidence_thresholds = self._load_confidence_thresholds()
        self.reliability_weights = self._load_reliability_weights()
        self.uncertainty_patterns = self._load_uncertainty_patterns()
        self.validation_rules = self._load_validation_rules()
        
        # Initialize statistical models for confidence prediction
        self.confidence_predictors = {}
        self._initialize_confidence_predictors()
    
    def _load_confidence_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Load confidence thresholds for different attribute types"""
        return {
            'demographic': {
                'age': {'high': 0.8, 'medium': 0.6, 'low': 0.4},
                'gender': {'high': 0.9, 'medium': 0.7, 'low': 0.5},
                'location': {'high': 0.7, 'medium': 0.5, 'low': 0.3},
                'occupation': {'high': 0.8, 'medium': 0.6, 'low': 0.4},
                'education': {'high': 0.7, 'medium': 0.5, 'low': 0.3},
                'income': {'high': 0.6, 'medium': 0.4, 'low': 0.2}
            },
            'psychographic': {
                'interests': {'high': 0.7, 'medium': 0.5, 'low': 0.3},
                'values': {'high': 0.6, 'medium': 0.4, 'low': 0.2},
                'personality': {'high': 0.6, 'medium': 0.4, 'low': 0.2},
                'lifestyle': {'high': 0.7, 'medium': 0.5, 'low': 0.3},
                'motivations': {'high': 0.5, 'medium': 0.3, 'low': 0.1},
                'goals': {'high': 0.5, 'medium': 0.3, 'low': 0.1}
            },
            'behavioral': {
                'shopping_habits': {'high': 0.7, 'medium': 0.5, 'low': 0.3},
                'communication': {'high': 0.6, 'medium': 0.4, 'low': 0.2},
                'decision_making': {'high': 0.5, 'medium': 0.3, 'low': 0.1},
                'technology_usage': {'high': 0.7, 'medium': 0.5, 'low': 0.3},
                'media_consumption': {'high': 0.6, 'medium': 0.4, 'low': 0.2}
            }
        }
    
    def _load_reliability_weights(self) -> Dict[str, float]:
        """Load reliability weights for different extraction methods"""
        return {
            'direct_mention': 0.9,
            'named_entity_recognition': 0.8,
            'pattern_matching': 0.7,
            'statistical_inference': 0.6,
            'llm_extraction': 0.75,
            'sentiment_analysis': 0.65,
            'topic_modeling': 0.6,
            'keyword_extraction': 0.5,
            'rule_based': 0.7,
            'machine_learning': 0.8,
            'expert_validation': 0.95
        }
    
    def _load_uncertainty_patterns(self) -> Dict[str, List[str]]:
        """Load patterns that indicate uncertainty in text"""
        return {
            'uncertainty_words': [
                'maybe', 'perhaps', 'possibly', 'might', 'could', 'may',
                'seems', 'appears', 'likely', 'probably', 'uncertain',
                'unclear', 'ambiguous', 'vague', 'approximately', 'around'
            ],
            'hedging_phrases': [
                'i think', 'i believe', 'i guess', 'i suppose',
                'it seems', 'it appears', 'sort of', 'kind of',
                'more or less', 'to some extent'
            ],
            'negation_words': [
                'not', 'no', 'never', 'none', 'neither', 'nor',
                'nothing', 'nobody', 'nowhere', 'hardly', 'barely'
            ],
            'contradiction_indicators': [
                'but', 'however', 'although', 'though', 'despite',
                'nevertheless', 'nonetheless', 'on the other hand',
                'in contrast', 'conversely'
            ]
        }
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules for confidence assessment"""
        return {
            'minimum_evidence_count': {
                'demographic': 2,
                'psychographic': 3,
                'behavioral': 2
            },
            'consistency_requirements': {
                'age_occupation': True,
                'income_lifestyle': True,
                'education_occupation': True
            },
            'source_diversity_bonus': 0.1,  # Bonus for multiple evidence sources
            'contradiction_penalty': 0.3,   # Penalty for contradictory evidence
            'uncertainty_penalty': 0.2      # Penalty for uncertain language
        }
    
    def _initialize_confidence_predictors(self):
        """Initialize machine learning models for confidence prediction"""
        # These would be trained on labeled data in a real implementation
        self.confidence_predictors = {
            'demographic': RandomForestClassifier(n_estimators=100, random_state=42),
            'psychographic': RandomForestClassifier(n_estimators=100, random_state=42),
            'behavioral': RandomForestClassifier(n_estimators=100, random_state=42)
        }
    
    async def calculate_persona_confidence(self, persona: Dict[str, Any], 
                                         extraction_metadata: Optional[Dict[str, Any]] = None) -> PersonaConfidenceProfile:
        """
        Calculate comprehensive confidence profile for a persona
        
        Args:
            persona: Persona dictionary with extracted attributes
            extraction_metadata: Metadata about the extraction process
            
        Returns:
            PersonaConfidenceProfile with detailed confidence assessment
        """
        try:
            persona_id = persona.get('id', f"persona_{datetime.now().timestamp()}")
            attribute_confidences = []
            section_confidences = {}
            
            # Calculate confidence for each section
            for section_name in ['demographics', 'psychographics', 'behaviors']:
                section_data = persona.get(section_name, {})
                if section_data:
                    section_attrs = await self._calculate_section_confidence(
                        section_name, section_data, extraction_metadata
                    )
                    attribute_confidences.extend(section_attrs)
                    
                    # Calculate section-level confidence
                    if section_attrs:
                        section_confidence = float(np.mean([attr.confidence_score for attr in section_attrs]))
                        section_confidences[section_name] = section_confidence
                    else:
                        section_confidences[section_name] = 0.0
            
            # Calculate overall confidence
            if attribute_confidences:
                overall_confidence = self._calculate_overall_confidence(attribute_confidences, section_confidences)
            else:
                overall_confidence = 0.0
            
            # Calculate reliability metrics
            reliability_metrics = self._calculate_reliability_metrics(attribute_confidences)
            
            # Calculate quality indicators
            quality_indicators = self._calculate_quality_indicators(persona, attribute_confidences)
            
            return PersonaConfidenceProfile(
                persona_id=persona_id,
                overall_confidence=overall_confidence,
                attribute_confidences=attribute_confidences,
                section_confidences=section_confidences,
                reliability_metrics=reliability_metrics,
                quality_indicators=quality_indicators,
                confidence_metadata={
                    'calculation_timestamp': datetime.now().isoformat(),
                    'total_attributes': len(attribute_confidences),
                    'high_confidence_attributes': len([a for a in attribute_confidences if a.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]]),
                    'extraction_metadata': extraction_metadata or {}
                }
            )
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return PersonaConfidenceProfile(
                persona_id=persona.get('id', 'unknown'),
                overall_confidence=0.0,
                attribute_confidences=[],
                section_confidences={},
                reliability_metrics={},
                quality_indicators={},
                confidence_metadata={'error': str(e)}
            )
    
    async def _calculate_section_confidence(self, section_name: str, section_data: Dict[str, Any], 
                                          extraction_metadata: Optional[Dict[str, Any]]) -> List[AttributeConfidence]:
        """Calculate confidence for all attributes in a section"""
        attribute_confidences = []
        
        # Map section names to attribute types
        section_type_map = {
            'demographics': AttributeType.DEMOGRAPHIC,
            'psychographics': AttributeType.PSYCHOGRAPHIC,
            'behaviors': AttributeType.BEHAVIORAL
        }
        
        attribute_type = section_type_map.get(section_name, AttributeType.CONTEXTUAL)
        
        for attr_name, attr_value in section_data.items():
            if attr_value and attr_value != 'unknown':
                confidence = await self._calculate_attribute_confidence(
                    attr_name, attr_value, attribute_type, extraction_metadata
                )
                attribute_confidences.append(confidence)
        
        return attribute_confidences
    
    async def _calculate_attribute_confidence(self, attr_name: str, attr_value: Any, 
                                            attr_type: AttributeType, 
                                            extraction_metadata: Optional[Dict[str, Any]]) -> AttributeConfidence:
        """Calculate confidence for a single attribute"""
        # Gather evidence for this attribute
        evidence = self._gather_attribute_evidence(attr_name, attr_value, extraction_metadata)
        
        # Calculate base confidence score
        base_confidence = self._calculate_base_confidence(attr_name, attr_value, attr_type, evidence)
        
        # Apply evidence-based adjustments
        evidence_adjusted_confidence = self._apply_evidence_adjustments(base_confidence, evidence)
        
        # Apply uncertainty penalties
        uncertainty_factors = self._identify_uncertainty_factors(attr_value, evidence)
        final_confidence = self._apply_uncertainty_penalties(evidence_adjusted_confidence, uncertainty_factors)
        
        # Calibrate confidence score
        calibrated_confidence = self._calibrate_confidence(final_confidence, attr_name, attr_type)
        
        # Determine confidence level
        confidence_level = self._determine_confidence_level(calibrated_confidence)
        
        # Generate alternative values if confidence is low
        alternative_values = []
        if calibrated_confidence < 0.7:
            alternative_values = self._generate_alternative_values(attr_name, attr_value, evidence)
        
        return AttributeConfidence(
            attribute_name=attr_name,
            attribute_type=attr_type,
            extracted_value=attr_value,
            confidence_score=calibrated_confidence,
            confidence_level=confidence_level,
            evidence=evidence,
            uncertainty_factors=uncertainty_factors,
            alternative_values=alternative_values,
            calibration_info={
                'base_confidence': base_confidence,
                'evidence_adjusted': evidence_adjusted_confidence,
                'uncertainty_adjusted': final_confidence,
                'calibrated': calibrated_confidence
            }
        )
    
    def _gather_attribute_evidence(self, attr_name: str, attr_value: Any, 
                                 extraction_metadata: Optional[Dict[str, Any]]) -> List[ConfidenceEvidence]:
        """Gather evidence supporting the extracted attribute value"""
        evidence = []
        
        if not extraction_metadata:
            return evidence
        
        # Check for direct mentions
        source_text = extraction_metadata.get('source_text', '')
        if source_text and isinstance(attr_value, str):
            if attr_value.lower() in source_text.lower():
                evidence.append(ConfidenceEvidence(
                    evidence_type=EvidenceType.DIRECT_MENTION,
                    source_text=source_text,
                    extraction_method="text_search",
                    reliability_score=0.9,
                    supporting_data={'match_type': 'exact'}
                ))
        
        # Check extraction method metadata
        extraction_methods = extraction_metadata.get('extraction_methods', {})
        for method, method_data in extraction_methods.items():
            if attr_name in method_data.get('extracted_attributes', []):
                reliability = self.reliability_weights.get(method, 0.5)
                
                evidence.append(ConfidenceEvidence(
                    evidence_type=EvidenceType.LLM_EXTRACTION if 'llm' in method else EvidenceType.PATTERN_MATCHING,
                    source_text=method_data.get('source_text', ''),
                    extraction_method=method,
                    reliability_score=reliability,
                    supporting_data=method_data
                ))
        
        # Check for statistical correlations
        correlations = extraction_metadata.get('statistical_correlations', {})
        if attr_name in correlations:
            correlation_data = correlations[attr_name]
            evidence.append(ConfidenceEvidence(
                evidence_type=EvidenceType.STATISTICAL_CORRELATION,
                source_text="",
                extraction_method="statistical_analysis",
                reliability_score=correlation_data.get('correlation_strength', 0.5),
                supporting_data=correlation_data
            ))
        
        return evidence
    
    def _calculate_base_confidence(self, attr_name: str, attr_value: Any, 
                                 attr_type: AttributeType, evidence: List[ConfidenceEvidence]) -> float:
        """Calculate base confidence score for an attribute"""
        # Get attribute-specific thresholds
        type_name = attr_type.value
        thresholds = self.confidence_thresholds.get(type_name, {}).get(attr_name, {'high': 0.7, 'medium': 0.5, 'low': 0.3})
        
        if not evidence:
            return 0.1  # Very low confidence without evidence
        
        # Calculate evidence-weighted confidence
        total_weight = 0
        weighted_confidence = 0
        
        for ev in evidence:
            weight = ev.reliability_score
            confidence_contribution = self._evidence_to_confidence(ev)
            
            weighted_confidence += confidence_contribution * weight
            total_weight += weight
        
        if total_weight > 0:
            base_confidence = weighted_confidence / total_weight
        else:
            base_confidence = 0.1
        
        # Apply attribute-specific scaling
        if attr_name in ['age', 'gender', 'occupation']:  # High-confidence attributes
            base_confidence = min(1.0, base_confidence * 1.2)
        elif attr_name in ['motivations', 'goals', 'values']:  # Psychographic attributes - removed penalty
            base_confidence = base_confidence * 1.0  # No penalty for psychographic attributes
        
        return float(np.clip(base_confidence, 0.0, 1.0))
    
    def _evidence_to_confidence(self, evidence: ConfidenceEvidence) -> float:
        """Convert evidence to confidence contribution"""
        base_confidence = 0.6  # Increased from 0.5
        
        if evidence.evidence_type == EvidenceType.DIRECT_MENTION:
            base_confidence = 0.9
        elif evidence.evidence_type == EvidenceType.LLM_EXTRACTION:
            base_confidence = 0.85  # Increased from 0.75
        elif evidence.evidence_type == EvidenceType.PATTERN_MATCHING:
            base_confidence = 0.7
        elif evidence.evidence_type == EvidenceType.STATISTICAL_CORRELATION:
            base_confidence = 0.6
        elif evidence.evidence_type == EvidenceType.INFERENCE:
            base_confidence = 0.55  # Increased from 0.5
        
        # Adjust based on supporting data
        supporting_data = evidence.supporting_data
        if 'confidence_score' in supporting_data:
            model_confidence = supporting_data['confidence_score']
            base_confidence = (base_confidence + model_confidence) / 2
        
        return base_confidence
    
    def _apply_evidence_adjustments(self, base_confidence: float, evidence: List[ConfidenceEvidence]) -> float:
        """Apply adjustments based on evidence quality and quantity"""
        adjusted_confidence = base_confidence
        
        # Multiple evidence sources bonus
        if len(evidence) > 1:
            unique_sources = len(set(ev.extraction_method for ev in evidence))
            if unique_sources > 1:
                adjusted_confidence += self.validation_rules['source_diversity_bonus']
        
        # Evidence consistency check
        if len(evidence) > 1:
            reliability_scores = [ev.reliability_score for ev in evidence]
            consistency = 1.0 - float(np.std(reliability_scores))  # Higher consistency = lower std
            adjusted_confidence *= (0.8 + 0.2 * consistency)  # Scale by consistency
        
        # High-quality evidence bonus
        high_quality_evidence = [ev for ev in evidence if ev.reliability_score > 0.8]
        if high_quality_evidence:
            adjusted_confidence += 0.05 * len(high_quality_evidence)
        
        return float(np.clip(adjusted_confidence, 0.0, 1.0))
    
    def _identify_uncertainty_factors(self, attr_value: Any, evidence: List[ConfidenceEvidence]) -> List[str]:
        """Identify factors that increase uncertainty"""
        uncertainty_factors = []
        
        # Check for uncertainty language in evidence
        for ev in evidence:
            source_text = ev.source_text.lower()
            
            # Check for uncertainty words
            for word in self.uncertainty_patterns['uncertainty_words']:
                if word in source_text:
                    uncertainty_factors.append(f"uncertainty_language: {word}")
                    break
            
            # Check for hedging phrases
            for phrase in self.uncertainty_patterns['hedging_phrases']:
                if phrase in source_text:
                    uncertainty_factors.append(f"hedging: {phrase}")
                    break
            
            # Check for contradictions
            for indicator in self.uncertainty_patterns['contradiction_indicators']:
                if indicator in source_text:
                    uncertainty_factors.append(f"contradiction_indicator: {indicator}")
                    break
        
        # Check for conflicting evidence
        if len(evidence) > 1:
            reliability_range = max([ev.reliability_score for ev in evidence]) - min([ev.reliability_score for ev in evidence])
            if reliability_range > 0.3:
                uncertainty_factors.append("conflicting_evidence_reliability")
        
        # Check for vague or generic values
        if isinstance(attr_value, str):
            if attr_value.lower() in ['unknown', 'unclear', 'various', 'mixed', 'general']:
                uncertainty_factors.append("vague_value")
        
        return list(set(uncertainty_factors))  # Remove duplicates
    
    def _apply_uncertainty_penalties(self, confidence: float, uncertainty_factors: List[str]) -> float:
        """Apply penalties for uncertainty factors"""
        adjusted_confidence = confidence
        
        # Apply penalty for each uncertainty factor
        for factor in uncertainty_factors:
            if 'uncertainty_language' in factor or 'hedging' in factor:
                adjusted_confidence *= (1 - self.validation_rules['uncertainty_penalty'])
            elif 'contradiction' in factor or 'conflicting' in factor:
                adjusted_confidence *= (1 - self.validation_rules['contradiction_penalty'])
            elif 'vague_value' in factor:
                adjusted_confidence *= 0.7
        
        return float(np.clip(adjusted_confidence, 0.0, 1.0))
    
    def _calibrate_confidence(self, confidence: float, attr_name: str, attr_type: AttributeType) -> float:
        """Calibrate confidence score using learned calibration"""
        # In a real implementation, this would use trained calibration models
        # For now, apply simple calibration based on attribute type
        
        calibration_factors = {
            AttributeType.DEMOGRAPHIC: 1.0,    # Demographics are generally more reliable
            AttributeType.PSYCHOGRAPHIC: 0.9,  # Psychographics are less certain
            AttributeType.BEHAVIORAL: 0.85,    # Behaviors are moderately certain
            AttributeType.CONTEXTUAL: 0.8      # Contextual attributes are least certain
        }
        
        calibration_factor = calibration_factors.get(attr_type, 0.8)
        calibrated = confidence * calibration_factor
        
        # Apply sigmoid calibration to avoid extreme values
        calibrated = 1 / (1 + np.exp(-5 * (calibrated - 0.5)))
        
        return float(np.clip(calibrated, 0.0, 1.0))
    
    def _determine_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """Determine confidence level from score"""
        if confidence_score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence_score >= 0.7:
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence_score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _generate_alternative_values(self, attr_name: str, attr_value: Any, 
                                   evidence: List[ConfidenceEvidence]) -> List[Tuple[Any, float]]:
        """Generate alternative values with probabilities for low-confidence attributes"""
        alternatives = []
        
        # Extract alternative values from evidence
        for ev in evidence:
            supporting_data = ev.supporting_data
            
            # Check for alternative predictions
            if 'alternatives' in supporting_data:
                for alt_value, alt_prob in supporting_data['alternatives']:
                    if alt_value != attr_value:
                        alternatives.append((alt_value, alt_prob * ev.reliability_score))
            
            # Check for uncertainty ranges (for numeric attributes)
            if 'uncertainty_range' in supporting_data and isinstance(attr_value, (int, float)):
                range_data = supporting_data['uncertainty_range']
                lower_bound = range_data.get('lower', attr_value * 0.8)
                upper_bound = range_data.get('upper', attr_value * 1.2)
                
                alternatives.append((f"{lower_bound}-{upper_bound}", 0.6))
        
        # Sort by probability and return top alternatives
        alternatives.sort(key=lambda x: x[1], reverse=True)
        return alternatives[:3]  # Return top 3 alternatives
    
    def _calculate_overall_confidence(self, attribute_confidences: List[AttributeConfidence], 
                                    section_confidences: Dict[str, float]) -> float:
        """Calculate overall persona confidence"""
        if not attribute_confidences:
            return 0.0
        
        # Weight different sections
        section_weights = {
            'demographics': 0.4,
            'psychographics': 0.35,
            'behaviors': 0.25
        }
        
        # Calculate weighted section confidence
        weighted_confidence = 0
        total_weight = 0
        
        for section, confidence in section_confidences.items():
            weight = section_weights.get(section, 0.33)
            weighted_confidence += confidence * weight
            total_weight += weight
        
        if total_weight > 0:
            overall_confidence = weighted_confidence / total_weight
        else:
            overall_confidence = float(np.mean([attr.confidence_score for attr in attribute_confidences]))
        
        # Apply quality adjustments (modified to be less aggressive)
        high_confidence_ratio = len([a for a in attribute_confidences if a.confidence_score > 0.5]) / len(attribute_confidences)
        overall_confidence *= (0.85 + 0.15 * high_confidence_ratio)
        
        return float(np.clip(overall_confidence, 0.0, 1.0))
    
    def _calculate_reliability_metrics(self, attribute_confidences: List[AttributeConfidence]) -> Dict[str, float]:
        """Calculate reliability metrics for the confidence assessment"""
        if not attribute_confidences:
            return {}
        
        confidence_scores = [attr.confidence_score for attr in attribute_confidences]
        
        return {
            'mean_confidence': float(np.mean(confidence_scores)),
            'median_confidence': float(np.median(confidence_scores)),
            'std_confidence': float(np.std(confidence_scores)),
            'min_confidence': float(np.min(confidence_scores)),
            'max_confidence': float(np.max(confidence_scores)),
            'high_confidence_ratio': len([c for c in confidence_scores if c > 0.7]) / len(confidence_scores),
            'low_confidence_ratio': len([c for c in confidence_scores if c < 0.3]) / len(confidence_scores),
            'evidence_diversity': len(set(ev.evidence_type for attr in attribute_confidences for ev in attr.evidence)) / max(1, len(EvidenceType)),
            'total_evidence_count': sum(len(attr.evidence) for attr in attribute_confidences)
        }
    
    def _calculate_quality_indicators(self, persona: Dict[str, Any], 
                                    attribute_confidences: List[AttributeConfidence]) -> Dict[str, Any]:
        """Calculate quality indicators for the persona"""
        quality_indicators = {
            'completeness': self._calculate_completeness(persona),
            'consistency': self._calculate_consistency(attribute_confidences),
            'specificity': self._calculate_specificity(persona),
            'evidence_quality': self._calculate_evidence_quality(attribute_confidences),
            'uncertainty_level': self._calculate_uncertainty_level(attribute_confidences)
        }
        
        return quality_indicators
    
    def _calculate_completeness(self, persona: Dict[str, Any]) -> float:
        """Calculate persona completeness score"""
        required_fields = {
            'demographics': ['age_range', 'gender', 'occupation'],
            'psychographics': ['interests', 'values'],
            'behaviors': ['shopping_habits']
        }
        
        total_required = sum(len(fields) for fields in required_fields.values())
        filled_required = 0
        
        for section, fields in required_fields.items():
            section_data = persona.get(section, {})
            for field in fields:
                if section_data.get(field) and section_data[field] != 'unknown':
                    filled_required += 1
        
        return filled_required / total_required if total_required > 0 else 0.0
    
    def _calculate_consistency(self, attribute_confidences: List[AttributeConfidence]) -> float:
        """Calculate consistency score across attributes"""
        if len(attribute_confidences) < 2:
            return 1.0
        
        # Calculate consistency based on confidence score variance
        confidence_scores = [attr.confidence_score for attr in attribute_confidences]
        consistency = 1.0 - (float(np.std(confidence_scores)) / float(np.mean(confidence_scores))) if float(np.mean(confidence_scores)) > 0 else 0.0
        
        return float(np.clip(consistency, 0.0, 1.0))
    
    def _calculate_specificity(self, persona: Dict[str, Any]) -> float:
        """Calculate specificity score (how specific vs generic the persona is)"""
        generic_terms = ['general', 'various', 'mixed', 'average', 'typical', 'normal', 'standard']
        total_values = 0
        specific_values = 0
        
        for section in ['demographics', 'psychographics', 'behaviors']:
            section_data = persona.get(section, {})
            for value in section_data.values():
                if value and value != 'unknown':
                    total_values += 1
                    if isinstance(value, str) and not any(term in value.lower() for term in generic_terms):
                        specific_values += 1
                    elif isinstance(value, list) and len(value) > 0:
                        specific_values += 1
        
        return specific_values / total_values if total_values > 0 else 0.0
    
    def _calculate_evidence_quality(self, attribute_confidences: List[AttributeConfidence]) -> float:
        """Calculate overall evidence quality score"""
        if not attribute_confidences:
            return 0.0
        
        total_evidence = 0
        high_quality_evidence = 0
        
        for attr in attribute_confidences:
            for evidence in attr.evidence:
                total_evidence += 1
                if evidence.reliability_score > 0.7:
                    high_quality_evidence += 1
        
        return high_quality_evidence / total_evidence if total_evidence > 0 else 0.0
    
    def _calculate_uncertainty_level(self, attribute_confidences: List[AttributeConfidence]) -> float:
        """Calculate overall uncertainty level"""
        if not attribute_confidences:
            return 1.0
        
        total_uncertainty_factors = sum(len(attr.uncertainty_factors) for attr in attribute_confidences)
        avg_uncertainty_factors = total_uncertainty_factors / len(attribute_confidences)
        
        # Normalize to 0-1 scale (assuming max 5 uncertainty factors per attribute)
        uncertainty_level = min(1.0, avg_uncertainty_factors / 5.0)
        
        return uncertainty_level
    
    def create_confidence_report(self, confidence_profile: PersonaConfidenceProfile) -> Dict[str, Any]:
        """Create a comprehensive confidence report"""
        report = {
            "executive_summary": {
                "persona_id": confidence_profile.persona_id,
                "overall_confidence": confidence_profile.overall_confidence,
                "confidence_level": self._determine_confidence_level(confidence_profile.overall_confidence).value,
                "total_attributes": len(confidence_profile.attribute_confidences),
                "high_confidence_attributes": len([a for a in confidence_profile.attribute_confidences if a.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]])
            },
            "section_analysis": {
                "section_confidences": confidence_profile.section_confidences,
                "strongest_section": max(confidence_profile.section_confidences.items(), key=lambda x: x[1])[0] if confidence_profile.section_confidences else None,
                "weakest_section": min(confidence_profile.section_confidences.items(), key=lambda x: x[1])[0] if confidence_profile.section_confidences else None
            },
            "attribute_details": [
                {
                    "name": attr.attribute_name,
                    "value": attr.extracted_value,
                    "confidence_score": attr.confidence_score,
                    "confidence_level": attr.confidence_level.value,
                    "evidence_count": len(attr.evidence),
                    "uncertainty_factors": attr.uncertainty_factors,
                    "has_alternatives": len(attr.alternative_values) > 0
                }
                for attr in confidence_profile.attribute_confidences
            ],
            "reliability_metrics": confidence_profile.reliability_metrics,
            "quality_indicators": confidence_profile.quality_indicators,
            "recommendations": self._generate_confidence_recommendations(confidence_profile),
            "metadata": confidence_profile.confidence_metadata
        }
        
        return report
    
    def _generate_confidence_recommendations(self, confidence_profile: PersonaConfidenceProfile) -> List[str]:
        """Generate recommendations for improving confidence"""
        recommendations = []
        
        # Low overall confidence
        if confidence_profile.overall_confidence < 0.5:
            recommendations.append("Overall confidence is low - consider gathering more evidence or using additional extraction methods")
        
        # Low-confidence attributes
        low_confidence_attrs = [a for a in confidence_profile.attribute_confidences if a.confidence_score < 0.4]
        if low_confidence_attrs:
            recommendations.append(f"Review {len(low_confidence_attrs)} low-confidence attributes: {', '.join([a.attribute_name for a in low_confidence_attrs[:3]])}")
        
        # High uncertainty
        high_uncertainty_attrs = [a for a in confidence_profile.attribute_confidences if len(a.uncertainty_factors) > 2]
        if high_uncertainty_attrs:
            recommendations.append(f"Address uncertainty factors in {len(high_uncertainty_attrs)} attributes")
        
        # Missing evidence
        low_evidence_attrs = [a for a in confidence_profile.attribute_confidences if len(a.evidence) < 2]
        if low_evidence_attrs:
            recommendations.append(f"Gather additional evidence for {len(low_evidence_attrs)} attributes with limited support")
        
        # Quality improvements
        quality_indicators = confidence_profile.quality_indicators
        if quality_indicators.get('completeness', 0) < 0.7:
            recommendations.append("Improve persona completeness by filling missing required attributes")
        
        if quality_indicators.get('specificity', 0) < 0.6:
            recommendations.append("Increase persona specificity by replacing generic terms with specific details")
        
        return recommendations[:5]  # Limit to top 5 recommendations