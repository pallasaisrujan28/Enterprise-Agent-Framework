"""Advanced NLP service for sophisticated text analysis and entity extraction"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
import re
import json
from collections import Counter, defaultdict

# Core NLP libraries
import spacy
import nltk
from textblob import TextBlob
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.metrics.pairwise import cosine_similarity

# Advanced transformers and embeddings
from transformers import pipeline, AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
import torch

# Statistical and ML libraries
from scipy import stats
from scipy.spatial.distance import pdist, squareform
import matplotlib.pyplot as plt
import seaborn as sns

# Validation
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class EntityExtractionResult(BaseModel):
    """Result of entity extraction"""
    entities: Dict[str, List[Dict[str, Any]]]
    demographics: Dict[str, Any]
    psychographics: Dict[str, Any]
    behavioral_indicators: Dict[str, Any]
    sentiment_analysis: Dict[str, Any]
    topic_modeling: Dict[str, Any]
    linguistic_features: Dict[str, Any]
    confidence_scores: Dict[str, float]
    processing_metadata: Dict[str, Any]

class AdvancedNLPService:
    """Advanced NLP service with multiple model support"""
    
    def __init__(self, spacy_model: str = "en_core_web_lg"):
        """
        Initialize NLP service with advanced models
        
        Args:
            spacy_model: spaCy model to use (en_core_web_sm, en_core_web_md, en_core_web_lg)
        """
        self.spacy_model_name = spacy_model
        self.nlp = None
        self.demographic_patterns = self._load_demographic_patterns()
        self.psychographic_indicators = self._load_psychographic_indicators()
        self.behavioral_patterns = self._load_behavioral_patterns()
        
        # Transformer models
        self.sentiment_pipeline = None
        self.emotion_pipeline = None
        self.sentence_transformer = None
        self.ner_pipeline = None
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize NLP models and download required data"""
        try:
            # Load spaCy model
            self.nlp = spacy.load(self.spacy_model_name)
            logger.info(f"Loaded spaCy model: {self.spacy_model_name}")
        except OSError:
            logger.warning(f"spaCy model {self.spacy_model_name} not found, falling back to en_core_web_sm")
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.error("No spaCy model available. Please install: python -m spacy download en_core_web_sm")
                raise
        
        # Download required NLTK data with SSL handling
        import ssl
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context
        
        nltk_packages = [
            ('tokenizers/punkt', 'punkt'),
            ('corpora/stopwords', 'stopwords'),
            ('taggers/averaged_perceptron_tagger', 'averaged_perceptron_tagger'),
            ('corpora/wordnet', 'wordnet')
        ]
        
        for data_path, package_name in nltk_packages:
            try:
                nltk.data.find(data_path)
                logger.info(f"NLTK package {package_name} already available")
            except LookupError:
                try:
                    logger.info(f"Downloading NLTK package: {package_name}")
                    nltk.download(package_name, quiet=True)
                    logger.info(f"Successfully downloaded NLTK package: {package_name}")
                except Exception as e:
                    logger.warning(f"Failed to download NLTK package {package_name}: {e}")
                    logger.warning(f"Some NLP features may be limited without {package_name}")
        
        # Initialize transformer models
        self._initialize_transformer_models()
    
    def _initialize_transformer_models(self):
        """Initialize transformer-based models for advanced NLP"""
        try:
            # Sentiment analysis pipeline
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                return_all_scores=True
            )
            logger.info("Loaded sentiment analysis pipeline")
            
            # Emotion detection pipeline
            self.emotion_pipeline = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                return_all_scores=True
            )
            logger.info("Loaded emotion detection pipeline")
            
            # Named Entity Recognition pipeline
            self.ner_pipeline = pipeline(
                "ner",
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                aggregation_strategy="simple"
            )
            logger.info("Loaded NER pipeline")
            
            # Sentence transformer for embeddings
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded sentence transformer model")
            
        except Exception as e:
            logger.warning(f"Failed to load some transformer models: {e}")
            logger.info("Falling back to basic NLP processing")
    
    def _load_demographic_patterns(self) -> Dict[str, List[str]]:
        """Load demographic extraction patterns"""
        return {
            'age_indicators': [
                r'\b(?:i am|i\'m)\s+(\d{1,2})\s+(?:years?\s+old|yo)\b',
                r'\b(\d{1,2})\s*(?:year|yr)s?\s*old\b',
                r'\baged?\s+(\d{1,2})\b',
                r'\b(?:in my|my)\s+(early|mid|late)\s+(teens|twenties|thirties|forties|fifties|sixties|seventies)\b',
                r'\b(teenager|teen|young adult|middle aged|elderly|senior)\b'
            ],
            'gender_indicators': [
                r'\b(?:i am|i\'m)\s+(?:a\s+)?(male|female|man|woman|guy|girl|boy|lady|gentleman)\b',
                r'\b(?:as a|being a)\s+(male|female|man|woman|guy|girl|boy|lady|gentleman)\b',
                r'\b(he/him|she/her|they/them|he\/his|she\/hers)\b',
                r'\b(?:my|the)\s+(husband|wife|boyfriend|girlfriend|partner)\b'
            ],
            'location_indicators': [
                r'\b(?:i live in|living in|from|based in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
                r'\b(?:in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\b',
                r'\b(urban|suburban|rural|city|town|village)\s+(?:area|environment|setting)\b'
            ],
            'occupation_indicators': [
                r'\b(?:i work as|working as|i am a|job as|employed as)\s+(?:a\s+|an\s+)?([a-z\s]+)\b',
                r'\b(?:my job|my career|my profession)\s+(?:is|as)\s+(?:a\s+|an\s+)?([a-z\s]+)\b',
                r'\b(student|teacher|doctor|nurse|engineer|manager|developer|designer|analyst)\b'
            ],
            'education_indicators': [
                r'\b(?:i have|i hold)\s+(?:a\s+|an\s+)?(bachelor|master|phd|doctorate|degree|diploma)\b',
                r'\b(?:graduated from|studied at|attending)\s+([A-Z][a-z\s]+(?:university|college|school))\b',
                r'\b(high school|college|university|graduate school)\s+(?:graduate|student|education)\b'
            ],
            'income_indicators': [
                r'\b(?:earn|make|income of)\s+(?:about\s+|around\s+)?\$?([0-9,]+)\s*(?:k|thousand|per year|annually)?\b',
                r'\b(low income|middle class|upper class|wealthy|struggling financially)\b',
                r'\b(?:budget|afford|expensive|cheap|cost)\b'
            ],
            'family_indicators': [
                r'\b(?:i have|we have)\s+(\d+)\s+(?:kids?|children)\b',
                r'\b(?:married|single|divorced|widowed|in a relationship)\b',
                r'\b(?:my|our)\s+(family|spouse|partner|children|kids)\b'
            ]
        }
    
    def _load_psychographic_indicators(self) -> Dict[str, List[str]]:
        """Load psychographic analysis patterns"""
        return {
            'values': {
                'family_oriented': ['family', 'children', 'kids', 'parenting', 'home', 'tradition'],
                'career_focused': ['career', 'professional', 'success', 'achievement', 'ambition', 'work'],
                'health_conscious': ['health', 'fitness', 'exercise', 'nutrition', 'wellness', 'organic'],
                'environmentally_conscious': ['environment', 'sustainable', 'eco-friendly', 'green', 'climate'],
                'socially_conscious': ['community', 'social justice', 'equality', 'volunteer', 'charity'],
                'financially_conscious': ['savings', 'investment', 'budget', 'financial planning', 'money']
            },
            'interests': {
                'technology': ['tech', 'gadgets', 'software', 'apps', 'digital', 'innovation'],
                'sports': ['sports', 'football', 'basketball', 'soccer', 'tennis', 'fitness'],
                'arts': ['art', 'music', 'painting', 'theater', 'culture', 'creative'],
                'travel': ['travel', 'vacation', 'explore', 'adventure', 'tourism', 'destinations'],
                'food': ['cooking', 'food', 'restaurant', 'cuisine', 'recipe', 'dining'],
                'entertainment': ['movies', 'tv', 'games', 'entertainment', 'streaming', 'media']
            },
            'personality_traits': {
                'extroverted': ['social', 'outgoing', 'party', 'friends', 'networking', 'talkative'],
                'introverted': ['quiet', 'private', 'alone time', 'solitude', 'introspective'],
                'analytical': ['analyze', 'data', 'research', 'logical', 'systematic', 'detail'],
                'creative': ['creative', 'artistic', 'innovative', 'imagination', 'original'],
                'adventurous': ['adventure', 'risk', 'explore', 'new experiences', 'spontaneous'],
                'conservative': ['traditional', 'stable', 'reliable', 'conventional', 'cautious']
            }
        }
    
    def _load_behavioral_patterns(self) -> Dict[str, List[str]]:
        """Load behavioral analysis patterns"""
        return {
            'shopping_behavior': {
                'price_sensitive': ['cheap', 'discount', 'sale', 'bargain', 'budget', 'affordable'],
                'quality_focused': ['quality', 'premium', 'luxury', 'high-end', 'durable', 'reliable'],
                'brand_loyal': ['brand', 'loyal', 'favorite', 'always buy', 'trust', 'consistent'],
                'impulse_buyer': ['impulse', 'spontaneous', 'sudden', 'immediate', 'quick decision']
            },
            'communication_style': {
                'formal': ['professional', 'formal', 'business', 'official', 'proper'],
                'casual': ['casual', 'informal', 'relaxed', 'friendly', 'laid-back'],
                'direct': ['direct', 'straightforward', 'honest', 'blunt', 'clear'],
                'diplomatic': ['diplomatic', 'tactful', 'careful', 'considerate', 'polite']
            },
            'decision_making': {
                'research_heavy': ['research', 'compare', 'analyze', 'investigate', 'study'],
                'quick_decision': ['quick', 'fast', 'immediate', 'instant', 'rapid'],
                'consensus_seeking': ['discuss', 'consult', 'ask others', 'group decision', 'collaborate'],
                'independent': ['independent', 'self-reliant', 'own decision', 'autonomous']
            }
        }
    
    async def extract_entities_advanced(self, text: str) -> EntityExtractionResult:
        """Advanced entity extraction using multiple NLP techniques"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Process text with spaCy
            doc = self.nlp(text)
            
            # Generate semantic embeddings
            embeddings = await self._generate_embeddings(text)
            
            # Extract named entities using both spaCy and transformers
            entities = await self._extract_named_entities_advanced(text, doc)
            
            # Extract demographics
            demographics = await self._extract_demographics(text, doc)
            
            # Extract psychographics
            psychographics = await self._extract_psychographics(text, doc)
            
            # Extract behavioral indicators
            behavioral_indicators = await self._extract_behavioral_indicators(text, doc)
            
            # Perform advanced sentiment analysis with transformers
            sentiment_analysis = await self._analyze_sentiment_advanced(text, doc)
            
            # Perform topic modeling
            topic_modeling = await self._perform_topic_modeling(text)
            
            # Extract linguistic features
            linguistic_features = self._extract_linguistic_features(text, doc)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(
                entities, demographics, psychographics, behavioral_indicators
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return EntityExtractionResult(
                entities=entities,
                demographics=demographics,
                psychographics=psychographics,
                behavioral_indicators=behavioral_indicators,
                sentiment_analysis=sentiment_analysis,
                topic_modeling=topic_modeling,
                linguistic_features=linguistic_features,
                confidence_scores=confidence_scores,
                processing_metadata={
                    'processing_time': processing_time,
                    'text_length': len(text),
                    'sentence_count': len(list(doc.sents)),
                    'token_count': len(doc),
                    'spacy_model': self.spacy_model_name,
                    'has_embeddings': embeddings is not None,
                    'transformer_models_loaded': self.sentiment_pipeline is not None,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Advanced entity extraction failed: {e}")
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return EntityExtractionResult(
                entities={},
                demographics={},
                psychographics={},
                behavioral_indicators={},
                sentiment_analysis={},
                topic_modeling={},
                linguistic_features={},
                confidence_scores={},
                processing_metadata={'error': str(e), 'processing_time': processing_time}
            )
    
    async def _extract_named_entities_advanced(self, text: str, doc) -> Dict[str, List[Dict[str, Any]]]:
        """Extract named entities using both spaCy and transformers"""
        entities = defaultdict(list)
        
        # spaCy entities
        for ent in doc.ents:
            entities[f"spacy_{ent.label_}"].append({
                'text': ent.text,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': getattr(ent, 'confidence', 0.8),
                'source': 'spacy'
            })
        
        # Transformer-based NER
        if self.ner_pipeline:
            try:
                transformer_entities = self.ner_pipeline(text[:512])  # Limit text length
                for ent in transformer_entities:
                    entities[f"transformer_{ent['entity_group']}"].append({
                        'text': ent['word'],
                        'start': ent.get('start', 0),
                        'end': ent.get('end', 0),
                        'confidence': ent['score'],
                        'source': 'transformer'
                    })
            except Exception as e:
                logger.warning(f"Transformer NER failed: {e}")
        
        return dict(entities)
    
    def _extract_named_entities(self, doc) -> Dict[str, List[Dict[str, Any]]]:
        """Extract named entities using spaCy (legacy method)"""
        entities = defaultdict(list)
        
        for ent in doc.ents:
            entities[ent.label_].append({
                'text': ent.text,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': getattr(ent, 'confidence', 0.8)
            })
        
        return dict(entities)
    
    async def _extract_demographics(self, text: str, doc) -> Dict[str, Any]:
        """Extract demographic information using pattern matching and NLP"""
        demographics = {
            'age': {'value': None, 'confidence': 0.0, 'evidence': []},
            'gender': {'value': None, 'confidence': 0.0, 'evidence': []},
            'location': {'value': None, 'confidence': 0.0, 'evidence': []},
            'occupation': {'value': None, 'confidence': 0.0, 'evidence': []},
            'education': {'value': None, 'confidence': 0.0, 'evidence': []},
            'income': {'value': None, 'confidence': 0.0, 'evidence': []},
            'family_status': {'value': None, 'confidence': 0.0, 'evidence': []}
        }
        
        text_lower = text.lower()
        
        # Extract age information
        for pattern in self.demographic_patterns['age_indicators']:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if match.group(1).isdigit():
                    age = int(match.group(1))
                    if 10 <= age <= 100:
                        demographics['age']['value'] = age
                        demographics['age']['confidence'] = 0.9
                        demographics['age']['evidence'].append(match.group(0))
                else:
                    # Handle age ranges like "early twenties"
                    age_range = self._parse_age_range(match.group(0))
                    if age_range:
                        demographics['age']['value'] = age_range
                        demographics['age']['confidence'] = 0.7
                        demographics['age']['evidence'].append(match.group(0))
        
        # Extract gender information
        for pattern in self.demographic_patterns['gender_indicators']:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                gender = self._normalize_gender(match.group(1) if len(match.groups()) > 0 else match.group(0))
                if gender:
                    demographics['gender']['value'] = gender
                    demographics['gender']['confidence'] = 0.8
                    demographics['gender']['evidence'].append(match.group(0))
        
        # Extract location information
        locations = [ent.text for ent in doc.ents if ent.label_ in ['GPE', 'LOC']]
        if locations:
            demographics['location']['value'] = locations[0]
            demographics['location']['confidence'] = 0.7
            demographics['location']['evidence'] = locations
        
        # Extract occupation information
        for pattern in self.demographic_patterns['occupation_indicators']:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) > 0:
                    occupation = match.group(1).strip()
                    demographics['occupation']['value'] = occupation
                    demographics['occupation']['confidence'] = 0.7
                    demographics['occupation']['evidence'].append(match.group(0))
        
        return demographics
    
    async def _extract_psychographics(self, text: str, doc) -> Dict[str, Any]:
        """Extract psychographic information"""
        psychographics = {
            'values': [],
            'interests': [],
            'personality_traits': [],
            'lifestyle_indicators': [],
            'motivations': [],
            'pain_points': []
        }
        
        text_lower = text.lower()
        
        # Extract values
        for value_type, keywords in self.psychographic_indicators['values'].items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                psychographics['values'].append({
                    'type': value_type,
                    'score': score / len(keywords),
                    'evidence_count': score
                })
        
        # Extract interests
        for interest_type, keywords in self.psychographic_indicators['interests'].items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                psychographics['interests'].append({
                    'type': interest_type,
                    'score': score / len(keywords),
                    'evidence_count': score
                })
        
        # Extract personality traits
        for trait_type, keywords in self.psychographic_indicators['personality_traits'].items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                psychographics['personality_traits'].append({
                    'type': trait_type,
                    'score': score / len(keywords),
                    'evidence_count': score
                })
        
        # Extract pain points and motivations from sentiment and context
        sentences = [sent.text for sent in doc.sents]
        for sentence in sentences:
            blob = TextBlob(sentence)
            if blob.sentiment.polarity < -0.3:  # Negative sentiment
                psychographics['pain_points'].append({
                    'text': sentence.strip(),
                    'sentiment': blob.sentiment.polarity
                })
            elif blob.sentiment.polarity > 0.3:  # Positive sentiment
                psychographics['motivations'].append({
                    'text': sentence.strip(),
                    'sentiment': blob.sentiment.polarity
                })
        
        return psychographics
    
    async def _extract_behavioral_indicators(self, text: str, doc) -> Dict[str, Any]:
        """Extract behavioral indicators"""
        behavioral_indicators = {
            'shopping_behavior': [],
            'communication_style': [],
            'decision_making': [],
            'technology_usage': [],
            'social_behavior': []
        }
        
        text_lower = text.lower()
        
        # Extract shopping behavior
        for behavior_type, keywords in self.behavioral_patterns['shopping_behavior'].items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                behavioral_indicators['shopping_behavior'].append({
                    'type': behavior_type,
                    'score': score / len(keywords),
                    'evidence_count': score
                })
        
        # Extract communication style
        for style_type, keywords in self.behavioral_patterns['communication_style'].items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                behavioral_indicators['communication_style'].append({
                    'type': style_type,
                    'score': score / len(keywords),
                    'evidence_count': score
                })
        
        # Extract decision making patterns
        for decision_type, keywords in self.behavioral_patterns['decision_making'].items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                behavioral_indicators['decision_making'].append({
                    'type': decision_type,
                    'score': score / len(keywords),
                    'evidence_count': score
                })
        
        return behavioral_indicators
    
    async def _generate_embeddings(self, text: str) -> Optional[np.ndarray]:
        """Generate semantic embeddings for text"""
        try:
            if self.sentence_transformer:
                embeddings = self.sentence_transformer.encode([text])
                return embeddings[0]
        except Exception as e:
            logger.warning(f"Failed to generate embeddings: {e}")
        return None
    
    async def _analyze_sentiment_advanced(self, text: str, doc) -> Dict[str, Any]:
        """Perform advanced sentiment analysis using transformers and TextBlob"""
        blob = TextBlob(text)
        
        # Basic TextBlob sentiment
        textblob_sentiment = {
            'polarity': blob.sentiment.polarity,
            'subjectivity': blob.sentiment.subjectivity,
            'label': self._get_sentiment_label(blob.sentiment.polarity)
        }
        
        # Advanced transformer-based sentiment
        transformer_sentiment = None
        if self.sentiment_pipeline:
            try:
                results = self.sentiment_pipeline(text[:512])  # Limit text length
                transformer_sentiment = {
                    'predictions': results[0] if results else [],
                    'dominant_sentiment': max(results[0], key=lambda x: x['score'])['label'] if results and results[0] else 'neutral'
                }
            except Exception as e:
                logger.warning(f"Transformer sentiment analysis failed: {e}")
        
        # Emotion analysis
        emotions = None
        if self.emotion_pipeline:
            try:
                emotion_results = self.emotion_pipeline(text[:512])
                emotions = {
                    'predictions': emotion_results[0] if emotion_results else [],
                    'dominant_emotion': max(emotion_results[0], key=lambda x: x['score'])['label'] if emotion_results and emotion_results[0] else 'neutral'
                }
            except Exception as e:
                logger.warning(f"Emotion analysis failed: {e}")
        
        # Sentence-level sentiment
        sentence_sentiments = []
        for sent in doc.sents:
            sent_blob = TextBlob(sent.text)
            sentence_sentiments.append({
                'text': sent.text.strip(),
                'polarity': sent_blob.sentiment.polarity,
                'subjectivity': sent_blob.sentiment.subjectivity
            })
        
        return {
            'textblob': textblob_sentiment,
            'transformer': transformer_sentiment,
            'emotions': emotions,
            'sentence_sentiments': sentence_sentiments,
            'emotional_indicators': self._extract_emotional_indicators(text)
        }
    
    async def _analyze_sentiment(self, text: str, doc) -> Dict[str, Any]:
        """Perform comprehensive sentiment analysis (legacy method)"""
        blob = TextBlob(text)
        
        # Sentence-level sentiment
        sentence_sentiments = []
        for sent in doc.sents:
            sent_blob = TextBlob(sent.text)
            sentence_sentiments.append({
                'text': sent.text.strip(),
                'polarity': sent_blob.sentiment.polarity,
                'subjectivity': sent_blob.sentiment.subjectivity
            })
        
        return {
            'overall_polarity': blob.sentiment.polarity,
            'overall_subjectivity': blob.sentiment.subjectivity,
            'sentiment_label': self._get_sentiment_label(blob.sentiment.polarity),
            'sentence_sentiments': sentence_sentiments,
            'emotional_indicators': self._extract_emotional_indicators(text)
        }
    
    async def _perform_topic_modeling(self, text: str) -> Dict[str, Any]:
        """Perform topic modeling using LDA"""
        try:
            # Split into sentences for topic modeling
            sentences = nltk.sent_tokenize(text)
            
            if len(sentences) < 3:
                return {'topics': [], 'method': 'insufficient_data'}
            
            # Vectorize text
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            doc_term_matrix = vectorizer.fit_transform(sentences)
            
            # Perform LDA
            n_topics = min(3, len(sentences))
            lda = LatentDirichletAllocation(n_components=n_topics, random_state=42)
            lda.fit(doc_term_matrix)
            
            # Extract topics
            feature_names = vectorizer.get_feature_names_out()
            topics = []
            
            for topic_idx, topic in enumerate(lda.components_):
                top_words_idx = topic.argsort()[-10:][::-1]
                top_words = [feature_names[i] for i in top_words_idx]
                topics.append({
                    'id': topic_idx,
                    'words': top_words,
                    'weight': float(topic.max())
                })
            
            return {
                'topics': topics,
                'method': 'lda',
                'n_topics': n_topics
            }
            
        except Exception as e:
            logger.error(f"Topic modeling failed: {e}")
            return {'topics': [], 'method': 'error', 'error': str(e)}
    
    def _extract_linguistic_features(self, text: str, doc) -> Dict[str, Any]:
        """Extract linguistic features from text"""
        return {
            'readability': self._calculate_readability(text),
            'lexical_diversity': self._calculate_lexical_diversity(doc),
            'pos_distribution': self._get_pos_distribution(doc),
            'sentence_complexity': self._analyze_sentence_complexity(doc),
            'vocabulary_sophistication': self._analyze_vocabulary_sophistication(doc)
        }
    
    def _calculate_confidence_scores(self, entities, demographics, psychographics, behavioral_indicators) -> Dict[str, float]:
        """Calculate confidence scores for extracted information"""
        scores = {}
        
        # Demographics confidence
        demo_scores = [demo['confidence'] for demo in demographics.values() if demo['confidence'] > 0]
        scores['demographics'] = float(np.mean(demo_scores)) if demo_scores else 0.0
        
        # Psychographics confidence
        psycho_scores = []
        for category in psychographics.values():
            if isinstance(category, list) and category:
                psycho_scores.extend([item.get('score', 0) for item in category])
        scores['psychographics'] = float(np.mean(psycho_scores)) if psycho_scores else 0.0
        
        # Behavioral confidence
        behavior_scores = []
        for category in behavioral_indicators.values():
            if isinstance(category, list) and category:
                behavior_scores.extend([item.get('score', 0) for item in category])
        scores['behavioral'] = float(np.mean(behavior_scores)) if behavior_scores else 0.0
        
        # Overall confidence
        all_scores = [score for score in scores.values() if score > 0]
        scores['overall'] = float(np.mean(all_scores)) if all_scores else 0.0
        
        return scores
    
    def _parse_age_range(self, age_text: str) -> Optional[str]:
        """Parse age range from text"""
        age_mappings = {
            'teens': '13-19',
            'twenties': '20-29',
            'thirties': '30-39',
            'forties': '40-49',
            'fifties': '50-59',
            'sixties': '60-69',
            'seventies': '70-79'
        }
        
        for age_word, age_range in age_mappings.items():
            if age_word in age_text.lower():
                return age_range
        return None
    
    def _normalize_gender(self, gender_text: str) -> Optional[str]:
        """Normalize gender text"""
        gender_text = gender_text.lower().strip()
        
        if gender_text in ['male', 'man', 'guy', 'boy', 'gentleman', 'he/him']:
            return 'male'
        elif gender_text in ['female', 'woman', 'girl', 'lady', 'she/her']:
            return 'female'
        elif gender_text in ['they/them', 'non-binary', 'nb']:
            return 'non-binary'
        
        return None
    
    def _get_sentiment_label(self, polarity: float) -> str:
        """Get sentiment label from polarity score"""
        if polarity > 0.1:
            return 'positive'
        elif polarity < -0.1:
            return 'negative'
        else:
            return 'neutral'
    
    def _extract_emotional_indicators(self, text: str) -> List[str]:
        """Extract emotional indicators from text"""
        emotion_keywords = {
            'joy': ['happy', 'excited', 'thrilled', 'delighted', 'joyful'],
            'anger': ['angry', 'frustrated', 'annoyed', 'furious', 'mad'],
            'sadness': ['sad', 'depressed', 'disappointed', 'upset', 'down'],
            'fear': ['afraid', 'scared', 'worried', 'anxious', 'nervous'],
            'surprise': ['surprised', 'shocked', 'amazed', 'astonished'],
            'disgust': ['disgusted', 'revolted', 'appalled', 'sickened']
        }
        
        text_lower = text.lower()
        detected_emotions = []
        
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_emotions.append(emotion)
        
        return detected_emotions
    
    def _calculate_readability(self, text: str) -> Dict[str, float]:
        """Calculate readability metrics"""
        sentences = nltk.sent_tokenize(text)
        words = nltk.word_tokenize(text)
        
        if not sentences or not words:
            return {'flesch_score': 0.0, 'avg_sentence_length': 0.0}
        
        avg_sentence_length = len(words) / len(sentences)
        
        # Simple Flesch reading ease approximation
        syllable_count = sum(self._count_syllables(word) for word in words)
        avg_syllables_per_word = syllable_count / len(words) if words else 0
        
        flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        
        return {
            'flesch_score': max(0, min(100, flesch_score)),
            'avg_sentence_length': avg_sentence_length
        }
    
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simple approximation)"""
        word = word.lower()
        vowels = 'aeiouy'
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        
        # Handle silent 'e'
        if word.endswith('e'):
            syllable_count -= 1
        
        return max(1, syllable_count)
    
    def _calculate_lexical_diversity(self, doc) -> float:
        """Calculate lexical diversity (type-token ratio)"""
        tokens = [token.text.lower() for token in doc if token.is_alpha]
        if not tokens:
            return 0.0
        
        unique_tokens = set(tokens)
        return len(unique_tokens) / len(tokens)
    
    def _get_pos_distribution(self, doc) -> Dict[str, float]:
        """Get part-of-speech distribution"""
        pos_counts = Counter(token.pos_ for token in doc if token.is_alpha)
        total = sum(pos_counts.values())
        
        if total == 0:
            return {}
        
        return {pos: count / total for pos, count in pos_counts.items()}
    
    def _analyze_sentence_complexity(self, doc) -> Dict[str, float]:
        """Analyze sentence complexity"""
        sentences = list(doc.sents)
        if not sentences:
            return {'avg_length': 0.0, 'complexity_score': 0.0}
        
        lengths = [len(sent) for sent in sentences]
        avg_length = float(np.mean(lengths))
        
        # Simple complexity score based on subordinate clauses
        complexity_indicators = ['because', 'although', 'while', 'since', 'if', 'when', 'where']
        complexity_count = sum(1 for sent in sentences 
                             for token in sent 
                             if token.text.lower() in complexity_indicators)
        
        complexity_score = complexity_count / len(sentences) if sentences else 0
        
        return {
            'avg_length': avg_length,
            'complexity_score': complexity_score
        }
    
    def _analyze_vocabulary_sophistication(self, doc) -> Dict[str, float]:
        """Analyze vocabulary sophistication"""
        tokens = [token for token in doc if token.is_alpha and not token.is_stop]
        if not tokens:
            return {'avg_word_length': 0.0, 'rare_word_ratio': 0.0}
        
        word_lengths = [len(token.text) for token in tokens]
        avg_word_length = float(np.mean(word_lengths))
        
        # Simple rare word detection (words longer than 7 characters)
        rare_words = [token for token in tokens if len(token.text) > 7]
        rare_word_ratio = len(rare_words) / len(tokens) if tokens else 0
        
        return {
            'avg_word_length': avg_word_length,
            'rare_word_ratio': rare_word_ratio
        }