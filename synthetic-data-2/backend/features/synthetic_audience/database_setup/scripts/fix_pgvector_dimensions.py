#!/usr/bin/env python3
"""
Fix pgvector Dimensions - Create Dynamic Vector Tables
"""

import psycopg2
import psycopg2.extras
import numpy as np

class PgVectorFixer:
    def __init__(self, database_url: str = "postgresql://postgres:postgres@localhost:5432/synthetic_personas"):
        self.database_url = database_url
        self.conn = None
        self.cursor = None

    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            print("✅ Connected to database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    def drop_and_recreate_vector_tables(self):
        """Drop old tables and create new ones with correct dimensions"""
        print("🔧 Recreating Vector Tables with Correct Dimensions")
        print("-" * 50)

        # Drop existing tables
        drop_sql = """
        DROP TABLE IF EXISTS segment_vectors CASCADE;
        DROP TABLE IF EXISTS trait_vectors CASCADE;
        """

        try:
            self.cursor.execute(drop_sql)
            self.conn.commit()
            print("✅ Dropped old vector tables")
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            raise

        # Create new segment_vectors table with flexible dimensions
        segment_vectors_sql = """
        CREATE TABLE segment_vectors (
            vector_id SERIAL PRIMARY KEY,
            segment_id INTEGER NOT NULL REFERENCES audience_segments(segment_id),
            segment_name VARCHAR(200) NOT NULL,
            domain VARCHAR(50) NOT NULL,
            vector_type VARCHAR(50) NOT NULL,
            vector_dimensions INTEGER NOT NULL,
            trait_vector TEXT NOT NULL, -- Store as text, convert to vector on query
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(segment_id, domain, vector_type)
        );

        CREATE INDEX idx_segment_vectors_segment_id ON segment_vectors(segment_id);
        CREATE INDEX idx_segment_vectors_domain ON segment_vectors(domain);
        CREATE INDEX idx_segment_vectors_type ON segment_vectors(vector_type);

        COMMENT ON TABLE segment_vectors IS 'pgvector embeddings for audience segments with flexible dimensions';
        """

        # Create new trait_vectors table (9 dimensions for segments)
        trait_vectors_sql = """
        CREATE TABLE trait_vectors (
            vector_id SERIAL PRIMARY KEY,
            trait_text VARCHAR(500) NOT NULL,
            domain VARCHAR(50) NOT NULL,
            section VARCHAR(200),
            segment_probabilities vector(9), -- Fixed 9 segments
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(trait_text, domain)
        );

        CREATE INDEX idx_trait_vectors_domain ON trait_vectors(domain);
        CREATE INDEX idx_trait_vectors_section ON trait_vectors(section);
        CREATE INDEX idx_trait_vectors_similarity ON trait_vectors USING ivfflat (segment_probabilities vector_cosine_ops);

        COMMENT ON TABLE trait_vectors IS 'pgvector embeddings for traits showing segment probability patterns';
        """

        try:
            self.cursor.execute(segment_vectors_sql)
            self.cursor.execute(trait_vectors_sql)
            self.conn.commit()
            print("✅ Created new vector tables with correct dimensions")
        except Exception as e:
            print(f"❌ Error creating vector tables: {e}")
            self.conn.rollback()
            raise

    def generate_segment_vectors_fixed(self, domain: str, table_name: str):
        """Generate segment vectors with correct dimensions"""
        print(f"🔢 Generating {domain} segment vectors (fixed)...")

        # Get traits count for this domain
        self.cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        trait_count = self.cursor.fetchone()['count']
        print(f"  📊 Domain has {trait_count} traits")

        # Get all traits for this domain
        self.cursor.execute(f"""
            SELECT trait_text, section,
                   university_students, business_leaders, finance_professionals,
                   legal_services, media_professionals, healthcare_professionals,
                   government_workers, hospitality_workers,
                   manufacturing_food_and_drink_sectors_workers
            FROM {table_name}
            ORDER BY trait_text
        """)

        traits = self.cursor.fetchall()

        # Get segments
        self.cursor.execute("SELECT segment_id, segment_name FROM audience_segments ORDER BY segment_id")
        segments = self.cursor.fetchall()

        # Segment name to column mapping
        segment_mapping = {
            'University Students': 'university_students',
            'Business Leaders': 'business_leaders',
            'Finance Professionals': 'finance_professionals',
            'Legal Services': 'legal_services',
            'Media Professionals': 'media_professionals',
            'Healthcare Professionals': 'healthcare_professionals',
            'Government / Public sector workers': 'government_workers',
            'Hospitality Workers': 'hospitality_workers',
            'Manufacturing Workers (Food & Drink sectors)': 'manufacturing_food_and_drink_sectors_workers'
        }

        vectors_created = 0
        for segment in segments:
            segment_id = segment['segment_id']
            segment_name = segment['segment_name']

            if segment_name not in segment_mapping:
                print(f"  ⚠️  No mapping for segment: {segment_name}")
                continue

            segment_column = segment_mapping[segment_name]

            # Extract vector values for this segment
            vector_values = []
            for trait in traits:
                value = trait[segment_column]
                if value is not None:
                    vector_values.append(float(value))
                else:
                    vector_values.append(0.0)

            # Store as text representation
            vector_str = '[' + ','.join(map(str, vector_values)) + ']'

            try:
                insert_sql = """
                    INSERT INTO segment_vectors (segment_id, segment_name, domain, vector_type, vector_dimensions, trait_vector)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (segment_id, domain, vector_type)
                    DO UPDATE SET
                        vector_dimensions = EXCLUDED.vector_dimensions,
                        trait_vector = EXCLUDED.trait_vector
                """

                self.cursor.execute(insert_sql, (
                    segment_id, segment_name, domain, 'trait_probabilities', trait_count, vector_str
                ))
                vectors_created += 1

            except Exception as e:
                print(f"  ❌ Error creating vector for {segment_name}: {e}")

        self.conn.commit()
        print(f"  ✅ Created {vectors_created} segment vectors for {domain}")

    def generate_trait_vectors_fixed(self, domain: str, table_name: str):
        """Generate trait vectors (fixed 9 dimensions for segments)"""
        print(f"📋 Generating {domain} trait vectors (fixed)...")

        # Get all traits for this domain
        self.cursor.execute(f"""
            SELECT trait_text, section,
                   university_students, business_leaders, finance_professionals,
                   legal_services, media_professionals, healthcare_professionals,
                   government_workers, hospitality_workers,
                   manufacturing_food_and_drink_sectors_workers
            FROM {table_name}
            ORDER BY trait_text
        """)

        traits = self.cursor.fetchall()

        segment_columns = [
            'university_students', 'business_leaders', 'finance_professionals',
            'legal_services', 'media_professionals', 'healthcare_professionals',
            'government_workers', 'hospitality_workers', 'manufacturing_food_and_drink_sectors_workers'
        ]

        vectors_created = 0
        for trait in traits:
            trait_text = trait['trait_text']
            section = trait['section']

            # Create vector from segment probabilities (9 dimensions)
            vector_values = []
            for col in segment_columns:
                value = trait[col]
                if value is not None:
                    vector_values.append(float(value))
                else:
                    vector_values.append(0.0)

            # Convert to postgres vector format
            vector_str = '[' + ','.join(map(str, vector_values)) + ']'

            try:
                insert_sql = """
                    INSERT INTO trait_vectors (trait_text, domain, section, segment_probabilities)
                    VALUES (%s, %s, %s, %s::vector)
                    ON CONFLICT (trait_text, domain)
                    DO UPDATE SET segment_probabilities = EXCLUDED.segment_probabilities
                """

                self.cursor.execute(insert_sql, (trait_text, domain, section, vector_str))
                vectors_created += 1

            except Exception as e:
                print(f"  ❌ Error creating vector for '{trait_text}': {e}")

        self.conn.commit()
        print(f"  ✅ Created {vectors_created} trait vectors for {domain}")

    def create_vector_similarity_functions(self):
        """Create similarity functions that work with flexible dimensions"""
        print("\n🔍 Creating Vector Similarity Functions")
        print("-" * 40)

        functions_sql = """
        -- Function to calculate cosine similarity between two text vectors
        CREATE OR REPLACE FUNCTION text_vector_similarity(vec1 TEXT, vec2 TEXT)
        RETURNS FLOAT AS $$
        DECLARE
            arr1 FLOAT[];
            arr2 FLOAT[];
            dot_product FLOAT := 0;
            norm1 FLOAT := 0;
            norm2 FLOAT := 0;
            i INTEGER;
        BEGIN
            -- Parse text vectors to arrays
            arr1 := string_to_array(trim(both '[]' from vec1), ',')::FLOAT[];
            arr2 := string_to_array(trim(both '[]' from vec2), ',')::FLOAT[];

            -- Check if arrays have same length
            IF array_length(arr1, 1) != array_length(arr2, 1) THEN
                RETURN 0;
            END IF;

            -- Calculate dot product and norms
            FOR i IN 1..array_length(arr1, 1) LOOP
                dot_product := dot_product + (arr1[i] * arr2[i]);
                norm1 := norm1 + (arr1[i] * arr1[i]);
                norm2 := norm2 + (arr2[i] * arr2[i]);
            END LOOP;

            -- Calculate cosine similarity
            IF norm1 = 0 OR norm2 = 0 THEN
                RETURN 0;
            END IF;

            RETURN dot_product / (sqrt(norm1) * sqrt(norm2));
        END;
        $$ LANGUAGE plpgsql;

        -- Function to find similar segments within a domain
        CREATE OR REPLACE FUNCTION find_similar_segments_in_domain(
            target_segment_name TEXT,
            target_domain TEXT,
            similarity_threshold FLOAT DEFAULT 0.8,
            limit_results INT DEFAULT 5
        )
        RETURNS TABLE(
            segment_name TEXT,
            domain TEXT,
            similarity_score FLOAT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                sv2.segment_name::TEXT,
                sv2.domain::TEXT,
                text_vector_similarity(sv1.trait_vector, sv2.trait_vector) as similarity_score
            FROM segment_vectors sv1
            JOIN segment_vectors sv2 ON sv1.domain = sv2.domain
                AND sv1.vector_type = sv2.vector_type
            WHERE sv1.segment_name = target_segment_name
                AND sv1.domain = target_domain
                AND sv2.segment_name != target_segment_name
                AND text_vector_similarity(sv1.trait_vector, sv2.trait_vector) >= similarity_threshold
            ORDER BY similarity_score DESC
            LIMIT limit_results;
        END;
        $$ LANGUAGE plpgsql;

        -- Function to find similar traits using pgvector
        CREATE OR REPLACE FUNCTION find_similar_traits_vector(
            target_trait_text TEXT,
            target_domain TEXT,
            similarity_threshold FLOAT DEFAULT 0.7,
            limit_results INT DEFAULT 10
        )
        RETURNS TABLE(
            trait_text TEXT,
            domain TEXT,
            section TEXT,
            similarity_score FLOAT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                tv2.trait_text::TEXT,
                tv2.domain::TEXT,
                tv2.section::TEXT,
                (1 - (tv1.segment_probabilities <=> tv2.segment_probabilities))::FLOAT as similarity_score
            FROM trait_vectors tv1
            JOIN trait_vectors tv2 ON tv1.domain = tv2.domain
            WHERE tv1.trait_text = target_trait_text
                AND tv1.domain = target_domain
                AND tv2.trait_text != target_trait_text
                AND (1 - (tv1.segment_probabilities <=> tv2.segment_probabilities)) >= similarity_threshold
            ORDER BY similarity_score DESC
            LIMIT limit_results;
        END;
        $$ LANGUAGE plpgsql;

        -- Function to find distinguishing traits for a segment
        CREATE OR REPLACE FUNCTION find_segment_distinguishing_traits(
            target_segment_name TEXT,
            target_domain TEXT,
            min_probability FLOAT DEFAULT 0.5,
            limit_results INT DEFAULT 15
        )
        RETURNS TABLE(
            trait_text TEXT,
            section TEXT,
            segment_probability FLOAT,
            rank_in_segment INTEGER
        ) AS $$
        DECLARE
            segment_index INTEGER;
        BEGIN
            -- Map segment name to array index (1-based)
            segment_index := CASE target_segment_name
                WHEN 'University Students' THEN 1
                WHEN 'Business Leaders' THEN 2
                WHEN 'Finance Professionals' THEN 3
                WHEN 'Legal Services' THEN 4
                WHEN 'Media Professionals' THEN 5
                WHEN 'Healthcare Professionals' THEN 6
                WHEN 'Government / Public sector workers' THEN 7
                WHEN 'Hospitality Workers' THEN 8
                WHEN 'Manufacturing Workers (Food & Drink sectors)' THEN 9
                ELSE 1
            END;

            RETURN QUERY
            SELECT
                tv.trait_text::TEXT,
                tv.section::TEXT,
                (tv.segment_probabilities::float4[])[segment_index]::FLOAT as segment_probability,
                ROW_NUMBER() OVER (ORDER BY (tv.segment_probabilities::float4[])[segment_index] DESC)::INTEGER as rank_in_segment
            FROM trait_vectors tv
            WHERE tv.domain = target_domain
                AND (tv.segment_probabilities::float4[])[segment_index] >= min_probability
            ORDER BY segment_probability DESC
            LIMIT limit_results;
        END;
        $$ LANGUAGE plpgsql;

        COMMENT ON FUNCTION text_vector_similarity IS 'Calculate cosine similarity between two text-encoded vectors';
        COMMENT ON FUNCTION find_similar_segments_in_domain IS 'Find segments with similar trait patterns within a domain';
        COMMENT ON FUNCTION find_similar_traits_vector IS 'Find traits with similar segment patterns using pgvector';
        COMMENT ON FUNCTION find_segment_distinguishing_traits IS 'Find top traits that distinguish a specific segment';
        """

        try:
            self.cursor.execute(functions_sql)
            self.conn.commit()
            print("✅ Created vector similarity functions")
        except Exception as e:
            print(f"❌ Error creating similarity functions: {e}")
            self.conn.rollback()
            raise

    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

def main():
    """Main execution"""
    print("🔧 Fixing pgvector Dimensions")
    print("=" * 35)

    fixer = PgVectorFixer()

    try:
        fixer.connect_db()

        # Recreate tables with correct dimensions
        fixer.drop_and_recreate_vector_tables()

        # Generate vectors for each domain with correct dimensions
        trait_domains = [
            ('generic', 'generic_traits'),
            ('beauty', 'beauty_traits'),
            ('health_sports', 'health_sports_traits'),
            ('interests_lifestyle', 'interests_lifestyle_traits'),
            ('purchases', 'purchases_traits')
        ]

        for domain, table_name in trait_domains:
            fixer.generate_segment_vectors_fixed(domain, table_name)
            fixer.generate_trait_vectors_fixed(domain, table_name)

        # Create similarity functions
        fixer.create_vector_similarity_functions()

        print(f"\n🎉 SUCCESS! pgvector embeddings fixed and working.")
        print(f"🔍 Use these similarity functions:")
        print(f"   - find_similar_segments_in_domain('University Students', 'beauty')")
        print(f"   - find_similar_traits_vector('Music', 'interests_lifestyle')")
        print(f"   - find_segment_distinguishing_traits('Business Leaders', 'purchases')")

    except Exception as e:
        print(f"💥 Error: {e}")
        raise
    finally:
        fixer.close()

if __name__ == "__main__":
    main()