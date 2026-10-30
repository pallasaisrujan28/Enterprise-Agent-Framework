"""Two-stage validation system with structural and domain expert validation"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
import json
import re
from collections import defaultdict
import numpy as np
from enum import Enum

# Validation libraries
from pydantic import BaseModel, Field, ValidationError
from jsonschema import validate, ValidationError as JsonSchemaValidationError

# Statistical analysis
from scipy import stats
from scipy.spatial.distance import cosine
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

class ValidationStage(Enum):
    """Validation stages"""
    STRUCTURAL = "structural"
    DOMAIN_EXPERT = "domain_expert"
    ADVERSARIAL = "adversarial"
    CONSISTENCY = "consistency"
    BIAS_CHECK = "bias_check"

class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ValidationIssue(BaseModel):
    """Individual validation issue"""
    stage: ValidationStage
    severity: ValidationSeverity
    issue_type: str
    description: str
    affected_attribute: Optional[str] = None
    suggested_fix: Optional[str] = None
    confidence: float
    evidence: List[str] = []

class ValidationResult(BaseModel):
    """Complete validation result"""
    overall_score: float
    stage_scores: Dict[str, float]
    issues: List[ValidationIssue]
    passed_checks: List[str]
    recommendations: List[str]
    validation_metadata: Dict[str, Any]
    is_valid: bool
    quality_metrics: Dict[str, float]

class PersonaValidationService:
    """Two-stage validation service for persona quality assessment"""
    
    def __init__(self, llm_service=None):
        """
        Initialize validation service
        
        Args:
            llm_service: LLM service for adversarial questioning
        """
        self.llm_service = llm_service
        self.persona_schema = self._load_persona_schema()
        self.validation_rules = self._load_validation_rules()
        self.bias_detection_patterns = self._load_bias_patterns()
        self.consistency_checks = self._load_consistency_checks()
    
    def _load_persona_schema(self) -> Dict[str, Any]:
        """Load persona validation schema"""
        return {
            "type": "object",
            "required": ["id", "name", "demographics", "psychographics", "behaviors"],
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9_-]+$"
                },
                "name": {
                    "type": "string",
                    "minLength": 2,
                    "maxLength": 100
                },
                "demographics": {
                    "type": "object",
                    "required": ["age_range"],
                    "properties": {
                        "age_range": {
                            "type": "string",
                            "pattern": "^\\d+-\\d+$|^\\d+$|^(teens|twenties|thirties|forties|fifties|sixties|seventies|unknown)$"
                        },
                        "gender": {
                            "type": "string",
                            "enum": ["male", "female", "non-binary", "unknown"]
                        },
                        "location": {
                            "type": "string",
                            "minLength": 2
                        },
                        "occupation": {
                            "type": "string",
                            "minLength": 2
                        },
                        "income_level": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "upper-middle", "unknown"]
                        },
                        "education": {
                            "type": "string",
                            "enum": ["high_school", "college", "bachelors", "masters", "phd", "unknown"]
                        },
                        "family_status": {
                            "type": "string"
                        }
                    }
                },
                "psychographics": {
                    "type": "object",
                    "properties": {
                        "interests": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 10
                        },
                        "values": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 8
                        },
                        "personality_traits": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 8
                        },
                        "lifestyle": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "motivations": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "pain_points": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "goals": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "behaviors": {
                    "type": "object",
                    "properties": {
                        "shopping_habits": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "communication_preferences": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "decision_factors": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "media_consumption": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "technology_usage": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "brand_preferences": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "confidence_scores": {
                    "type": "object",
                    "properties": {
                        "demographics": {"type": "number", "minimum": 0, "maximum": 1},
                        "psychographics": {"type": "number", "minimum": 0, "maximum": 1},
                        "behaviors": {"type": "number", "minimum": 0, "maximum": 1},
                        "overall": {"type": "number", "minimum": 0, "maximum": 1}
                    }
                }
            }
        }
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules for persona quality assessment"""
        return {
            'demographic_consistency': {
                'age_occupation': {
                    'student': {'min_age': 16, 'max_age': 30},
                    'retired': {'min_age': 60, 'max_age': 100},
                    'executive': {'min_age': 30, 'max_age': 70},
                    'intern': {'min_age': 18, 'max_age': 25}
                },
                'age_education': {
                    'high_school': {'min_age': 14, 'max_age': 25},
                    'bachelors': {'min_age': 18, 'max_age': 80},
                    'masters': {'min_age': 22, 'max_age': 80},
                    'phd': {'min_age': 25, 'max_age': 80}
                },
                'income_occupation': {
                    'student': {'max_income': 'medium'},
                    'executive': {'min_income': 'medium'},
                    'doctor': {'min_income': 'medium'},
                    'teacher': {'max_income': 'high'}
                }
            },
            'psychographic_coherence': {
                'conflicting_values': [
                    (['environmentally_conscious'], ['luxury_focused']),
                    (['budget_conscious'], ['luxury_focused']),
                    (['family_oriented'], ['career_focused'])
                ],
                'supporting_combinations': [
                    (['health_conscious'], ['fitness', 'wellness']),
                    (['technology_enthusiast'], ['innovation', 'gadgets']),
                    (['family_oriented'], ['home', 'children'])
                ]
            },
            'behavioral_logic': {
                'shopping_decision_consistency': {
                    'price_sensitive': ['discount', 'budget', 'sale'],
                    'quality_focused': ['premium', 'durable', 'reliable'],
                    'brand_loyal': ['consistent', 'trusted', 'favorite']
                },
                'communication_technology_alignment': {
                    'tech_savvy': ['digital', 'social_media', 'apps'],
                    'traditional': ['phone', 'email', 'in_person']
                }
            },
            'completeness_requirements': {
                'minimum_attributes': {
                    'demographics': 3,
                    'psychographics': 5,
                    'behaviors': 3
                },
                'required_fields': ['age_range', 'interests', 'values']
            }
        }
    
    def _load_bias_patterns(self) -> Dict[str, Any]:
        """Load bias detection patterns"""
        return {
            'gender_occupation_bias': {
                'male_dominated': ['engineer', 'developer', 'ceo', 'cto', 'architect'],
                'female_dominated': ['nurse', 'teacher', 'secretary', 'assistant'],
                'neutral': ['manager', 'analyst', 'consultant', 'designer']
            },
            'age_technology_bias': {
                'young_tech_assumption': {
                    'age_threshold': 30,
                    'tech_indicators': ['social_media', 'apps', 'gaming', 'streaming']
                },
                'old_tech_aversion': {
                    'age_threshold': 60,
                    'tech_indicators': ['traditional', 'phone', 'newspaper']
                }
            },
            'income_lifestyle_bias': {
                'high_income_assumptions': {
                    'income_level': 'high',
                    'lifestyle_indicators': ['luxury', 'premium', 'exclusive', 'high-end']
                },
                'low_income_assumptions': {
                    'income_level': 'low',
                    'lifestyle_indicators': ['budget', 'cheap', 'discount', 'struggling']
                }
            },
            'cultural_stereotypes': {
                'location_assumptions': {
                    'urban': ['tech-savvy', 'liberal', 'diverse'],
                    'rural': ['traditional', 'conservative', 'simple']
                }
            }
        }
    
    def _load_consistency_checks(self) -> List[Dict[str, Any]]:
        """Load consistency check definitions"""
        return [
            {
                'name': 'age_education_consistency',
                'description': 'Check if education level is consistent with age',
                'check_function': self._check_age_education_consistency
            },
            {
                'name': 'income_occupation_consistency',
                'description': 'Check if income level matches occupation expectations',
                'check_function': self._check_income_occupation_consistency
            },
            {
                'name': 'values_behavior_alignment',
                'description': 'Check if behaviors align with stated values',
                'check_function': self._check_values_behavior_alignment
            },
            {
                'name': 'interest_lifestyle_coherence',
                'description': 'Check if interests are coherent with lifestyle',
                'check_function': self._check_interest_lifestyle_coherence
            },
            {
                'name': 'demographic_psychographic_harmony',
                'description': 'Check harmony between demographics and psychographics',
                'check_function': self._check_demographic_psychographic_harmony
            }
        ]
    
    async def validate_personas(self, personas: List[Dict[str, Any]], 
                               validation_config: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Perform comprehensive two-stage validation of personas
        
        Args:
            personas: List of persona dictionaries to validate
            validation_config: Optional validation configuration
            
        Returns:
            ValidationResult with comprehensive validation assessment
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            issues = []
            passed_checks = []
            stage_scores = {}
            
            # Stage 1: Structural Validation
            structural_issues, structural_score = await self._validate_structural(personas)
            issues.extend(structural_issues)
            stage_scores['structural'] = structural_score
            
            # Stage 2: Domain Expert Validation
            domain_issues, domain_score = await self._validate_domain_expert(personas)
            issues.extend(domain_issues)
            stage_scores['domain_expert'] = domain_score
            
            # Stage 3: Adversarial Questioning (if LLM available)
            if self.llm_service:
                adversarial_issues, adversarial_score = await self._validate_adversarial(personas)
                issues.extend(adversarial_issues)
                stage_scores['adversarial'] = adversarial_score
            
            # Stage 4: Consistency Checks
            consistency_issues, consistency_score = await self._validate_consistency(personas)
            issues.extend(consistency_issues)
            stage_scores['consistency'] = consistency_score
            
            # Stage 5: Bias Detection
            bias_issues, bias_score = await self._validate_bias_detection(personas)
            issues.extend(bias_issues)
            stage_scores['bias_check'] = bias_score
            
            # Calculate overall score
            overall_score = float(np.mean(list(stage_scores.values())))
            
            # Determine if validation passed
            critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
            high_issues = [i for i in issues if i.severity == ValidationSeverity.HIGH]
            is_valid = len(critical_issues) == 0 and len(high_issues) <= 2
            
            # Generate recommendations
            recommendations = self._generate_recommendations(issues, personas)
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(personas, issues)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return ValidationResult(
                overall_score=overall_score,
                stage_scores=stage_scores,
                issues=issues,
                passed_checks=passed_checks,
                recommendations=recommendations,
                validation_metadata={
                    'processing_time': processing_time,
                    'personas_validated': len(personas),
                    'validation_stages': len(stage_scores),
                    'total_checks_performed': len(passed_checks) + len(issues)
                },
                is_valid=is_valid,
                quality_metrics=quality_metrics
            )
            
        except Exception as e:
            logger.error(f"Persona validation failed: {e}")
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return ValidationResult(
                overall_score=0.0,
                stage_scores={},
                issues=[
                    ValidationIssue(
                        stage=ValidationStage.STRUCTURAL,
                        severity=ValidationSeverity.CRITICAL,
                        issue_type="validation_error",
                        description=f"Validation process failed: {str(e)}",
                        confidence=1.0
                    )
                ],
                passed_checks=[],
                recommendations=["Fix validation errors and retry"],
                validation_metadata={'error': str(e), 'processing_time': processing_time},
                is_valid=False,
                quality_metrics={}
            )
    
    async def _validate_structural(self, personas: List[Dict[str, Any]]) -> Tuple[List[ValidationIssue], float]:
        """Stage 1: Structural validation using JSON schema"""
        issues = []
        valid_personas = 0
        
        for i, persona in enumerate(personas):
            try:
                # Validate against schema
                validate(instance=persona, schema=self.persona_schema)
                valid_personas += 1
                
                # Additional structural checks
                if 'confidence_scores' in persona:
                    scores = persona['confidence_scores']
                    if isinstance(scores, dict):
                        for score_type, score_value in scores.items():
                            if not isinstance(score_value, (int, float)) or not (0 <= score_value <= 1):
                                issues.append(ValidationIssue(
                                    stage=ValidationStage.STRUCTURAL,
                                    severity=ValidationSeverity.HIGH,
                                    issue_type="invalid_confidence_score",
                                    description=f"Persona {i}: Invalid confidence score for {score_type}: {score_value}",
                                    affected_attribute=f"confidence_scores.{score_type}",
                                    suggested_fix="Ensure confidence scores are between 0 and 1",
                                    confidence=1.0
                                ))
                
                # Check for empty or minimal content
                if self._is_persona_minimal(persona):
                    issues.append(ValidationIssue(
                        stage=ValidationStage.STRUCTURAL,
                        severity=ValidationSeverity.MEDIUM,
                        issue_type="minimal_content",
                        description=f"Persona {i}: Contains minimal content",
                        suggested_fix="Add more detailed attributes and descriptions",
                        confidence=0.8
                    ))
                
            except JsonSchemaValidationError as e:
                issues.append(ValidationIssue(
                    stage=ValidationStage.STRUCTURAL,
                    severity=ValidationSeverity.CRITICAL,
                    issue_type="schema_validation_error",
                    description=f"Persona {i}: Schema validation failed: {e.message}",
                    affected_attribute=e.absolute_path[-1] if e.absolute_path else None,
                    suggested_fix="Fix schema validation errors",
                    confidence=1.0,
                    evidence=[str(e.instance)]
                ))
            except Exception as e:
                issues.append(ValidationIssue(
                    stage=ValidationStage.STRUCTURAL,
                    severity=ValidationSeverity.CRITICAL,
                    issue_type="validation_error",
                    description=f"Persona {i}: Validation error: {str(e)}",
                    confidence=1.0
                ))
        
        structural_score = valid_personas / len(personas) if personas else 0.0
        return issues, structural_score
    
    async def _validate_domain_expert(self, personas: List[Dict[str, Any]]) -> Tuple[List[ValidationIssue], float]:
        """Stage 2: Domain expert validation using business rules"""
        issues = []
        total_checks = 0
        passed_checks = 0
        
        for i, persona in enumerate(personas):
            # Check demographic consistency
            demo_issues, demo_passed = self._validate_demographic_consistency(persona, i)
            issues.extend(demo_issues)
            total_checks += len(demo_issues) + demo_passed
            passed_checks += demo_passed
            
            # Check psychographic coherence
            psycho_issues, psycho_passed = self._validate_psychographic_coherence(persona, i)
            issues.extend(psycho_issues)
            total_checks += len(psycho_issues) + psycho_passed
            passed_checks += psycho_passed
            
            # Check behavioral logic
            behavior_issues, behavior_passed = self._validate_behavioral_logic(persona, i)
            issues.extend(behavior_issues)
            total_checks += len(behavior_issues) + behavior_passed
            passed_checks += behavior_passed
            
            # Check completeness
            completeness_issues, completeness_passed = self._validate_completeness(persona, i)
            issues.extend(completeness_issues)
            total_checks += len(completeness_issues) + completeness_passed
            passed_checks += completeness_passed
        
        domain_score = passed_checks / total_checks if total_checks > 0 else 0.0
        return issues, domain_score
    
    async def _validate_adversarial(self, personas: List[Dict[str, Any]]) -> Tuple[List[ValidationIssue], float]:
        """Stage 3: Adversarial questioning using LLM"""
        if not self.llm_service:
            return [], 1.0
        
        issues = []
        total_personas = len(personas)
        valid_personas = 0
        
        for i, persona in enumerate(personas):
            try:
                # Generate adversarial questions
                adversarial_prompt = self._create_adversarial_prompt(persona)
                
                # Get LLM response
                response = await self.llm_service.validate_persona(persona)
                
                if isinstance(response, dict):
                    # Parse validation response
                    consistency_score = response.get('consistency_score', 0.5)
                    realism_score = response.get('realism_score', 0.5)
                    bias_indicators = response.get('bias_indicators', [])
                    logical_conflicts = response.get('logical_conflicts', [])
                    strengths = response.get('strengths', [])
                    improvement_suggestions = response.get('improvement_suggestions', [])
                    
                    # Check scores with more nuanced thresholds
                    if consistency_score < 0.7:
                        severity = ValidationSeverity.HIGH if consistency_score < 0.5 else ValidationSeverity.MEDIUM
                        issues.append(ValidationIssue(
                            stage=ValidationStage.ADVERSARIAL,
                            severity=severity,
                            issue_type="low_consistency",
                            description=f"Persona {i}: Consistency concerns ({consistency_score:.2f})",
                            confidence=1.0 - consistency_score,
                            evidence=["LLM adversarial consistency analysis"],
                            suggested_fix="Review demographic and psychographic alignment"
                        ))
                    
                    if realism_score < 0.7:
                        severity = ValidationSeverity.HIGH if realism_score < 0.5 else ValidationSeverity.MEDIUM
                        issues.append(ValidationIssue(
                            stage=ValidationStage.ADVERSARIAL,
                            severity=severity,
                            issue_type="low_realism",
                            description=f"Persona {i}: Realism concerns ({realism_score:.2f})",
                            confidence=1.0 - realism_score,
                            evidence=["LLM adversarial realism analysis"],
                            suggested_fix="Ensure all attributes are realistic and achievable"
                        ))
                    
                    # Check bias indicators with detailed analysis
                    for bias in bias_indicators:
                        issues.append(ValidationIssue(
                            stage=ValidationStage.ADVERSARIAL,
                            severity=ValidationSeverity.HIGH,
                            issue_type="bias_detected",
                            description=f"Persona {i}: Bias detected: {bias}",
                            confidence=0.8,
                            evidence=[bias, "LLM adversarial bias detection"],
                            suggested_fix="Remove stereotypical assumptions and generalizations"
                        ))
                    
                    # Check logical conflicts with high priority
                    for conflict in logical_conflicts:
                        issues.append(ValidationIssue(
                            stage=ValidationStage.ADVERSARIAL,
                            severity=ValidationSeverity.CRITICAL,
                            issue_type="logical_conflict",
                            description=f"Persona {i}: Logical conflict: {conflict}",
                            confidence=0.9,
                            evidence=[conflict, "LLM adversarial logic analysis"],
                            suggested_fix="Resolve contradictory attributes"
                        ))
                    
                    # Add improvement suggestions as low-priority issues
                    for suggestion in improvement_suggestions:
                        issues.append(ValidationIssue(
                            stage=ValidationStage.ADVERSARIAL,
                            severity=ValidationSeverity.INFO,
                            issue_type="improvement_opportunity",
                            description=f"Persona {i}: Enhancement opportunity: {suggestion}",
                            confidence=0.6,
                            evidence=["LLM adversarial improvement analysis"],
                            suggested_fix=suggestion
                        ))
                    
                    # More stringent validation criteria
                    if (consistency_score >= 0.7 and realism_score >= 0.7 and 
                        len(bias_indicators) == 0 and len(logical_conflicts) == 0):
                        valid_personas += 1
                
            except Exception as e:
                logger.warning(f"Adversarial validation failed for persona {i}: {e}")
                issues.append(ValidationIssue(
                    stage=ValidationStage.ADVERSARIAL,
                    severity=ValidationSeverity.LOW,
                    issue_type="adversarial_validation_error",
                    description=f"Persona {i}: Adversarial validation failed: {str(e)}",
                    confidence=0.5
                ))
        
        adversarial_score = valid_personas / total_personas if total_personas > 0 else 0.0
        return issues, adversarial_score
    
    async def _validate_consistency(self, personas: List[Dict[str, Any]]) -> Tuple[List[ValidationIssue], float]:
        """Stage 4: Consistency validation using predefined checks"""
        issues = []
        total_checks = 0
        passed_checks = 0
        
        for i, persona in enumerate(personas):
            for check in self.consistency_checks:
                try:
                    check_result = check['check_function'](persona)
                    total_checks += 1
                    
                    if check_result['passed']:
                        passed_checks += 1
                    else:
                        issues.append(ValidationIssue(
                            stage=ValidationStage.CONSISTENCY,
                            severity=ValidationSeverity.MEDIUM,
                            issue_type=check['name'],
                            description=f"Persona {i}: {check_result['message']}",
                            suggested_fix=check_result.get('suggestion', ''),
                            confidence=check_result.get('confidence', 0.7),
                            evidence=check_result.get('evidence', [])
                        ))
                        
                except Exception as e:
                    logger.warning(f"Consistency check {check['name']} failed for persona {i}: {e}")
        
        consistency_score = passed_checks / total_checks if total_checks > 0 else 0.0
        return issues, consistency_score
    
    async def _validate_bias_detection(self, personas: List[Dict[str, Any]]) -> Tuple[List[ValidationIssue], float]:
        """Stage 5: Bias detection validation"""
        issues = []
        total_personas = len(personas)
        unbiased_personas = 0
        
        for i, persona in enumerate(personas):
            persona_biases = self._detect_persona_biases(persona)
            
            if not persona_biases:
                unbiased_personas += 1
            else:
                for bias in persona_biases:
                    issues.append(ValidationIssue(
                        stage=ValidationStage.BIAS_CHECK,
                        severity=ValidationSeverity.MEDIUM,
                        issue_type="bias_detected",
                        description=f"Persona {i}: {bias['description']}",
                        affected_attribute=bias.get('attribute'),
                        suggested_fix=bias.get('suggestion', 'Review and adjust to reduce bias'),
                        confidence=bias.get('confidence', 0.7),
                        evidence=bias.get('evidence', [])
                    ))
        
        bias_score = unbiased_personas / total_personas if total_personas > 0 else 0.0
        return issues, bias_score
    
    def _validate_demographic_consistency(self, persona: Dict[str, Any], persona_index: int) -> Tuple[List[ValidationIssue], int]:
        """Validate demographic consistency"""
        issues = []
        passed = 0
        
        demographics = persona.get('demographics', {})
        
        # Age-occupation consistency
        age_range = demographics.get('age_range', '')
        occupation = demographics.get('occupation', '').lower()
        
        if age_range and occupation:
            age_num = self._extract_age_number(age_range)
            if age_num:
                for occ_pattern, age_limits in self.validation_rules['demographic_consistency']['age_occupation'].items():
                    if occ_pattern in occupation:
                        if not (age_limits['min_age'] <= age_num <= age_limits['max_age']):
                            issues.append(ValidationIssue(
                                stage=ValidationStage.DOMAIN_EXPERT,
                                severity=ValidationSeverity.HIGH,
                                issue_type="age_occupation_inconsistency",
                                description=f"Age {age_num} inconsistent with occupation '{occupation}'",
                                affected_attribute="demographics.age_range",
                                suggested_fix=f"Adjust age to {age_limits['min_age']}-{age_limits['max_age']} range",
                                confidence=0.8
                            ))
                        else:
                            passed += 1
        
        return issues, passed
    
    def _validate_psychographic_coherence(self, persona: Dict[str, Any], persona_index: int) -> Tuple[List[ValidationIssue], int]:
        """Validate psychographic coherence"""
        issues = []
        passed = 0
        
        psychographics = persona.get('psychographics', {})
        values = psychographics.get('values', [])
        interests = psychographics.get('interests', [])
        
        # Check for conflicting values
        for conflicting_pair in self.validation_rules['psychographic_coherence']['conflicting_values']:
            values_set = set([v.lower() for v in values])
            if any(v in values_set for v in conflicting_pair[0]) and any(v in values_set for v in conflicting_pair[1]):
                issues.append(ValidationIssue(
                    stage=ValidationStage.DOMAIN_EXPERT,
                    severity=ValidationSeverity.MEDIUM,
                    issue_type="conflicting_values",
                    description=f"Conflicting values detected: {conflicting_pair[0]} vs {conflicting_pair[1]}",
                    affected_attribute="psychographics.values",
                    suggested_fix="Remove or reconcile conflicting values",
                    confidence=0.7
                ))
            else:
                passed += 1
        
        return issues, passed
    
    def _validate_behavioral_logic(self, persona: Dict[str, Any], persona_index: int) -> Tuple[List[ValidationIssue], int]:
        """Validate behavioral logic"""
        issues = []
        passed = 0
        
        behaviors = persona.get('behaviors', {})
        shopping_habits = behaviors.get('shopping_habits', [])
        
        # Check shopping behavior consistency
        shopping_text = ' '.join(shopping_habits).lower()
        
        behavior_indicators = self.validation_rules['behavioral_logic']['shopping_decision_consistency']
        detected_behaviors = []
        
        for behavior_type, keywords in behavior_indicators.items():
            if any(keyword in shopping_text for keyword in keywords):
                detected_behaviors.append(behavior_type)
        
        # Check for conflicting shopping behaviors
        if 'price_sensitive' in detected_behaviors and 'quality_focused' in detected_behaviors:
            issues.append(ValidationIssue(
                stage=ValidationStage.DOMAIN_EXPERT,
                severity=ValidationSeverity.MEDIUM,
                issue_type="conflicting_shopping_behavior",
                description="Both price-sensitive and quality-focused behaviors detected",
                affected_attribute="behaviors.shopping_habits",
                suggested_fix="Clarify primary shopping motivation",
                confidence=0.6
            ))
        else:
            passed += 1
        
        return issues, passed
    
    def _validate_completeness(self, persona: Dict[str, Any], persona_index: int) -> Tuple[List[ValidationIssue], int]:
        """Validate persona completeness"""
        issues = []
        passed = 0
        
        requirements = self.validation_rules['completeness_requirements']
        
        # Check minimum attributes
        for section, min_count in requirements['minimum_attributes'].items():
            section_data = persona.get(section, {})
            if isinstance(section_data, dict):
                non_empty_attrs = sum(1 for v in section_data.values() if v and v != 'unknown')
                if non_empty_attrs < min_count:
                    issues.append(ValidationIssue(
                        stage=ValidationStage.DOMAIN_EXPERT,
                        severity=ValidationSeverity.MEDIUM,
                        issue_type="insufficient_attributes",
                        description=f"Section '{section}' has only {non_empty_attrs} attributes, minimum {min_count} required",
                        affected_attribute=section,
                        suggested_fix=f"Add more {section} attributes",
                        confidence=0.9
                    ))
                else:
                    passed += 1
        
        # Check required fields
        for field in requirements['required_fields']:
            if '.' in field:
                section, attr = field.split('.', 1)
                value = persona.get(section, {}).get(attr)
            else:
                value = persona.get(field)
            
            if not value or value == 'unknown':
                issues.append(ValidationIssue(
                    stage=ValidationStage.DOMAIN_EXPERT,
                    severity=ValidationSeverity.HIGH,
                    issue_type="missing_required_field",
                    description=f"Required field '{field}' is missing or unknown",
                    affected_attribute=field,
                    suggested_fix=f"Provide value for {field}",
                    confidence=1.0
                ))
            else:
                passed += 1
        
        return issues, passed
    
    def _detect_persona_biases(self, persona: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect potential biases in persona"""
        biases = []
        
        demographics = persona.get('demographics', {})
        psychographics = persona.get('psychographics', {})
        behaviors = persona.get('behaviors', {})
        
        # Gender-occupation bias
        gender = demographics.get('gender', '').lower()
        occupation = demographics.get('occupation', '').lower()
        
        if gender and occupation:
            bias_patterns = self.bias_detection_patterns['gender_occupation_bias']
            
            if gender == 'male' and any(occ in occupation for occ in bias_patterns['female_dominated']):
                biases.append({
                    'description': f"Male in traditionally female-dominated occupation: {occupation}",
                    'attribute': 'demographics.occupation',
                    'confidence': 0.6,
                    'evidence': [f"Gender: {gender}, Occupation: {occupation}"]
                })
            elif gender == 'female' and any(occ in occupation for occ in bias_patterns['male_dominated']):
                biases.append({
                    'description': f"Female in traditionally male-dominated occupation: {occupation}",
                    'attribute': 'demographics.occupation',
                    'confidence': 0.6,
                    'evidence': [f"Gender: {gender}, Occupation: {occupation}"]
                })
        
        # Age-technology bias
        age_range = demographics.get('age_range', '')
        interests = psychographics.get('interests', [])
        tech_usage = behaviors.get('technology_usage', [])
        
        age_num = self._extract_age_number(age_range)
        if age_num:
            tech_indicators = self.bias_detection_patterns['age_technology_bias']
            
            # Check young tech assumption
            if age_num < tech_indicators['young_tech_assumption']['age_threshold']:
                tech_keywords = tech_indicators['young_tech_assumption']['tech_indicators']
                if not any(keyword in ' '.join(interests + tech_usage).lower() for keyword in tech_keywords):
                    biases.append({
                        'description': f"Young person ({age_num}) without expected technology interests",
                        'attribute': 'psychographics.interests',
                        'confidence': 0.5,
                        'evidence': [f"Age: {age_num}, Limited tech interests"]
                    })
        
        return biases
    
    def _create_adversarial_prompt(self, persona: Dict[str, Any]) -> str:
        """Create sophisticated adversarial questioning prompt for LLM validation"""
        demographics = persona.get('demographics', {})
        psychographics = persona.get('psychographics', {})
        behaviors = persona.get('behaviors', {})
        
        return f"""
        You are an expert persona validation specialist. Conduct a thorough adversarial analysis of this persona:
        
        {json.dumps(persona, indent=2)}
        
        CRITICAL ANALYSIS FRAMEWORK:
        
        1. DEMOGRAPHIC CONSISTENCY:
        - Does age align with education level and career stage?
        - Is income realistic for occupation and location?
        - Are family status and lifestyle choices coherent?
        
        2. PSYCHOGRAPHIC COHERENCE:
        - Do values, attitudes, and motivations form a logical pattern?
        - Are personality traits mutually compatible?
        - Do interests align with stated values and lifestyle?
        
        3. BEHAVIORAL LOGIC:
        - Are purchasing behaviors consistent with income and values?
        - Do media consumption patterns match demographics and interests?
        - Are social behaviors aligned with personality and lifestyle?
        
        4. BIAS DETECTION:
        - Identify any cultural, gender, age, or socioeconomic stereotypes
        - Flag unrealistic generalizations or oversimplifications
        - Check for implicit assumptions about groups or demographics
        
        5. REALISM ASSESSMENT:
        - Could this person exist in the real world?
        - Are all attributes achievable within stated constraints?
        - Are there any fantastical or impossible combinations?
        
        6. ACTIONABILITY:
        - Is there enough detail for marketing/design decisions?
        - Are the insights specific and measurable?
        - Can this persona guide concrete business actions?
        
        RESPONSE FORMAT:
        Return a JSON object with:
        {{
            "consistency_score": 0.0-1.0,
            "realism_score": 0.0-1.0,
            "bias_indicators": ["list of specific bias issues"],
            "logical_conflicts": ["list of contradictions"],
            "strengths": ["list of well-constructed elements"],
            "improvement_suggestions": ["specific recommendations"]
        }}
        
        Be thorough, critical, and specific in your analysis.
        """
    
    def _check_age_education_consistency(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """Check age-education consistency"""
        demographics = persona.get('demographics', {})
        age_range = demographics.get('age_range', '')
        education = demographics.get('education', '')
        
        age_num = self._extract_age_number(age_range)
        
        if not age_num or not education:
            return {'passed': True, 'message': 'Insufficient data for age-education check'}
        
        education_rules = self.validation_rules['demographic_consistency']['age_education']
        
        if education in education_rules:
            min_age = education_rules[education]['min_age']
            max_age = education_rules[education]['max_age']
            
            if not (min_age <= age_num <= max_age):
                return {
                    'passed': False,
                    'message': f"Age {age_num} inconsistent with education level '{education}'",
                    'suggestion': f"Adjust age to {min_age}-{max_age} range or change education level",
                    'confidence': 0.8,
                    'evidence': [f"Age: {age_num}, Education: {education}"]
                }
        
        return {'passed': True, 'message': 'Age-education consistency check passed'}
    
    def _check_income_occupation_consistency(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """Check income-occupation consistency"""
        demographics = persona.get('demographics', {})
        occupation = demographics.get('occupation', '').lower()
        income_level = demographics.get('income_level', '')
        
        if not occupation or not income_level:
            return {'passed': True, 'message': 'Insufficient data for income-occupation check'}
        
        income_rules = self.validation_rules['demographic_consistency']['income_occupation']
        
        for occ_pattern, income_constraints in income_rules.items():
            if occ_pattern in occupation:
                if 'min_income' in income_constraints:
                    min_income = income_constraints['min_income']
                    if not self._income_meets_minimum(income_level, min_income):
                        return {
                            'passed': False,
                            'message': f"Income level '{income_level}' too low for occupation '{occupation}'",
                            'suggestion': f"Increase income level to at least '{min_income}'",
                            'confidence': 0.7,
                            'evidence': [f"Occupation: {occupation}, Income: {income_level}"]
                        }
                
                if 'max_income' in income_constraints:
                    max_income = income_constraints['max_income']
                    if not self._income_meets_maximum(income_level, max_income):
                        return {
                            'passed': False,
                            'message': f"Income level '{income_level}' too high for occupation '{occupation}'",
                            'suggestion': f"Decrease income level to at most '{max_income}'",
                            'confidence': 0.7,
                            'evidence': [f"Occupation: {occupation}, Income: {income_level}"]
                        }
        
        return {'passed': True, 'message': 'Income-occupation consistency check passed'}
    
    def _check_values_behavior_alignment(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """Check values-behavior alignment"""
        psychographics = persona.get('psychographics', {})
        behaviors = persona.get('behaviors', {})
        
        values = psychographics.get('values', [])
        shopping_habits = behaviors.get('shopping_habits', [])
        
        if not values or not shopping_habits:
            return {'passed': True, 'message': 'Insufficient data for values-behavior alignment check'}
        
        # Simple alignment check
        values_text = ' '.join(values).lower()
        shopping_text = ' '.join(shopping_habits).lower()
        
        # Check for obvious misalignments
        if 'environmentally_conscious' in values_text and 'luxury' in shopping_text:
            return {
                'passed': False,
                'message': 'Environmental values conflict with luxury shopping behavior',
                'suggestion': 'Align shopping habits with environmental values or adjust values',
                'confidence': 0.6,
                'evidence': [f"Values: {values}", f"Shopping: {shopping_habits}"]
            }
        
        return {'passed': True, 'message': 'Values-behavior alignment check passed'}
    
    def _check_interest_lifestyle_coherence(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """Check interest-lifestyle coherence"""
        psychographics = persona.get('psychographics', {})
        interests = psychographics.get('interests', [])
        lifestyle = psychographics.get('lifestyle', [])
        
        if not interests or not lifestyle:
            return {'passed': True, 'message': 'Insufficient data for interest-lifestyle coherence check'}
        
        # Simple coherence check
        interests_text = ' '.join(interests).lower()
        lifestyle_text = ' '.join(lifestyle).lower()
        
        # Check for coherence
        if 'fitness' in interests_text and 'sedentary' in lifestyle_text:
            return {
                'passed': False,
                'message': 'Fitness interests conflict with sedentary lifestyle',
                'suggestion': 'Align lifestyle with fitness interests or adjust interests',
                'confidence': 0.7,
                'evidence': [f"Interests: {interests}", f"Lifestyle: {lifestyle}"]
            }
        
        return {'passed': True, 'message': 'Interest-lifestyle coherence check passed'}
    
    def _check_demographic_psychographic_harmony(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """Check demographic-psychographic harmony"""
        demographics = persona.get('demographics', {})
        psychographics = persona.get('psychographics', {})
        
        age_range = demographics.get('age_range', '')
        interests = psychographics.get('interests', [])
        
        age_num = self._extract_age_number(age_range)
        
        if not age_num or not interests:
            return {'passed': True, 'message': 'Insufficient data for demographic-psychographic harmony check'}
        
        interests_text = ' '.join(interests).lower()
        
        # Simple harmony check
        if age_num > 65 and 'gaming' in interests_text and 'social media' in interests_text:
            return {
                'passed': False,
                'message': 'Senior age with heavy gaming and social media interests may be unrealistic',
                'suggestion': 'Consider age-appropriate interests or adjust age',
                'confidence': 0.5,
                'evidence': [f"Age: {age_num}", f"Interests: {interests}"]
            }
        
        return {'passed': True, 'message': 'Demographic-psychographic harmony check passed'}
    
    def _extract_age_number(self, age_range: str) -> Optional[int]:
        """Extract numeric age from age range string"""
        if not age_range:
            return None
        
        # Try to extract number
        numbers = re.findall(r'\d+', age_range)
        if numbers:
            return int(numbers[0])
        
        # Handle age range words
        age_mappings = {
            'teens': 17,
            'twenties': 25,
            'thirties': 35,
            'forties': 45,
            'fifties': 55,
            'sixties': 65,
            'seventies': 75
        }
        
        for age_word, age_num in age_mappings.items():
            if age_word in age_range.lower():
                return age_num
        
        return None
    
    def _income_meets_minimum(self, income_level: str, min_income: str) -> bool:
        """Check if income meets minimum requirement"""
        income_order = ['low', 'medium', 'upper-middle', 'high']
        try:
            current_idx = income_order.index(income_level)
            min_idx = income_order.index(min_income)
            return current_idx >= min_idx
        except ValueError:
            return True  # Unknown income levels pass
    
    def _income_meets_maximum(self, income_level: str, max_income: str) -> bool:
        """Check if income meets maximum requirement"""
        income_order = ['low', 'medium', 'upper-middle', 'high']
        try:
            current_idx = income_order.index(income_level)
            max_idx = income_order.index(max_income)
            return current_idx <= max_idx
        except ValueError:
            return True  # Unknown income levels pass
    
    def _is_persona_minimal(self, persona: Dict[str, Any]) -> bool:
        """Check if persona has minimal content"""
        demographics = persona.get('demographics', {})
        psychographics = persona.get('psychographics', {})
        behaviors = persona.get('behaviors', {})
        
        # Count non-empty attributes
        demo_count = sum(1 for v in demographics.values() if v and v != 'unknown')
        psycho_count = sum(len(v) if isinstance(v, list) else (1 if v else 0) for v in psychographics.values())
        behavior_count = sum(len(v) if isinstance(v, list) else (1 if v else 0) for v in behaviors.values())
        
        total_attributes = demo_count + psycho_count + behavior_count
        return total_attributes < 10
    
    def _generate_recommendations(self, issues: List[ValidationIssue], personas: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on validation issues"""
        recommendations = []
        
        # Group issues by type
        issue_types = defaultdict(int)
        for issue in issues:
            issue_types[issue.issue_type] += 1
        
        # Generate specific recommendations
        if issue_types.get('schema_validation_error', 0) > 0:
            recommendations.append("Fix schema validation errors to ensure proper persona structure")
        
        if issue_types.get('age_occupation_inconsistency', 0) > 0:
            recommendations.append("Review age-occupation combinations for realistic consistency")
        
        if issue_types.get('conflicting_values', 0) > 0:
            recommendations.append("Resolve conflicting values in psychographic profiles")
        
        if issue_types.get('bias_detected', 0) > 0:
            recommendations.append("Address potential biases in demographic and psychographic attributes")
        
        if issue_types.get('minimal_content', 0) > 0:
            recommendations.append("Enhance personas with more detailed attributes and descriptions")
        
        # General recommendations
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        if critical_issues:
            recommendations.append("Address critical validation issues before using personas")
        
        high_issues = [i for i in issues if i.severity == ValidationSeverity.HIGH]
        if len(high_issues) > 3:
            recommendations.append("Consider regenerating personas to reduce validation issues")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _calculate_quality_metrics(self, personas: List[Dict[str, Any]], issues: List[ValidationIssue]) -> Dict[str, float]:
        """Calculate quality metrics for personas"""
        if not personas:
            return {}
        
        # Calculate issue density
        total_issues = len(issues)
        critical_issues = len([i for i in issues if i.severity == ValidationSeverity.CRITICAL])
        high_issues = len([i for i in issues if i.severity == ValidationSeverity.HIGH])
        
        # Calculate completeness
        total_attributes = 0
        filled_attributes = 0
        
        for persona in personas:
            for section in ['demographics', 'psychographics', 'behaviors']:
                section_data = persona.get(section, {})
                if isinstance(section_data, dict):
                    for value in section_data.values():
                        total_attributes += 1
                        if value and value != 'unknown':
                            filled_attributes += 1
        
        completeness = filled_attributes / total_attributes if total_attributes > 0 else 0.0
        
        # Calculate diversity (simplified)
        diversity_score = min(1.0, len(personas) / 5.0)  # Assume 5+ personas is good diversity
        
        return {
            'completeness': completeness,
            'issue_density': total_issues / len(personas),
            'critical_issue_ratio': critical_issues / len(personas),
            'high_issue_ratio': high_issues / len(personas),
            'diversity_score': diversity_score,
            'overall_quality': (completeness + (1 - min(1.0, total_issues / (len(personas) * 5)))) / 2
        }