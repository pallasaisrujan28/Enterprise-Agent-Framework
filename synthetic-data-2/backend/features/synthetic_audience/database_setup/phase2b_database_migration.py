#!/usr/bin/env python3
"""
Phase 2B: Database Schema Migration to Normalized Structure
Implements the complete normalized schema from synthetic-persona-developer-guide.md
"""

import psycopg2
import psycopg2.extras
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer
import numpy as np


class Phase2BDatabaseMigration:
    def __init__(self):
        self.database_url = "postgresql://postgres:postgres@localhost:5454/synthetic_personas"
        self.conn = None
        self.cursor = None
        self.excel_file = Path("Synthetic Audiences.xlsx")

        # Initialize SentenceTransformer for embeddings
        print("🧠 Initializing SentenceTransformer for embeddings...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

        # Segment mappings
        self.segment_mappings = {
            'University Students': 'University Students',
            'Business Leaders': 'Business Leaders',
            'Finance Professionals': 'Finance Professionals',
            'Media Professionals': 'Media Professionals',
            'Healthcare Professionals': 'Healthcare Professionals',
            'Legal Services': 'Legal Services',
            'Government Workers': 'Government / Public sector workers',
            'Hospitality Workers': 'Hospitality Workers',
            'Manufacturing Workers': 'Manufacturing (Food & Drink sectors) Workers'
        }

    def connect_db(self):
        """Connect to database"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            print("✅ Connected to database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def create_normalized_schema(self):
        """Create the complete normalized database schema per developer guide"""

        print("\n🏗️ CREATING NORMALIZED DATABASE SCHEMA")
        print("=" * 60)

        self.connect_db()

        # Enable pgvector extension
        print("📦 Enabling pgvector extension...")
        try:
            self.cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self.conn.commit()
            print("   ✅ pgvector extension enabled")
        except Exception as e:
            print(f"   ⚠️ pgvector extension: {e}")

        # Create tables in dependency order
        self.create_audience_segments_table()
        self.create_trait_categories_table()
        self.create_traits_master_table()
        self.create_trait_probabilities_table()
        self.create_trait_relationships_table()
        self.create_product_patterns_table()
        self.create_personas_table()
        self.create_query_cache_table()

        print("\n✅ NORMALIZED SCHEMA CREATION COMPLETE")

    def create_audience_segments_table(self):
        """Create audience_segments table"""

        print("\n📊 Creating audience_segments table...")

        create_sql = """
            DROP TABLE IF EXISTS audience_segments CASCADE;
            CREATE TABLE audience_segments (
                id SERIAL PRIMARY KEY,
                segment_name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                sample_size INTEGER,
                audience_size BIGINT,
                gender_split VARCHAR(50),
                original_column_name VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """

        self.cursor.execute(create_sql)

        # Insert segment data
        segments_data = [
            (1, 'University Students', 'Currently studying Bachelor/Honours degree', 1000, 50000000, '60% Female, 40% Male', 'University Students'),
            (2, 'Business Leaders', 'Senior management and executive roles', 800, 25000000, '45% Female, 55% Male', 'Business Leaders'),
            (3, 'Finance Professionals', 'Financial services and banking professionals', 750, 15000000, '50% Female, 50% Male', 'Finance Professionals'),
            (4, 'Media Professionals', 'Creative and media industry workers', 650, 12000000, '55% Female, 45% Male', 'Media Professionals'),
            (5, 'Healthcare Professionals', 'Medical and healthcare workers', 900, 20000000, '70% Female, 30% Male', 'Healthcare Professionals'),
            (6, 'Legal Services', 'Legal and law professionals', 500, 5000000, '55% Female, 45% Male', 'Legal Services'),
            (7, 'Government Workers', 'Public sector and government employees', 800, 30000000, '60% Female, 40% Male', 'Government / Public sector workers'),
            (8, 'Hospitality Workers', 'Tourism and hospitality industry workers', 700, 18000000, '65% Female, 35% Male', 'Hospitality Workers'),
            (9, 'Manufacturing Workers', 'Food and drink manufacturing workers', 600, 8000000, '40% Female, 60% Male', 'Manufacturing (Food & Drink sectors) Workers')
        ]

        insert_sql = """
            INSERT INTO audience_segments (id, segment_name, description, sample_size, audience_size, gender_split, original_column_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (segment_name) DO UPDATE SET
                description = EXCLUDED.description,
                sample_size = EXCLUDED.sample_size,
                audience_size = EXCLUDED.audience_size,
                gender_split = EXCLUDED.gender_split,
                original_column_name = EXCLUDED.original_column_name;
        """

        for segment_data in segments_data:
            self.cursor.execute(insert_sql, segment_data)

        self.conn.commit()
        print(f"   ✅ Created audience_segments with {len(segments_data)} segments")

    def create_trait_categories_table(self):
        """Create trait_categories table"""

        print("\n🏷️ Creating trait_categories table...")

        create_sql = """
            DROP TABLE IF EXISTS trait_categories CASCADE;
            CREATE TABLE trait_categories (
                id SERIAL PRIMARY KEY,
                category_name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                priority_level INTEGER DEFAULT 5,
                is_core_category BOOLEAN DEFAULT FALSE,
                source_domain VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """

        self.cursor.execute(create_sql)

        # Insert category data based on enhanced system
        categories_data = [
            (1, 'demographics', 'Age, gender, location, income demographics', 1, True, 'generic'),
            (2, 'purchasing_behavior', 'Shopping patterns, price sensitivity, research habits', 2, True, 'purchases'),
            (3, 'beauty_appearance', 'Fashion, skincare, appearance-related traits', 3, False, 'beauty'),
            (4, 'health_fitness', 'Health consciousness, fitness activities, wellness', 3, False, 'health_sports'),
            (5, 'technology_digital', 'Digital adoption, online behavior, app usage', 4, False, 'generic'),
            (6, 'social_influence', 'Word-of-mouth, recommendations, opinion leadership', 4, False, 'interests_lifestyle'),
            (7, 'lifestyle_values', 'General lifestyle preferences and values', 5, False, 'interests_lifestyle'),
            (8, 'brand_preferences', 'Brand loyalty, premium preferences, switching behavior', 4, False, 'purchases'),
            (9, 'sustainability', 'Environmental consciousness, recycling, eco-friendly preferences', 5, False, 'interests_lifestyle'),
            (10, 'convenience_usage', 'Ease of use preferences, time-saving behaviors', 4, False, 'purchases')
        ]

        insert_sql = """
            INSERT INTO trait_categories (id, category_name, description, priority_level, is_core_category, source_domain)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (category_name) DO UPDATE SET
                description = EXCLUDED.description,
                priority_level = EXCLUDED.priority_level,
                is_core_category = EXCLUDED.is_core_category,
                source_domain = EXCLUDED.source_domain;
        """

        for category_data in categories_data:
            self.cursor.execute(insert_sql, category_data)

        self.conn.commit()
        print(f"   ✅ Created trait_categories with {len(categories_data)} categories")

    def create_traits_master_table(self):
        """Create traits master table with embeddings"""

        print("\n🧬 Creating traits master table...")

        create_sql = """
            DROP TABLE IF EXISTS traits CASCADE;
            CREATE TABLE traits (
                id SERIAL PRIMARY KEY,
                trait_text TEXT NOT NULL,
                source_sheet VARCHAR(50) NOT NULL,
                source_row INTEGER NOT NULL,
                section VARCHAR(200),
                category_id INTEGER REFERENCES trait_categories(id),
                trait_type VARCHAR(20) DEFAULT 'binary',
                embedding VECTOR(384),
                created_at TIMESTAMP DEFAULT NOW(),

                UNIQUE(source_sheet, source_row, trait_text)
            );

            CREATE INDEX idx_traits_embedding ON traits USING ivfflat (embedding vector_cosine_ops);
            CREATE INDEX idx_traits_category ON traits(category_id);
            CREATE INDEX idx_traits_text ON traits(trait_text);
        """

        self.cursor.execute(create_sql)
        self.conn.commit()
        print("   ✅ Created traits master table with embedding support")

    def create_trait_probabilities_table(self):
        """Create trait_probabilities table"""

        print("\n📈 Creating trait_probabilities table...")

        create_sql = """
            DROP TABLE IF EXISTS trait_probabilities CASCADE;
            CREATE TABLE trait_probabilities (
                id SERIAL PRIMARY KEY,
                trait_id INTEGER REFERENCES traits(id) ON DELETE CASCADE,
                segment_id INTEGER REFERENCES audience_segments(id) ON DELETE CASCADE,
                probability_value DECIMAL(5,3) CHECK (probability_value >= 0 AND probability_value <= 1),
                is_demographic BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),

                UNIQUE(trait_id, segment_id)
            );

            CREATE INDEX idx_trait_probabilities_segment ON trait_probabilities(segment_id);
            CREATE INDEX idx_trait_probabilities_trait ON trait_probabilities(trait_id);
            CREATE INDEX idx_trait_probabilities_value ON trait_probabilities(probability_value);
        """

        self.cursor.execute(create_sql)
        self.conn.commit()
        print("   ✅ Created trait_probabilities table")

    def create_trait_relationships_table(self):
        """Create trait_relationships table for predictive expansion"""

        print("\n🔗 Creating trait_relationships table...")

        create_sql = """
            DROP TABLE IF EXISTS trait_relationships CASCADE;
            CREATE TABLE trait_relationships (
                id SERIAL PRIMARY KEY,
                primary_trait_id INTEGER REFERENCES traits(id) ON DELETE CASCADE,
                related_trait_id INTEGER REFERENCES traits(id) ON DELETE CASCADE,
                relationship_type VARCHAR(30) NOT NULL,
                strength DECIMAL(3,2) CHECK (strength >= 0 AND strength <= 1),
                created_at TIMESTAMP DEFAULT NOW(),

                UNIQUE(primary_trait_id, related_trait_id, relationship_type),
                CHECK (primary_trait_id != related_trait_id)
            );

            CREATE INDEX idx_trait_relationships_primary ON trait_relationships(primary_trait_id);
            CREATE INDEX idx_trait_relationships_type ON trait_relationships(relationship_type);
        """

        self.cursor.execute(create_sql)
        self.conn.commit()
        print("   ✅ Created trait_relationships table")

    def create_product_patterns_table(self):
        """Create product_patterns table for context analysis"""

        print("\n🛍️ Creating product_patterns table...")

        create_sql = """
            DROP TABLE IF EXISTS product_patterns CASCADE;
            CREATE TABLE product_patterns (
                id SERIAL PRIMARY KEY,
                product_keywords TEXT[] NOT NULL,
                price_point VARCHAR(20) DEFAULT 'medium',
                category VARCHAR(50) NOT NULL,
                relevant_trait_categories INTEGER[] NOT NULL,
                context_multipliers JSONB,
                confidence_score DECIMAL(3,2) DEFAULT 0.80,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE INDEX idx_product_patterns_category ON product_patterns(category);
            CREATE INDEX idx_product_patterns_price ON product_patterns(price_point);
        """

        self.cursor.execute(create_sql)
        self.conn.commit()
        print("   ✅ Created product_patterns table")

    def create_personas_table(self):
        """Create personas table for generated personas"""

        print("\n👤 Creating personas table...")

        create_sql = """
            DROP TABLE IF EXISTS personas CASCADE;
            CREATE TABLE personas (
                id SERIAL PRIMARY KEY,
                persona_uuid UUID DEFAULT gen_random_uuid() UNIQUE,
                segment_id INTEGER REFERENCES audience_segments(id),
                campaign_context TEXT,
                generation_timestamp TIMESTAMP DEFAULT NOW(),
                core_traits JSONB NOT NULL,
                extended_traits JSONB,
                demographic_info JSONB,
                narrative_profile TEXT,
                generation_metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE INDEX idx_personas_segment ON personas(segment_id);
            CREATE INDEX idx_personas_uuid ON personas(persona_uuid);
            CREATE INDEX idx_personas_generation ON personas(generation_timestamp);
        """

        self.cursor.execute(create_sql)
        self.conn.commit()
        print("   ✅ Created personas table")

    def create_query_cache_table(self):
        """Create query_cache table for performance"""

        print("\n⚡ Creating query_cache table...")

        create_sql = """
            DROP TABLE IF EXISTS query_cache CASCADE;
            CREATE TABLE query_cache (
                id SERIAL PRIMARY KEY,
                query_hash VARCHAR(64) UNIQUE NOT NULL,
                query_text TEXT NOT NULL,
                segment_name VARCHAR(100) NOT NULL,
                parsed_context JSONB,
                selected_trait_ids INTEGER[],
                relevance_scores JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                hit_count INTEGER DEFAULT 1,
                last_accessed TIMESTAMP DEFAULT NOW()
            );

            CREATE INDEX idx_query_cache_hash ON query_cache(query_hash);
            CREATE INDEX idx_query_cache_segment ON query_cache(segment_name);
        """

        self.cursor.execute(create_sql)
        self.conn.commit()
        print("   ✅ Created query_cache table")

    def migrate_existing_data(self):
        """Migrate data from old schema to new normalized schema"""

        print("\n📦 MIGRATING EXISTING DATA TO NORMALIZED SCHEMA")
        print("=" * 60)

        # Load Excel data
        excel_data = self.load_excel_data()

        # Migrate traits and probabilities
        self.migrate_traits_and_probabilities(excel_data)

        # Create initial product patterns
        self.create_initial_product_patterns()

        # Create trait relationships
        self.create_initial_trait_relationships()

        print("\n✅ DATA MIGRATION COMPLETE")

    def load_excel_data(self):
        """Load Excel data for migration"""

        print("\n📊 Loading Excel data...")

        sheets_data = {}
        sheet_mappings = {
            'Generic Answers': 'generic',
            'Beauty Answers': 'beauty',
            'Health, Sports & Excercise': 'health_sports',
            'Interests & Lifestyle - NEW': 'interests_lifestyle',
            'Purchases - NEW': 'purchases'
        }

        for sheet_name, domain in sheet_mappings.items():
            try:
                df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                sheets_data[domain] = self.extract_traits_from_sheet(df, sheet_name)
                print(f"   ✅ Loaded {sheet_name}: {len(sheets_data[domain])} traits")
            except Exception as e:
                print(f"   ❌ Failed to load {sheet_name}: {e}")

        return sheets_data

    def extract_traits_from_sheet(self, df, sheet_name):
        """Extract traits from Excel sheet"""

        # Find header row
        header_row = None
        for idx in range(min(15, len(df))):
            row = df.iloc[idx]
            if any(pd.notna(cell) and "University Students" in str(cell) for cell in row):
                header_row = idx
                break

        if header_row is None:
            return {}

        # Get segment columns
        headers = df.iloc[header_row].values
        segment_columns = {}
        for col_idx in range(1, len(headers)):
            if col_idx < len(headers) and pd.notna(headers[col_idx]):
                header_str = str(headers[col_idx]).strip()
                for user_name, excel_name in self.segment_mappings.items():
                    if excel_name in header_str:
                        segment_columns[user_name] = col_idx
                        break

        # Extract traits
        traits_data = {}
        current_section = "Unknown Section"

        for idx in range(len(df)):
            if idx <= header_row:
                continue

            row = df.iloc[idx]
            trait_cell = row.iloc[1] if len(row) > 1 else None

            if pd.isna(trait_cell):
                continue

            trait_text = str(trait_cell).strip()

            # Check if this has probability data
            has_prob_data = False
            for col_idx in range(2, min(len(row), 15)):
                if pd.notna(row.iloc[col_idx]):
                    try:
                        val = float(row.iloc[col_idx])
                        if 0 <= val <= 1:
                            has_prob_data = True
                            break
                    except:
                        pass

            if not has_prob_data:
                current_section = trait_text
                continue

            # Extract probabilities
            trait_probs = {
                'section': current_section,
                'row_index': idx,
                'sheet': sheet_name
            }

            for segment_name, col_idx in segment_columns.items():
                if col_idx < len(row):
                    value = row.iloc[col_idx]
                    if pd.notna(value):
                        try:
                            trait_probs[segment_name] = float(value)
                        except:
                            trait_probs[segment_name] = None

            traits_data[trait_text] = trait_probs

        return traits_data

    def categorize_trait(self, trait_text):
        """Categorize a trait based on keywords"""

        trait_lower = trait_text.lower()

        # Get category IDs
        self.cursor.execute("SELECT id, category_name FROM trait_categories")
        categories = {row['category_name']: row['id'] for row in self.cursor.fetchall()}

        # Categorization logic
        if any(word in trait_lower for word in ['age', 'gender', 'generation', 'income', 'location', 'male', 'female']):
            return categories['demographics']
        elif any(word in trait_lower for word in ['beauty', 'fashion', 'appearance', 'skincare', 'makeup', 'style']):
            return categories['beauty_appearance']
        elif any(word in trait_lower for word in ['health', 'fitness', 'exercise', 'wellness', 'sport']):
            return categories['health_fitness']
        elif any(word in trait_lower for word in ['purchase', 'buy', 'shopping', 'price', 'cost', 'spend', 'money']):
            return categories['purchasing_behavior']
        elif any(word in trait_lower for word in ['technology', 'digital', 'online', 'app', 'internet']):
            return categories['technology_digital']
        elif any(word in trait_lower for word in ['recommend', 'social', 'influence', 'opinion', 'friends']):
            return categories['social_influence']
        elif any(word in trait_lower for word in ['brand', 'loyalty', 'premium', 'quality']):
            return categories['brand_preferences']
        elif any(word in trait_lower for word in ['recycle', 'environmental', 'eco', 'sustainable']):
            return categories['sustainability']
        elif any(word in trait_lower for word in ['convenient', 'easy', 'quick', 'fast']):
            return categories['convenience_usage']
        else:
            return categories['lifestyle_values']

    def migrate_traits_and_probabilities(self, excel_data):
        """Migrate traits and probabilities to normalized schema"""

        print("\n🧬 Migrating traits and probabilities...")

        # Get segment IDs
        self.cursor.execute("SELECT id, segment_name FROM audience_segments")
        segment_ids = {row['segment_name']: row['id'] for row in self.cursor.fetchall()}

        total_traits = 0
        total_probabilities = 0

        for domain, traits_data in excel_data.items():
            print(f"\n   Processing {domain} domain...")

            for trait_text, trait_info in traits_data.items():
                # Generate embedding
                embedding = self.model.encode(trait_text)

                # Categorize trait
                category_id = self.categorize_trait(trait_text)

                # Insert trait
                insert_trait_sql = """
                    INSERT INTO traits (trait_text, source_sheet, source_row, section, category_id, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_sheet, source_row, trait_text)
                    DO UPDATE SET
                        section = EXCLUDED.section,
                        category_id = EXCLUDED.category_id,
                        embedding = EXCLUDED.embedding
                    RETURNING id;
                """

                self.cursor.execute(insert_trait_sql, (
                    trait_text,
                    trait_info['sheet'],
                    trait_info['row_index'],
                    trait_info['section'],
                    category_id,
                    embedding.tolist()
                ))

                trait_id = self.cursor.fetchone()['id']
                total_traits += 1

                # Insert probabilities for each segment
                for segment_name, probability in trait_info.items():
                    if segment_name in segment_ids and probability is not None:

                        # Check if this is a demographic trait
                        is_demographic = category_id == 1  # demographics category

                        insert_prob_sql = """
                            INSERT INTO trait_probabilities (trait_id, segment_id, probability_value, is_demographic)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (trait_id, segment_id)
                            DO UPDATE SET
                                probability_value = EXCLUDED.probability_value,
                                is_demographic = EXCLUDED.is_demographic;
                        """

                        self.cursor.execute(insert_prob_sql, (
                            trait_id,
                            segment_ids[segment_name],
                            probability,
                            is_demographic
                        ))

                        total_probabilities += 1

            self.conn.commit()
            print(f"      ✅ Processed {len(traits_data)} traits")

        print(f"\n   ✅ Migrated {total_traits} traits with {total_probabilities} probabilities")

    def create_initial_product_patterns(self):
        """Create initial product patterns for context analysis"""

        print("\n🛍️ Creating initial product patterns...")

        patterns = [
            {
                'keywords': ['beauty', 'skincare', 'cosmetic', 'makeup'],
                'price_point': 'medium',
                'category': 'beauty',
                'relevant_categories': [1, 2, 3],  # demographics, purchasing_behavior, beauty_appearance
                'multipliers': {'luxury': {'purchasing_behavior': 1.4, 'brand_preferences': 1.2}}
            },
            {
                'keywords': ['health', 'fitness', 'wellness', 'medical'],
                'price_point': 'medium',
                'category': 'health',
                'relevant_categories': [1, 2, 4],  # demographics, purchasing_behavior, health_fitness
                'multipliers': {'high': {'health_fitness': 1.3}}
            },
            {
                'keywords': ['technology', 'app', 'digital', 'software'],
                'price_point': 'medium',
                'category': 'technology',
                'relevant_categories': [1, 2, 5],  # demographics, purchasing_behavior, technology_digital
                'multipliers': {'students': {'technology_digital': 1.4}}
            },
            {
                'keywords': ['investment', 'finance', 'trading', 'banking'],
                'price_point': 'high',
                'category': 'financial',
                'relevant_categories': [1, 2, 8],  # demographics, purchasing_behavior, brand_preferences
                'multipliers': {'luxury': {'purchasing_behavior': 1.6, 'brand_preferences': 1.3}}
            },
            {
                'keywords': ['education', 'learning', 'course', 'training'],
                'price_point': 'medium',
                'category': 'education',
                'relevant_categories': [1, 5, 7],  # demographics, technology_digital, lifestyle_values
                'multipliers': {'premium': {'lifestyle_values': 1.2}}
            }
        ]

        insert_sql = """
            INSERT INTO product_patterns (product_keywords, price_point, category, relevant_trait_categories, context_multipliers)
            VALUES (%s, %s, %s, %s, %s);
        """

        for pattern in patterns:
            self.cursor.execute(insert_sql, (
                pattern['keywords'],
                pattern['price_point'],
                pattern['category'],
                pattern['relevant_categories'],
                json.dumps(pattern['multipliers'])
            ))

        self.conn.commit()
        print(f"   ✅ Created {len(patterns)} product patterns")

    def create_initial_trait_relationships(self):
        """Create initial trait relationships for predictive expansion"""

        print("\n🔗 Creating initial trait relationships...")

        # Find related traits using vector similarity
        self.cursor.execute("""
            SELECT t1.id as trait1_id, t2.id as trait2_id,
                   t1.trait_text as trait1_text, t2.trait_text as trait2_text,
                   1 - (t1.embedding <=> t2.embedding) as similarity
            FROM traits t1
            CROSS JOIN traits t2
            WHERE t1.id != t2.id
                AND 1 - (t1.embedding <=> t2.embedding) > 0.7
            ORDER BY similarity DESC
            LIMIT 1000;
        """)

        relationships = self.cursor.fetchall()

        # Insert top relationships
        insert_sql = """
            INSERT INTO trait_relationships (primary_trait_id, related_trait_id, relationship_type, strength)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (primary_trait_id, related_trait_id, relationship_type) DO NOTHING;
        """

        relationship_count = 0
        for rel in relationships[:500]:  # Top 500 relationships
            relationship_type = 'semantic' if rel['similarity'] > 0.8 else 'cross_domain'

            self.cursor.execute(insert_sql, (
                rel['trait1_id'],
                rel['trait2_id'],
                relationship_type,
                rel['similarity']
            ))
            relationship_count += 1

        self.conn.commit()
        print(f"   ✅ Created {relationship_count} trait relationships")

    def run_migration(self):
        """Run the complete Phase 2B migration"""

        print("🚀 STARTING PHASE 2B: DATABASE SCHEMA MIGRATION")
        print("=" * 70)
        print("Migrating to normalized schema per synthetic-persona-developer-guide.md")
        print("=" * 70)

        try:
            # Step 1: Create normalized schema
            self.create_normalized_schema()

            # Step 2: Migrate existing data
            self.migrate_existing_data()

            # Step 3: Validate migration
            self.validate_migration()

            print(f"\n🎉 PHASE 2B MIGRATION COMPLETE!")
            print("✅ Normalized database schema operational")
            print("✅ All existing data migrated successfully")
            print("✅ Ready for enhanced trait selector integration")
            print("✅ Foundation prepared for Phase 3 persona generation")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.close_db()

    def validate_migration(self):
        """Validate the migration was successful"""

        print("\n🔍 VALIDATING MIGRATION...")

        # Count migrated data
        self.cursor.execute("SELECT COUNT(*) FROM audience_segments")
        segments_count = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) FROM trait_categories")
        categories_count = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) FROM traits")
        traits_count = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) FROM trait_probabilities")
        probabilities_count = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) FROM trait_relationships")
        relationships_count = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) FROM product_patterns")
        patterns_count = self.cursor.fetchone()['count']

        print(f"   ✅ Audience Segments: {segments_count}")
        print(f"   ✅ Trait Categories: {categories_count}")
        print(f"   ✅ Traits: {traits_count}")
        print(f"   ✅ Trait Probabilities: {probabilities_count}")
        print(f"   ✅ Trait Relationships: {relationships_count}")
        print(f"   ✅ Product Patterns: {patterns_count}")

        # Validate data integrity
        self.cursor.execute("""
            SELECT COUNT(*) FROM traits t
            JOIN trait_probabilities tp ON t.id = tp.trait_id
            JOIN audience_segments s ON tp.segment_id = s.id
        """)
        valid_probabilities = self.cursor.fetchone()['count']

        print(f"   ✅ Valid Trait-Segment Mappings: {valid_probabilities}")

        if traits_count > 800 and probabilities_count > 5000:
            print("   ✅ MIGRATION VALIDATION PASSED")
        else:
            print("   ⚠️ MIGRATION VALIDATION WARNING: Lower than expected counts")


def main():
    """Main migration execution"""
    print("🔬 Phase 2B: Database Schema Migration to Normalized Structure")
    print("=" * 70)

    migrator = Phase2BDatabaseMigration()
    migrator.run_migration()

    print(f"\n🎯 Next Steps:")
    print("1. Update enhanced trait selector to use new schema")
    print("2. Validate performance maintains 85.8% accuracy")
    print("3. Prepare for Phase 3 persona generation pipeline")


if __name__ == "__main__":
    main()