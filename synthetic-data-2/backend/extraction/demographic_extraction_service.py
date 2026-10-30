"""Sophisticated demographic extraction using ML models and advanced NER"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
import re
import json
from collections import Counter, defaultdict
import pickle
import os

# Core ML and NLP libraries
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.naive_bayes import MultinomialNB

# Advanced NLP
import spacy
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Span
import nltk
from textblob import TextBlob

# Statistical libraries
from scipy import stats
from scipy.spatial.distance import cosine

# Validation
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class DemographicPrediction(BaseModel):
    """Single demographic prediction result"""
    attribute: str
    value: Any
    confidence: float
    method: str
    evidence: List[str]
    alternatives: List[Dict[str, Any]]

class DemographicExtractionResult(BaseModel):
    """Complete demographic extraction result"""
    predictions: List[DemographicPrediction]
    aggregate_confidence: float
    extraction_metadata: Dict[str, Any]
    model_performance: Dict[str, Any]
    bias_indicators: List[str]
    uncertainty_analysis: Dict[str, Any]

class DemographicExtractionService:
    """Advanced demographic extraction using ML and NER models"""
    
    def __init__(self, spacy_model: str = "en_core_web_lg", model_cache_dir: str = "./models"):
        """
        Initialize demographic extraction service
        
        Args:
            spacy_model: spaCy model to use
            model_cache_dir: Directory to cache trained models
        """
        self.spacy_model_name = spacy_model
        self.model_cache_dir = model_cache_dir
        self.nlp = None
        self.matcher = None
        self.phrase_matcher = None
        
        # ML models for demographic prediction
        self.age_model = None
        self.gender_model = None
        self.occupation_model = None
        self.education_model = None
        self.income_model = None
        self.location_model = None
        
        # Feature extractors
        self.age_vectorizer = None
        self.gender_vectorizer = None
        self.occupation_vectorizer = None
        
        # Demographic patterns and rules
        self.demographic_rules = self._load_demographic_rules()
        self.demographic_lexicons = self._load_demographic_lexicons()
        
        # Initialize models
        self._initialize_models()
        self._setup_matchers()
        
        # Load or train ML models
        self._load_or_train_models()
    
    def _initialize_models(self):
        """Initialize NLP models"""
        try:
            self.nlp = spacy.load(self.spacy_model_name)
            logger.info(f"Loaded spaCy model: {self.spacy_model_name}")
        except OSError:
            logger.warning(f"spaCy model {self.spacy_model_name} not found, falling back to en_core_web_sm")
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.error("No spaCy model available")
                raise
        
        # Ensure model cache directory exists
        os.makedirs(self.model_cache_dir, exist_ok=True)
    
    def _setup_matchers(self):
        """Setup spaCy matchers for demographic patterns"""
        self.matcher = Matcher(self.nlp.vocab)
        self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        
        # Age patterns
        age_patterns = [
            [{"LIKE_NUM": True}, {"LOWER": {"IN": ["years", "year", "yrs", "yr"]}}, {"LOWER": "old"}],
            [{"LOWER": "aged"}, {"LIKE_NUM": True}],
            [{"LOWER": {"IN": ["i'm", "i", "am"]}}, {"LIKE_NUM": True}],
            [{"LOWER": "age"}, {"LIKE_NUM": True}]
        ]
        
        for i, pattern in enumerate(age_patterns):
            self.matcher.add(f"AGE_PATTERN_{i}", [pattern])
        
        # Gender patterns
        gender_patterns = [
            [{"LOWER": {"IN": ["i'm", "i", "am"]}}, {"LOWER": {"IN": ["male", "female", "man", "woman", "guy", "girl"]}}],
            [{"LOWER": "as"}, {"LOWER": "a"}, {"LOWER": {"IN": ["male", "female", "man", "woman", "guy", "girl"]}}]
        ]
        
        for i, pattern in enumerate(gender_patterns):
            self.matcher.add(f"GENDER_PATTERN_{i}", [pattern])
        
        # Occupation phrase matcher
        occupation_phrases = [
            "software engineer", "data scientist", "product manager", "marketing manager",
            "sales representative", "customer service", "human resources", "financial analyst",
            "graphic designer", "web developer", "project manager", "business analyst",
            "registered nurse", "medical doctor", "teacher", "professor", "student",
            "consultant", "entrepreneur", "freelancer", "retired", "unemployed"
        ]
        
        occupation_docs = [self.nlp(phrase) for phrase in occupation_phrases]
        self.phrase_matcher.add("OCCUPATIONS", occupation_docs)
    
    def _load_demographic_rules(self) -> Dict[str, Any]:
        """Load sophisticated demographic extraction rules"""
        return {
            'age_indicators': {
                'direct_age': [
                    r'\b(?:i am|i\'m|age|aged?)\s+(\d{1,2})\b',
                    r'\b(\d{1,2})\s*(?:years?|yrs?)\s*old\b',
                    r'\bborn in (19|20)\d{2}\b'
                ],
                'age_ranges': {
                    'teen': (13, 19),
                    'teenager': (13, 19),
                    'young adult': (18, 25),
                    'twenties': (20, 29),
                    'thirties': (30, 39),
                    'forties': (40, 49),
                    'fifties': (50, 59),
                    'sixties': (60, 69),
                    'seventies': (70, 79),
                    'elderly': (65, 100),
                    'senior': (65, 100),
                    'middle aged': (35, 55)
                },
                'contextual_clues': [
                    r'\b(?:in|during)\s+(?:high school|college|university)\b',
                    r'\b(?:retired|retirement)\b',
                    r'\b(?:kids?|children)\s+(?:in|at)\s+(?:school|college)\b',
                    r'\b(?:grandchildren|grandkids)\b'
                ]
            },
            'gender_indicators': {
                'direct_gender': [
                    r'\b(?:i am|i\'m)\s+(?:a\s+)?(male|female|man|woman|guy|girl|boy|lady|gentleman)\b',
                    r'\b(?:as a|being a)\s+(male|female|man|woman|guy|girl|boy|lady|gentleman)\b'
                ],
                'pronouns': {
                    'he/him': 'male',
                    'she/her': 'female',
                    'they/them': 'non-binary'
                },
                'relationship_indicators': {
                    'husband': 'male',
                    'wife': 'female',
                    'boyfriend': 'male',
                    'girlfriend': 'female',
                    'father': 'male',
                    'mother': 'female',
                    'dad': 'male',
                    'mom': 'female'
                }
            },
            'occupation_indicators': {
                'direct_occupation': [
                    r'\b(?:i work as|working as|i am a|job as|employed as|my job is)\s+(?:a\s+|an\s+)?([a-z\s]+)\b',
                    r'\b(?:my career|my profession)\s+(?:is|as)\s+(?:a\s+|an\s+)?([a-z\s]+)\b'
                ],
                'industry_indicators': {
                    'technology': ['software', 'programming', 'coding', 'tech', 'IT', 'computer'],
                    'healthcare': ['medical', 'hospital', 'patient', 'healthcare', 'medicine'],
                    'education': ['teaching', 'school', 'student', 'education', 'academic'],
                    'finance': ['banking', 'financial', 'investment', 'accounting', 'money'],
                    'retail': ['sales', 'customer', 'store', 'shopping', 'retail'],
                    'manufacturing': ['factory', 'production', 'manufacturing', 'assembly']
                }
            },
            'education_indicators': {
                'degree_patterns': [
                    r'\b(?:i have|i hold|graduated with)\s+(?:a\s+|an\s+)?(bachelor|master|phd|doctorate|degree|diploma)\b',
                    r'\b(bachelor|master|phd|doctorate)\s+(?:degree|in)\b'
                ],
                'institution_patterns': [
                    r'\b(?:graduated from|studied at|attending|alumni of)\s+([A-Z][a-z\s]+(?:university|college|school|institute))\b'
                ],
                'education_levels': {
                    'high school': 'high_school',
                    'college': 'college',
                    'university': 'university',
                    'bachelor': 'bachelors',
                    'master': 'masters',
                    'phd': 'phd',
                    'doctorate': 'phd'
                }
            },
            'income_indicators': {
                'salary_patterns': [
                    r'\b(?:earn|make|salary of|income of)\s+(?:about\s+|around\s+)?\$?([0-9,]+)\s*(?:k|thousand|per year|annually)?\b',
                    r'\b\$([0-9,]+)\s*(?:k|thousand)?\s+(?:per year|annually|salary|income)\b'
                ],
                'income_brackets': {
                    'low income': 'low',
                    'middle class': 'middle',
                    'upper class': 'high',
                    'wealthy': 'high',
                    'struggling financially': 'low',
                    'well off': 'high'
                }
            }
        }
    
    def _load_demographic_lexicons(self) -> Dict[str, Set[str]]:
        """Load demographic lexicons for feature extraction"""
        return {
            'age_related_words': {
                'young', 'old', 'teenager', 'adult', 'senior', 'elderly', 'middle-aged',
                'youth', 'mature', 'aging', 'generation', 'millennial', 'boomer', 'gen-x'
            },
            'gender_related_words': {
                'male', 'female', 'man', 'woman', 'guy', 'girl', 'boy', 'lady', 'gentleman',
                'masculine', 'feminine', 'gender', 'he', 'she', 'him', 'her', 'his', 'hers'
            },
            'occupation_related_words': {
                'work', 'job', 'career', 'profession', 'employment', 'occupation', 'business',
                'company', 'office', 'workplace', 'industry', 'field', 'position', 'role'
            },
            'education_related_words': {
                'school', 'college', 'university', 'education', 'degree', 'diploma', 'graduate',
                'student', 'academic', 'learning', 'study', 'course', 'major', 'minor'
            },
            'income_related_words': {
                'money', 'salary', 'income', 'wage', 'pay', 'earnings', 'financial', 'budget',
                'expensive', 'cheap', 'afford', 'cost', 'price', 'wealthy', 'poor', 'rich'
            }
        }
    
    def _load_or_train_models(self):
        """Load existing models or train new ones"""
        model_files = {
            'age_model': 'age_classifier.pkl',
            'gender_model': 'gender_classifier.pkl',
            'occupation_model': 'occupation_classifier.pkl',
            'education_model': 'education_classifier.pkl',
            'income_model': 'income_classifier.pkl'
        }
        
        for model_name, filename in model_files.items():
            filepath = os.path.join(self.model_cache_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'rb') as f:
                        setattr(self, model_name, pickle.load(f))
                    logger.info(f"Loaded {model_name} from cache")
                except Exception as e:
                    logger.warning(f"Failed to load {model_name}: {e}")
                    self._train_model(model_name)
            else:
                self._train_model(model_name)
    
    def _train_model(self, model_name: str):
        """Train a demographic prediction model"""
        logger.info(f"Training {model_name}...")
        
        # Generate synthetic training data for demonstration
        # In production, this would use real labeled data
        training_data = self._generate_synthetic_training_data(model_name)
        
        if not training_data:
            logger.warning(f"No training data available for {model_name}")
            return
        
        X, y = training_data
        
        if model_name == 'age_model':
            # Age regression model
            vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            X_vectorized = vectorizer.fit_transform(X)
            
            model = Pipeline([
                ('scaler', StandardScaler(with_mean=False)),
                ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
            ])
            
            model.fit(X_vectorized, y)
            self.age_model = (model, vectorizer)
            
        elif model_name == 'gender_model':
            # Gender classification model
            vectorizer = TfidfVectorizer(max_features=500, stop_words='english', ngram_range=(1, 2))
            X_vectorized = vectorizer.fit_transform(X)
            
            model = MultinomialNB(alpha=0.1)
            model.fit(X_vectorized, y)
            self.gender_model = (model, vectorizer)
            
        elif model_name == 'occupation_model':
            # Occupation classification model
            vectorizer = TfidfVectorizer(max_features=1500, stop_words='english', ngram_range=(1, 3))
            X_vectorized = vectorizer.fit_transform(X)
            
            model = GradientBoostingClassifier(n_estimators=100, random_state=42)
            model.fit(X_vectorized, y)
            self.occupation_model = (model, vectorizer)
        
        # Save trained model
        try:
            filepath = os.path.join(self.model_cache_dir, f"{model_name.replace('_model', '_classifier')}.pkl")
            with open(filepath, 'wb') as f:
                pickle.dump(getattr(self, model_name), f)
            logger.info(f"Saved {model_name} to cache")
        except Exception as e:
            logger.error(f"Failed to save {model_name}: {e}")
    
    def _generate_synthetic_training_data(self, model_name: str) -> Optional[Tuple[List[str], List[str]]]:
        """Generate synthetic training data for model training"""
        # This is a simplified example. In production, use real labeled data.
        
        if model_name == 'age_model':
            texts = [
                "I'm 25 years old and work in tech",
                "As a 45-year-old manager, I have experience",
                "Being 30, I'm looking for new opportunities",
                "At 55, I'm considering retirement",
                "I'm a 22-year-old college student"
            ]
            labels = ['20-30', '40-50', '30-40', '50-60', '20-30']
            return texts, labels
            
        elif model_name == 'gender_model':
            texts = [
                "I'm a male software engineer",
                "As a woman in tech, I face challenges",
                "He works as a manager",
                "She is a talented designer",
                "My husband and I are planning"
            ]
            labels = ['male', 'female', 'male', 'female', 'female']
            return texts, labels
            
        elif model_name == 'occupation_model':
            texts = [
                "I work as a software developer",
                "My job as a teacher is rewarding",
                "Working in healthcare as a nurse",
                "I'm a marketing manager at a startup",
                "As a data scientist, I analyze trends"
            ]
            labels = ['technology', 'education', 'healthcare', 'marketing', 'technology']
            return texts, labels
            
        elif model_name == 'education_model':
            texts = [
                "I have a bachelor's degree in computer science",
                "Graduated with a master's degree from Stanford",
                "I completed high school and started working",
                "Currently pursuing my PhD in biology",
                "I have an associate degree in nursing",
                "Dropped out of college to start my business",
                "I'm a high school graduate with some college experience"
            ]
            labels = ['bachelors', 'masters', 'high_school', 'phd', 'associate', 'some_college', 'some_college']
            return texts, labels
            
        elif model_name == 'income_model':
            texts = [
                "I earn around $45,000 per year as a teacher",
                "My salary is $120,000 annually in tech",
                "I make about $25k working part-time",
                "Earning $85,000 as a manager",
                "My income is around $200,000 as a senior executive",
                "I make minimum wage at my retail job",
                "My household income is about $65,000"
            ]
            labels = ['30k-50k', '100k-plus', 'under-30k', '75k-100k', '100k-plus', 'under-30k', '50k-75k']
            return texts, labels
        
        return None
    
    async def extract_demographics_advanced(self, text: str, nlp_features: Optional[Dict[str, Any]] = None, 
                                           entities: Optional[List[Dict[str, Any]]] = None, 
                                           focus_areas: Optional[List[str]] = None) -> DemographicExtractionResult:
        """Extract demographics using advanced ML and NER techniques"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            doc = self.nlp(text)
            predictions = []
            
            # Use provided entities if available, otherwise extract from spaCy
            available_entities = entities or []
            
            # Filter focus areas if specified
            target_attributes = focus_areas or ['age', 'gender', 'occupation', 'education', 'income', 'location']
            
            # Extract demographics based on focus areas
            if 'age' in target_attributes:
                age_prediction = await self._extract_age_advanced(text, doc, available_entities)
                if age_prediction:
                    predictions.append(age_prediction)
            
            if 'gender' in target_attributes:
                gender_prediction = await self._extract_gender_advanced(text, doc, available_entities)
                if gender_prediction:
                    predictions.append(gender_prediction)
            
            if 'occupation' in target_attributes:
                occupation_prediction = await self._extract_occupation_advanced(text, doc, available_entities)
                if occupation_prediction:
                    predictions.append(occupation_prediction)
            
            if 'education' in target_attributes:
                education_prediction = await self._extract_education_advanced(text, doc, available_entities)
                if education_prediction:
                    predictions.append(education_prediction)
            
            if 'income' in target_attributes:
                income_prediction = await self._extract_income_advanced(text, doc, available_entities)
                if income_prediction:
                    predictions.append(income_prediction)
            
            if 'location' in target_attributes:
                location_prediction = await self._extract_location_advanced(text, doc, available_entities)
                if location_prediction:
                    predictions.append(location_prediction)

            
            # Calculate aggregate confidence
            confidences = [p.confidence for p in predictions]
            aggregate_confidence = float(np.mean(confidences)) if confidences else 0.0
            
            # Detect potential biases
            bias_indicators = self._detect_bias_indicators(predictions)
            
            # Perform uncertainty analysis
            uncertainty_analysis = self._analyze_uncertainty(predictions, text)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return DemographicExtractionResult(
                predictions=predictions,
                aggregate_confidence=aggregate_confidence,
                extraction_metadata={
                    'processing_time': processing_time,
                    'text_length': len(text),
                    'methods_used': list(set(p.method for p in predictions)),
                    'total_predictions': len(predictions)
                },
                model_performance={
                    'age_model_available': self.age_model is not None,
                    'gender_model_available': self.gender_model is not None,
                    'occupation_model_available': self.occupation_model is not None
                },
                bias_indicators=bias_indicators,
                uncertainty_analysis=uncertainty_analysis
            )
            
        except Exception as e:
            logger.error(f"Advanced demographic extraction failed: {e}")
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return DemographicExtractionResult(
                predictions=[],
                aggregate_confidence=0.0,
                extraction_metadata={'error': str(e), 'processing_time': processing_time},
                model_performance={},
                bias_indicators=[],
                uncertainty_analysis={}
            )
    
    async def _extract_age_advanced(self, text: str, doc, entities: Optional[List[Dict[str, Any]]] = None) -> Optional[DemographicPrediction]:
        """Extract age using multiple advanced methods"""
        evidence = []
        methods_used = []
        age_candidates = []
        
        # Method 1: Use provided entities if available
        if entities:
            for entity in entities:
                if entity.get('label') in ['DATE', 'CARDINAL'] and 'age' in entity.get('text', '').lower():
                    # Extract age from entity context
                    entity_text = entity.get('text', '')
                    age_match = re.search(r'\b(\d{1,2})\b', entity_text)
                    if age_match:
                        age = int(age_match.group(1))
                        if 10 <= age <= 100:
                            age_candidates.append({
                                'value': age,
                                'confidence': 0.95,
                                'method': 'ner_entity_extraction',
                                'evidence': entity_text
                            })
                            evidence.append(entity_text)
                            methods_used.append('ner_entity_extraction')
        
        # Method 2: Pattern matching
        for pattern in self.demographic_rules['age_indicators']['direct_age']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    age_str = match.group(1)
                    if age_str.isdigit():
                        age = int(age_str)
                        if 10 <= age <= 100:
                            age_candidates.append({
                                'value': age,
                                'confidence': 0.9,
                                'method': 'pattern_matching',
                                'evidence': match.group(0)
                            })
                            evidence.append(match.group(0))
                            methods_used.append('pattern_matching')
        
        # Method 3: Age range detection
        text_lower = text.lower()
        for age_term, (min_age, max_age) in self.demographic_rules['age_indicators']['age_ranges'].items():
            if age_term in text_lower:
                age_candidates.append({
                    'value': f"{min_age}-{max_age}",
                    'confidence': 0.7,
                    'method': 'age_range_detection',
                    'evidence': age_term
                })
                evidence.append(age_term)
                methods_used.append('age_range_detection')
        
        # Method 3: ML model prediction
        if self.age_model:
            try:
                model, vectorizer = self.age_model
                text_vectorized = vectorizer.transform([text])
                prediction = model.predict(text_vectorized)[0]
                confidence = max(model.predict_proba(text_vectorized)[0])
                
                age_candidates.append({
                    'value': prediction,
                    'confidence': confidence,
                    'method': 'ml_model',
                    'evidence': 'ML model prediction'
                })
                methods_used.append('ml_model')
            except Exception as e:
                logger.warning(f"Age ML model prediction failed: {e}")
        
        # Method 4: Contextual clues
        for pattern in self.demographic_rules['age_indicators']['contextual_clues']:
            if re.search(pattern, text, re.IGNORECASE):
                # Infer age based on context
                if 'high school' in text.lower():
                    age_candidates.append({
                        'value': '15-18',
                        'confidence': 0.6,
                        'method': 'contextual_inference',
                        'evidence': 'high school context'
                    })
                elif 'college' in text.lower() or 'university' in text.lower():
                    age_candidates.append({
                        'value': '18-25',
                        'confidence': 0.6,
                        'method': 'contextual_inference',
                        'evidence': 'college context'
                    })
                elif 'retired' in text.lower() or 'retirement' in text.lower():
                    age_candidates.append({
                        'value': '65+',
                        'confidence': 0.7,
                        'method': 'contextual_inference',
                        'evidence': 'retirement context'
                    })
        
        if not age_candidates:
            return None
        
        # Select best prediction
        best_candidate = max(age_candidates, key=lambda x: x['confidence'])
        
        # Create alternatives list
        alternatives = [c for c in age_candidates if c != best_candidate][:3]
        
        return DemographicPrediction(
            attribute='age',
            value=best_candidate['value'],
            confidence=best_candidate['confidence'],
            method=best_candidate['method'],
            evidence=evidence,
            alternatives=alternatives
        )
    
    async def _extract_gender_advanced(self, text: str, doc, entities: Optional[List[Dict[str, Any]]] = None) -> Optional[DemographicPrediction]:
        """Extract gender using multiple advanced methods"""
        evidence = []
        methods_used = []
        gender_candidates = []
        
        # Method 1: Use provided entities for person name analysis
        if entities:
            for entity in entities:
                if entity.get('label') == 'PERSON':
                    person_name = entity.get('text', '')
                    # Simple name-based gender inference (could be enhanced with external name databases)
                    first_name = person_name.split()[0].lower() if person_name else ''
                    
                    # Basic gendered name patterns
                    male_endings = ['son', 'man', 'boy']
                    female_endings = ['daughter', 'woman', 'girl']
                    
                    if any(first_name.endswith(ending) for ending in male_endings):
                        gender_candidates.append({
                            'value': 'male',
                            'confidence': 0.75,
                            'method': 'person_entity_analysis',
                            'evidence': person_name
                        })
                        evidence.append(person_name)
                    elif any(first_name.endswith(ending) for ending in female_endings):
                        gender_candidates.append({
                            'value': 'female',
                            'confidence': 0.75,
                            'method': 'person_entity_analysis',
                            'evidence': person_name
                        })
                        evidence.append(person_name)
        
        # Method 2: Direct pattern matching
        for pattern in self.demographic_rules['gender_indicators']['direct_gender']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    gender_term = match.group(1).lower()
                    normalized_gender = self._normalize_gender_term(gender_term)
                    if normalized_gender:
                        gender_candidates.append({
                            'value': normalized_gender,
                            'confidence': 0.9,
                            'method': 'direct_pattern',
                            'evidence': match.group(0)
                        })
                        evidence.append(match.group(0))
        
        # Method 3: Pronoun analysis
        text_lower = text.lower()
        for pronoun, gender in self.demographic_rules['gender_indicators']['pronouns'].items():
            if pronoun in text_lower:
                gender_candidates.append({
                    'value': gender,
                    'confidence': 0.6,
                    'method': 'pronoun_analysis',
                    'evidence': pronoun
                })
                evidence.append(pronoun)
        
        # Method 4: Relationship indicators
        for relationship, gender in self.demographic_rules['gender_indicators']['relationship_indicators'].items():
            if relationship in text_lower:
                # This indicates the gender of someone else, need context
                if any(word in text_lower for word in ['my', 'i am', "i'm"]):
                    # Likely referring to self
                    gender_candidates.append({
                        'value': gender,
                        'confidence': 0.7,
                        'method': 'relationship_inference',
                        'evidence': relationship
                    })
                    evidence.append(relationship)
        
        # Method 4: ML model prediction
        if self.gender_model:
            try:
                model, vectorizer = self.gender_model
                text_vectorized = vectorizer.transform([text])
                prediction = model.predict(text_vectorized)[0]
                confidence = max(model.predict_proba(text_vectorized)[0])
                
                gender_candidates.append({
                    'value': prediction,
                    'confidence': confidence,
                    'method': 'ml_model',
                    'evidence': 'ML model prediction'
                })
            except Exception as e:
                logger.warning(f"Gender ML model prediction failed: {e}")
        
        if not gender_candidates:
            return None
        
        # Select best prediction
        best_candidate = max(gender_candidates, key=lambda x: x['confidence'])
        
        # Create alternatives list
        alternatives = [c for c in gender_candidates if c != best_candidate][:3]
        
        return DemographicPrediction(
            attribute='gender',
            value=best_candidate['value'],
            confidence=best_candidate['confidence'],
            method=best_candidate['method'],
            evidence=evidence,
            alternatives=alternatives
        )
    
    async def _extract_occupation_advanced(self, text: str, doc, entities: Optional[List[Dict[str, Any]]] = None) -> Optional[DemographicPrediction]:
        """Extract occupation using multiple advanced methods"""
        evidence = []
        occupation_candidates = []
        
        # Method 1: Use provided entities for organization and job title analysis
        if entities:
            for entity in entities:
                if entity.get('label') in ['ORG', 'ORGANIZATION']:
                    org_name = entity.get('text', '')
                    # Infer occupation from organization context
                    occupation_candidates.append({
                        'value': f"Employee at {org_name}",
                        'confidence': 0.6,
                        'method': 'organization_entity_analysis',
                        'evidence': org_name
                    })
                    evidence.append(org_name)
                elif entity.get('label') in ['JOB_TITLE', 'WORK_OF_ART'] and any(word in entity.get('text', '').lower() for word in ['manager', 'director', 'engineer', 'analyst', 'developer', 'consultant', 'specialist']):
                    job_title = entity.get('text', '')
                    occupation_candidates.append({
                        'value': job_title,
                        'confidence': 0.85,
                        'method': 'job_title_entity_analysis',
                        'evidence': job_title
                    })
                    evidence.append(job_title)
        
        # Method 2: Direct pattern matching
        for pattern in self.demographic_rules['occupation_indicators']['direct_occupation']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    occupation = match.group(1).strip()
                    occupation_candidates.append({
                        'value': occupation,
                        'confidence': 0.8,
                        'method': 'direct_pattern',
                        'evidence': match.group(0)
                    })
                    evidence.append(match.group(0))
        
        # Method 3: Phrase matching with spaCy
        matches = self.phrase_matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            occupation_candidates.append({
                'value': span.text,
                'confidence': 0.7,
                'method': 'phrase_matching',
                'evidence': span.text
            })
            evidence.append(span.text)
        
        # Method 4: Industry inference
        text_lower = text.lower()
        for industry, keywords in self.demographic_rules['occupation_indicators']['industry_indicators'].items():
            keyword_count = sum(1 for keyword in keywords if keyword in text_lower)
            if keyword_count > 0:
                confidence = min(0.8, keyword_count / len(keywords) + 0.3)
                occupation_candidates.append({
                    'value': f"{industry}_professional",
                    'confidence': confidence,
                    'method': 'industry_inference',
                    'evidence': f"Industry keywords: {keyword_count}"
                })
        
        # Method 4: ML model prediction
        if self.occupation_model:
            try:
                model, vectorizer = self.occupation_model
                text_vectorized = vectorizer.transform([text])
                prediction = model.predict(text_vectorized)[0]
                confidence = max(model.predict_proba(text_vectorized)[0])
                
                occupation_candidates.append({
                    'value': prediction,
                    'confidence': confidence,
                    'method': 'ml_model',
                    'evidence': 'ML model prediction'
                })
            except Exception as e:
                logger.warning(f"Occupation ML model prediction failed: {e}")
        
        if not occupation_candidates:
            return None
        
        # Select best prediction
        best_candidate = max(occupation_candidates, key=lambda x: x['confidence'])
        
        # Create alternatives list
        alternatives = [c for c in occupation_candidates if c != best_candidate][:3]
        
        return DemographicPrediction(
            attribute='occupation',
            value=best_candidate['value'],
            confidence=best_candidate['confidence'],
            method=best_candidate['method'],
            evidence=evidence,
            alternatives=alternatives
        )
    
    async def _extract_education_advanced(self, text: str, doc, entities: Optional[List[Dict[str, Any]]] = None) -> Optional[DemographicPrediction]:
        """Extract education using advanced methods"""
        evidence = []
        education_candidates = []
        
        # Method 1: Use provided entities for educational institution analysis
        if entities:
            for entity in entities:
                if entity.get('label') in ['ORG', 'ORGANIZATION']:
                    org_name = entity.get('text', '').lower()
                    # Check if organization is educational institution
                    edu_keywords = ['university', 'college', 'school', 'institute', 'academy']
                    if any(keyword in org_name for keyword in edu_keywords):
                        # Infer education level from institution type
                        if 'university' in org_name or 'college' in org_name:
                            education_level = 'bachelor'
                        elif 'school' in org_name:
                            education_level = 'high_school'
                        else:
                            education_level = 'higher_education'
                        
                        education_candidates.append({
                            'value': education_level,
                            'confidence': 0.8,
                            'method': 'educational_institution_analysis',
                            'evidence': entity.get('text', '')
                        })
                        evidence.append(entity.get('text', ''))
        
        # Method 2: Degree pattern matching
        for pattern in self.demographic_rules['education_indicators']['degree_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    degree = match.group(1).lower()
                    normalized_degree = self.demographic_rules['education_indicators']['education_levels'].get(degree, degree)
                    education_candidates.append({
                        'value': normalized_degree,
                        'confidence': 0.9,
                        'method': 'degree_pattern',
                        'evidence': match.group(0)
                    })
                    evidence.append(match.group(0))
        
        # Method 2: Institution pattern matching
        for pattern in self.demographic_rules['education_indicators']['institution_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    institution = match.group(1)
                    # Infer education level from institution type
                    if 'university' in institution.lower():
                        education_level = 'university'
                    elif 'college' in institution.lower():
                        education_level = 'college'
                    else:
                        education_level = 'higher_education'
                    
                    education_candidates.append({
                        'value': education_level,
                        'confidence': 0.7,
                        'method': 'institution_pattern',
                        'evidence': match.group(0)
                    })
                    evidence.append(match.group(0))
        
        # Method 3: Education level keywords
        text_lower = text.lower()
        for education_term, level in self.demographic_rules['education_indicators']['education_levels'].items():
            if education_term in text_lower:
                education_candidates.append({
                    'value': level,
                    'confidence': 0.6,
                    'method': 'keyword_matching',
                    'evidence': education_term
                })
                evidence.append(education_term)
        
        if not education_candidates:
            return None
        
        # Select best prediction
        best_candidate = max(education_candidates, key=lambda x: x['confidence'])
        
        # Create alternatives list
        alternatives = [c for c in education_candidates if c != best_candidate][:3]
        
        return DemographicPrediction(
            attribute='education',
            value=best_candidate['value'],
            confidence=best_candidate['confidence'],
            method=best_candidate['method'],
            evidence=evidence,
            alternatives=alternatives
        )
    
    async def _extract_income_advanced(self, text: str, doc, entities: Optional[List[Dict[str, Any]]] = None) -> Optional[DemographicPrediction]:
        """Extract income using advanced methods"""
        evidence = []
        income_candidates = []
        
        # Method 1: Use provided entities for monetary value analysis
        if entities:
            for entity in entities:
                if entity.get('label') in ['MONEY', 'CARDINAL']:
                    entity_text = entity.get('text', '')
                    # Extract numerical value from monetary entities
                    money_match = re.search(r'[\$£€]?([\d,]+(?:\.\d{2})?)', entity_text)
                    if money_match:
                        try:
                            amount_str = money_match.group(1).replace(',', '')
                            amount = float(amount_str)
                            
                            # Check if it's likely a salary (reasonable range)
                            if 10000 <= amount <= 1000000:
                                income_category = self._categorize_income(int(amount))
                                income_candidates.append({
                                    'value': income_category,
                                    'confidence': 0.85,
                                    'method': 'monetary_entity_analysis',
                                    'evidence': entity_text
                                })
                                evidence.append(entity_text)
                        except ValueError:
                            continue
        
        # Method 2: Salary pattern matching
        for pattern in self.demographic_rules['income_indicators']['salary_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    salary_str = match.group(1).replace(',', '')
                    if salary_str.isdigit():
                        salary = int(salary_str)
                        # Convert to annual if needed
                        if 'k' in match.group(0).lower() or 'thousand' in match.group(0).lower():
                            salary *= 1000
                        
                        income_bracket = self._categorize_income(salary)
                        income_candidates.append({
                            'value': income_bracket,
                            'confidence': 0.8,
                            'method': 'salary_pattern',
                            'evidence': match.group(0)
                        })
                        evidence.append(match.group(0))
        
        # Method 2: Income bracket keywords
        text_lower = text.lower()
        for income_term, bracket in self.demographic_rules['income_indicators']['income_brackets'].items():
            if income_term in text_lower:
                income_candidates.append({
                    'value': bracket,
                    'confidence': 0.6,
                    'method': 'bracket_keywords',
                    'evidence': income_term
                })
                evidence.append(income_term)
        
        if not income_candidates:
            return None
        
        # Select best prediction
        best_candidate = max(income_candidates, key=lambda x: x['confidence'])
        
        # Create alternatives list
        alternatives = [c for c in income_candidates if c != best_candidate][:3]
        
        return DemographicPrediction(
            attribute='income',
            value=best_candidate['value'],
            confidence=best_candidate['confidence'],
            method=best_candidate['method'],
            evidence=evidence,
            alternatives=alternatives
        )
    
    async def _extract_location_advanced(self, text: str, doc, entities: Optional[List[Dict[str, Any]]] = None) -> Optional[DemographicPrediction]:
        """Extract location using NER"""
        evidence = []
        location_candidates = []
        
        # Method 1: Use provided entities if available (higher confidence)
        if entities:
            for entity in entities:
                if entity.get('label') in ['GPE', 'LOC', 'LOCATION']:
                    location_candidates.append({
                        'value': entity.get('text', ''),
                        'confidence': 0.85,
                        'method': 'advanced_ner_extraction',
                        'evidence': entity.get('text', '')
                    })
                    evidence.append(entity.get('text', ''))
        
        # Method 2: Extract location entities from spaCy
        locations = [ent for ent in doc.ents if ent.label_ in ['GPE', 'LOC']]
        
        for location in locations:
            # Avoid duplicates from Method 1
            if not any(candidate['value'].lower() == location.text.lower() for candidate in location_candidates):
                location_candidates.append({
                    'value': location.text,
                    'confidence': 0.7,
                    'method': 'spacy_ner',
                    'evidence': location.text
                })
                evidence.append(location.text)
        
        if not location_candidates:
            return None
        
        # Select best prediction (first/most confident)
        best_candidate = location_candidates[0]
        
        # Create alternatives list
        alternatives = location_candidates[1:4]
        
        return DemographicPrediction(
            attribute='location',
            value=best_candidate['value'],
            confidence=best_candidate['confidence'],
            method=best_candidate['method'],
            evidence=evidence,
            alternatives=alternatives
        )
    
    def _normalize_gender_term(self, gender_term: str) -> Optional[str]:
        """Normalize gender terminology"""
        gender_term = gender_term.lower().strip()
        
        if gender_term in ['male', 'man', 'guy', 'boy', 'gentleman']:
            return 'male'
        elif gender_term in ['female', 'woman', 'girl', 'lady']:
            return 'female'
        elif gender_term in ['non-binary', 'nb', 'enby']:
            return 'non-binary'
        
        return None
    
    def _categorize_income(self, salary: int) -> str:
        """Categorize income into brackets"""
        if salary < 30000:
            return 'low'
        elif salary < 75000:
            return 'middle'
        elif salary < 150000:
            return 'upper-middle'
        else:
            return 'high'
    
    def _detect_bias_indicators(self, predictions: List[DemographicPrediction]) -> List[str]:
        """Detect potential bias indicators in predictions"""
        bias_indicators = []
        
        # Check for gender bias
        gender_predictions = [p for p in predictions if p.attribute == 'gender']
        if gender_predictions:
            gender_value = gender_predictions[0].value
            if gender_value in ['male', 'female'] and gender_predictions[0].confidence < 0.7:
                bias_indicators.append("Low confidence gender prediction may indicate bias")
        
        # Check for occupation-gender correlation bias
        occupation_predictions = [p for p in predictions if p.attribute == 'occupation']
        if gender_predictions and occupation_predictions:
            gender = gender_predictions[0].value
            occupation = occupation_predictions[0].value
            
            # Simple bias detection (in practice, use more sophisticated methods)
            if gender == 'female' and 'engineer' in occupation.lower():
                bias_indicators.append("Potential gender-occupation bias detected")
        
        return bias_indicators
    
    def _analyze_uncertainty(self, predictions: List[DemographicPrediction], text: str) -> Dict[str, Any]:
        """Analyze uncertainty in predictions"""
        if not predictions:
            return {'overall_uncertainty': 1.0, 'low_confidence_attributes': []}
        
        confidences = [p.confidence for p in predictions]
        overall_uncertainty = 1.0 - float(np.mean(confidences))
        
        low_confidence_attributes = [
            p.attribute for p in predictions if p.confidence < 0.6
        ]
        
        # Analyze text characteristics that might affect uncertainty
        text_length = len(text)
        uncertainty_factors = []
        
        if text_length < 100:
            uncertainty_factors.append("Short text length")
        
        if not any(p.method == 'ml_model' for p in predictions):
            uncertainty_factors.append("No ML model predictions available")
        
        return {
            'overall_uncertainty': overall_uncertainty,
            'low_confidence_attributes': low_confidence_attributes,
            'uncertainty_factors': uncertainty_factors,
            'confidence_distribution': {
                'mean': float(np.mean(confidences)),
                'std': float(np.std(confidences)),
                'min': float(np.min(confidences)),
                'max': float(np.max(confidences))
            }
        }