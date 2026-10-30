#!/usr/bin/env python3
"""
Enhanced Four-Layer Trait Selection System v2.0
Updated to work with normalized database schema from Phase 2B migration
"""

import psycopg2
import psycopg2.extras
import json
import numpy as np
from typing import Dict, List, Any, Tuple
from sentence_transformers import SentenceTransformer
import re
from datetime import datetime


class SemanticLayerV2:
    """Layer 1: Semantic Embedding Analysis - Updated for normalized schema"""

    def __init__(self):
        print("🧠 Initializing Semantic Layer v2.0...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def calculate_similarity(self, product_query: str, trait_embeddings: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity between product and traits using stored embeddings"""
        if len(trait_embeddings) == 0:
            return np.array([])

        # Generate product embedding
        product_embedding = self.model.encode([product_query])

        # Calculate cosine similarity using stored embeddings
        similarities = np.dot(product_embedding, trait_embeddings.T)[0]

        # Normalize to 0-1 range
        similarities = (similarities + 1) / 2  # Convert from [-1,1] to [0,1]

        return similarities


class ContextualLayerV2:
    """Layer 2: Contextual Analysis - Enhanced for normalized schema"""

    def __init__(self):
        self.price_indicators = {
            'luxury': ['luxury', 'exclusive', 'designer', 'elite', 'premium', 'high-end', 'expensive'],
            'high': ['premium', 'quality', 'professional', 'advanced', 'superior'],
            'medium': ['standard', 'regular', 'mid-range', 'moderate', 'typical'],
            'low': ['budget', 'cheap', 'affordable', 'low-cost', 'basic', 'economy'],
            'value': ['value', 'deal', 'discount', 'save', 'bargain']
        }

        self.product_categories = {
            'beauty': ['beauty', 'skincare', 'cosmetic', 'makeup', 'facial', 'anti-aging', 'serum'],
            'health': ['health', 'wellness', 'medical', 'fitness', 'nutrition', 'supplement'],
            'technology': ['app', 'digital', 'tech', 'software', 'platform', 'online', 'device'],
            'lifestyle': ['lifestyle', 'fashion', 'home', 'travel', 'entertainment'],
            'financial': ['investment', 'finance', 'banking', 'trading', 'insurance', 'cryptocurrency'],
            'education': ['course', 'learning', 'training', 'certification', 'education', 'skill'],
            'food': ['food', 'drink', 'coffee', 'restaurant', 'dining', 'nutrition'],
            'automotive': ['car', 'vehicle', 'automotive', 'transport', 'driving'],
            'retail': ['shopping', 'store', 'purchase', 'buy', 'retail', 'ecommerce']
        }

    def extract_context(self, query: str) -> Dict[str, Any]:
        """Extract product context from natural language query"""
        query_lower = query.lower()

        context = {
            'price_point': 'medium',  # default
            'category': 'general',
            'campaign_type': 'product_launch',
            'urgency_level': 'medium',
            'target_specificity': 'general'
        }

        # Detect price point (highest priority wins)
        price_scores = {}
        for price_level, indicators in self.price_indicators.items():
            score = sum(1 for indicator in indicators if indicator in query_lower)
            if score > 0:
                price_scores[price_level] = score

        if price_scores:
            context['price_point'] = max(price_scores, key=price_scores.get)

        # Detect product category
        for category, keywords in self.product_categories.items():
            if any(keyword in query_lower for keyword in keywords):
                context['category'] = category
                break

        # Detect target specificity
        specific_indicators = ['professional', 'expert', 'specialist', 'advanced']
        if any(indicator in query_lower for indicator in specific_indicators):
            context['target_specificity'] = 'specific'

        return context


class DomainKnowledgeLayerV2:
    """Layer 3: Domain Knowledge - Updated with normalized schema integration"""

    def __init__(self, database_connection):
        self.conn = database_connection
        self.cursor = database_connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Load category mappings from database
        self.load_category_mappings()

        # Context multipliers for different scenarios
        self.context_multipliers = {
            'price_point': {
                'luxury': {
                    'brand_preferences': 1.4,
                    'purchasing_behavior': 1.3,
                    'social_influence': 1.2,
                    'lifestyle_values': 1.1
                },
                'high': {
                    'brand_preferences': 1.2,
                    'purchasing_behavior': 1.1,
                    'social_influence': 1.1
                },
                'low': {
                    'purchasing_behavior': 0.7,
                    'convenience_usage': 1.2,
                    'brand_preferences': 0.8
                },
                'value': {
                    'purchasing_behavior': 0.6,
                    'convenience_usage': 1.3,
                    'brand_preferences': 0.7
                }
            },
            'audience_segment': {
                'Healthcare Professionals': {
                    'health_fitness': 1.3,
                    'purchasing_behavior': 1.1,
                    'brand_preferences': 1.1,
                    'technology_digital': 0.9
                },
                'University Students': {
                    'technology_digital': 1.4,
                    'purchasing_behavior': 0.7,
                    'social_influence': 1.2,
                    'convenience_usage': 1.1
                },
                'Business Leaders': {
                    'brand_preferences': 1.3,
                    'purchasing_behavior': 1.2,
                    'social_influence': 1.1,
                    'technology_digital': 1.1
                },
                'Finance Professionals': {
                    'purchasing_behavior': 1.2,
                    'brand_preferences': 1.1,
                    'technology_digital': 1.1
                }
            }
        }

    def load_category_mappings(self):
        """Load category mappings from database"""
        self.cursor.execute("""
            SELECT id, category_name, priority_level, is_core_category
            FROM trait_categories
            ORDER BY priority_level ASC
        """)

        self.categories = {}
        self.category_priorities = {}

        for row in self.cursor.fetchall():
            self.categories[row['category_name']] = row['id']
            self.category_priorities[row['category_name']] = row['priority_level']

    def get_relevance_weights(self, context: Dict[str, Any], audience_segment: str) -> Dict[str, float]:
        """Calculate relevance weights for trait categories using database patterns"""

        # Get product patterns from database
        self.cursor.execute("""
            SELECT category, relevant_trait_categories, context_multipliers
            FROM product_patterns
            WHERE %s = ANY(product_keywords) OR category = %s
            ORDER BY confidence_score DESC
            LIMIT 1
        """, (context['category'], context['category']))

        pattern = self.cursor.fetchone()

        weights = {}

        if pattern:
            # Use database pattern
            for category_id in pattern['relevant_trait_categories']:
                self.cursor.execute("""
                    SELECT category_name FROM trait_categories WHERE id = %s
                """, (category_id,))
                category_result = self.cursor.fetchone()
                if category_result:
                    weights[category_result['category_name']] = 1.0
        else:
            # Default weights for all categories
            for category_name in self.categories.keys():
                priority = self.category_priorities.get(category_name, 5)
                weights[category_name] = 1.0 / priority  # Higher priority = higher weight

        # Apply price point multipliers
        price_point = context.get('price_point', 'medium')
        if price_point in self.context_multipliers['price_point']:
            for trait_cat, multiplier in self.context_multipliers['price_point'][price_point].items():
                if trait_cat in weights:
                    weights[trait_cat] *= multiplier

        # Apply audience-specific multipliers
        if audience_segment in self.context_multipliers['audience_segment']:
            for trait_cat, multiplier in self.context_multipliers['audience_segment'][audience_segment].items():
                if trait_cat in weights:
                    weights[trait_cat] *= multiplier

        # Ensure demographic traits always have high weight
        weights['demographics'] = max(weights.get('demographics', 1.0), 0.9)

        return weights


class DynamicScoringLayerV2:
    """Layer 4: Dynamic Scoring - Updated for normalized schema"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.semantic_layer = SemanticLayerV2()
        self.contextual_layer = ContextualLayerV2()
        self.conn = None
        self.cursor = None

    def connect_db(self):
        """Connect to database"""
        try:
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(self.database_url)
                self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                print("✅ Connected to normalized database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None

    def fetch_traits_from_normalized_schema(self, audience_segment: str) -> List[Dict[str, Any]]:
        """Fetch all traits using normalized schema"""
        self.connect_db()

        # Get segment ID
        self.cursor.execute("""
            SELECT id FROM audience_segments WHERE segment_name = %s
        """, (audience_segment,))

        segment_result = self.cursor.fetchone()
        if not segment_result:
            print(f"❌ Segment not found: {audience_segment}")
            return []

        segment_id = segment_result['id']

        # Fetch traits with probabilities, categories, and embeddings
        query = """
            SELECT
                t.id,
                t.trait_text,
                t.section,
                t.source_sheet,
                t.embedding,
                tc.category_name,
                tp.probability_value,
                tp.is_demographic
            FROM traits t
            JOIN trait_categories tc ON t.category_id = tc.id
            JOIN trait_probabilities tp ON t.id = tp.trait_id
            WHERE tp.segment_id = %s
                AND tp.probability_value > 0
            ORDER BY tp.probability_value DESC
        """

        self.cursor.execute(query, (segment_id,))
        rows = self.cursor.fetchall()

        traits = []
        for row in rows:
            traits.append({
                'trait_id': row['id'],
                'trait_text': row['trait_text'],
                'section': row['section'] or 'Unknown',
                'source_sheet': row['source_sheet'],
                'category': row['category_name'],
                'probability': float(row['probability_value']),
                'is_demographic': row['is_demographic'],
                'embedding': np.array(row['embedding']) if row['embedding'] else None
            })

        print(f"   📊 Retrieved {len(traits)} traits from normalized schema")
        return traits

    def select_traits(self, query: str, audience_segment: str, max_traits: int = 60) -> Dict[str, Any]:
        """Main trait selection function using normalized schema - NO CACHING"""

        print(f"\n🚀 ENHANCED FOUR-LAYER TRAIT SELECTION v2.0 (No Caching)")
        print(f"Query: {query}")
        print(f"Segment: {audience_segment}")
        print("=" * 60)

        self.connect_db()

        # Layer 2: Extract context
        print("🔍 Layer 2: Analyzing context...")
        context = self.contextual_layer.extract_context(query)
        print(f"   Context: {context}")

        # Layer 3: Get domain knowledge weights
        print("📚 Layer 3: Applying domain knowledge...")
        domain_layer = DomainKnowledgeLayerV2(self.conn)
        category_weights = domain_layer.get_relevance_weights(context, audience_segment)
        print(f"   Category weights: {dict(list(category_weights.items())[:5])}...")

        # Fetch all traits from normalized schema
        print("💾 Fetching traits from normalized schema...")
        all_traits = self.fetch_traits_from_normalized_schema(audience_segment)

        if not all_traits:
            return {"error": "No traits found for segment"}

        # Layer 1: Calculate semantic similarities using stored embeddings
        print("🧠 Layer 1: Calculating semantic similarities...")
        valid_embeddings = []
        embedding_indices = []

        for i, trait in enumerate(all_traits):
            if trait['embedding'] is not None:
                try:
                    # Handle different embedding formats
                    if isinstance(trait['embedding'], str):
                        # Parse string representation of list
                        import ast
                        embedding_list = ast.literal_eval(trait['embedding'])
                        embedding_array = np.array(embedding_list)
                    elif isinstance(trait['embedding'], np.ndarray):
                        # Already a numpy array - check if it needs reshaping
                        embedding_array = trait['embedding']
                        # If it's a 0-dimensional array with string content, parse it
                        if embedding_array.ndim == 0:
                            import ast
                            embedding_str = str(embedding_array)
                            embedding_list = ast.literal_eval(embedding_str)
                            embedding_array = np.array(embedding_list)
                    elif isinstance(trait['embedding'], list):
                        # Direct list
                        embedding_array = np.array(trait['embedding'])
                    else:
                        # Try to convert whatever it is
                        embedding_array = np.array(trait['embedding'])

                    if embedding_array.shape == (384,):
                        valid_embeddings.append(embedding_array)
                        embedding_indices.append(i)
                except Exception as e:
                    continue

        if len(valid_embeddings) == 0:
            print("⚠️ No valid embeddings found, falling back to text similarity")
            similarities = np.ones(len(all_traits)) * 0.5  # Default similarity
        else:
            trait_embeddings = np.array(valid_embeddings)
            print(f"   Using {len(valid_embeddings)} valid embeddings (384-dim)")
            similarities_subset = self.semantic_layer.calculate_similarity(query, trait_embeddings)

            # Map similarities back to all traits
            similarities = np.ones(len(all_traits)) * 0.5  # Default for traits without embeddings
            for i, sim in enumerate(similarities_subset):
                similarities[embedding_indices[i]] = sim

        # Layer 4: Calculate final scores with semantic filtering
        print("⚡ Layer 4: Computing dynamic scores with relevance filtering...")
        scored_traits = []

        # Define minimum semantic thresholds
        MIN_SEMANTIC_THRESHOLD_CAMPAIGN_TRAITS = 0.40  # Behavioral/preference traits must be relevant
        MIN_SEMANTIC_THRESHOLD_DEMOGRAPHICS = 0.30     # Demographics (age, gender, job, etc.)

        for i, trait in enumerate(all_traits):
            semantic_score = similarities[i] if i < len(similarities) else 0.5
            category = trait['category']
            category_weight = category_weights.get(category, 0.5)

            # Apply minimum semantic threshold filtering
            # With contextual embeddings, this threshold works for ALL trait types
            min_threshold = MIN_SEMANTIC_THRESHOLD_DEMOGRAPHICS if trait['is_demographic'] else MIN_SEMANTIC_THRESHOLD_CAMPAIGN_TRAITS

            # Skip traits that are clearly irrelevant to the campaign
            if semantic_score < min_threshold:
                continue

            # Combined score: 70% semantic + 30% domain knowledge (increased semantic weight)
            final_score = (semantic_score * 0.7) + (category_weight * 0.3)

            scored_traits.append({
                'trait_id': trait['trait_id'],
                'trait_text': trait['trait_text'],
                'trait_probability': float(trait['probability']),
                'section': trait['section'],
                'source_sheet': trait['source_sheet'],
                'category': category,
                'semantic_score': float(semantic_score),
                'category_weight': float(category_weight),
                'final_score': float(final_score),
                'is_demographic': trait['is_demographic'],
                'source_type': 'normalized_enhanced_v2'
            })

        print(f"   Filtered to {len(scored_traits)} relevant traits (applied semantic threshold)")

        # Sort by final score
        scored_traits.sort(key=lambda x: x['final_score'], reverse=True)

        # Ensure balanced selection: demographics + campaign-relevant traits
        selected_traits = []
        demographic_traits = [t for t in scored_traits if t['is_demographic']]

        # Add top demographic traits (but only those that passed semantic threshold)
        max_demographics = min(8, len(demographic_traits))
        for trait in demographic_traits[:max_demographics]:
            selected_traits.append(trait)

        print(f"   Selected {len(selected_traits)} demographic traits (campaign-relevant only)")

        # Add other high-scoring traits, avoiding duplicates
        used_texts = set(t['trait_text'] for t in selected_traits)
        for trait in scored_traits:
            if len(selected_traits) >= max_traits:
                break
            if trait['trait_text'] not in used_texts:
                selected_traits.append(trait)
                used_texts.add(trait['trait_text'])

        # Calculate statistics
        avg_semantic = np.mean([t['semantic_score'] for t in selected_traits])
        avg_category_weight = np.mean([t['category_weight'] for t in selected_traits])
        avg_final_score = np.mean([t['final_score'] for t in selected_traits])

        print(f"\n📊 Selection Results:")
        print(f"   Selected: {len(selected_traits)} traits")
        print(f"   Avg Semantic Score: {avg_semantic:.3f}")
        print(f"   Avg Category Weight: {avg_category_weight:.3f}")
        print(f"   Avg Final Score: {avg_final_score:.3f}")

        # Cache results
        trait_ids = [t['trait_id'] for t in selected_traits]
        scores = {
            'avg_semantic': float(avg_semantic),
            'avg_category_weight': float(avg_category_weight),
            'avg_final_score': float(avg_final_score)
        }
        # Caching disabled - always perform fresh search

        # Build result structure
        result = {
            'analysis_metadata': {
                'target_segment': audience_segment,
                'product_query': query,
                'analysis_timestamp': datetime.now().isoformat(),
                'trait_selection_method': 'normalized_four_layer_v2',
                'total_traits_selected': len(selected_traits),
                'context_analysis': context,
                'category_weights': category_weights,
                'performance_metrics': {
                    'avg_semantic_score': float(avg_semantic),
                    'avg_category_weight': float(avg_category_weight),
                    'avg_final_score': float(avg_final_score)
                },
                'database_version': 'normalized_schema_v2'
            },
            'comprehensive_traits': selected_traits[:max_traits]
        }

        return result


def test_normalized_selector():
    """Test the enhanced trait selector with normalized schema"""

    # Test queries
    test_queries = [
        ("Premium skincare serum for Healthcare Professionals", "Healthcare Professionals"),
        ("Budget fitness app for University Students", "University Students"),
        ("Luxury investment platform for Business Leaders", "Business Leaders")
    ]

    # Initialize selector
    database_url = "postgresql://postgres:postgres@localhost:5432/synthetic_personas"

    for query, segment in test_queries:
        print(f"\n{'='*80}")
        print(f"TESTING NORMALIZED SCHEMA: {query} -> {segment}")
        print('='*80)

        selector = DynamicScoringLayerV2(database_url)

        try:
            result = selector.select_traits(query, segment, max_traits=40)

            if 'error' not in result:
                print(f"\n✅ SUCCESS: Selected {len(result['comprehensive_traits'])} traits")
                print(f"Context: {result['analysis_metadata']['context_analysis']}")
                print(f"Database Version: {result['analysis_metadata']['database_version']}")

                # Show top 10 traits
                print(f"\nTop 10 Selected Traits:")
                for i, trait in enumerate(result['comprehensive_traits'][:10]):
                    print(f"  {i+1:2d}. {trait['trait_text'][:50]:50s} | "
                          f"Score: {trait['final_score']:.3f} | "
                          f"Category: {trait['category']}")
            else:
                print(f"❌ ERROR: {result['error']}")

        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()

        finally:
            selector.close_db()

    print(f"\n{'='*80}")
    print("NORMALIZED SCHEMA TESTING COMPLETE")
    print('='*80)


if __name__ == "__main__":
    test_normalized_selector()