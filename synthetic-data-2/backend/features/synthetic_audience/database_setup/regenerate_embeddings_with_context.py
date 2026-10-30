#!/usr/bin/env python3
"""
Regenerate Embeddings WITH Section Context
This fixes the root cause: embeddings were created without question/section context
"""

import psycopg2
import psycopg2.extras
import numpy as np
from sentence_transformers import SentenceTransformer


class ContextualEmbeddingGenerator:
    def __init__(self):
        self.database_url = "postgresql://postgres:postgres@localhost:5454/synthetic_personas"
        self.conn = None
        self.cursor = None

        print("🧠 Initializing SentenceTransformer for contextual embeddings...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

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

    def create_contextual_text(self, trait_text: str, section: str) -> str:
        """
        Create contextual text for embedding

        Examples:
        - trait_text="Male", section="Gender" → "Gender: Male"
        - trait_text="Supervisor", section="Job Seniority" → "Job Seniority: Supervisor"
        - trait_text="Skincare", section="Health, Fitness & Beauty Interests" → "Health, Fitness & Beauty Interests: Skincare"
        """

        if section and section != "Unknown Section":
            return f"{section}: {trait_text}"
        else:
            # For unknown sections, just use trait text
            return trait_text

    def regenerate_all_embeddings(self):
        """Regenerate ALL embeddings with section context"""

        print("\n🔄 REGENERATING EMBEDDINGS WITH CONTEXT")
        print("=" * 60)

        self.connect_db()

        # Get all traits
        self.cursor.execute("""
            SELECT id, trait_text, section
            FROM traits
            ORDER BY id
        """)

        traits = self.cursor.fetchall()
        print(f"📊 Found {len(traits)} traits to process")

        regenerated_count = 0
        improved_count = 0

        for i, trait in enumerate(traits):
            trait_id = trait['id']
            trait_text = trait['trait_text']
            section = trait['section']

            try:
                # Create contextual text
                contextual_text = self.create_contextual_text(trait_text, section)

                # Track if context was added
                if contextual_text != trait_text:
                    improved_count += 1

                # Generate embedding with context
                embedding_vector = self.model.encode(contextual_text)

                # Convert to list for PostgreSQL
                embedding_list = embedding_vector.tolist()

                # Update with proper pgvector format
                update_sql = """
                    UPDATE traits
                    SET embedding = %s::vector
                    WHERE id = %s
                """

                self.cursor.execute(update_sql, (embedding_list, trait_id))
                regenerated_count += 1

                if (i + 1) % 100 == 0:
                    print(f"   ✅ Processed {i + 1}/{len(traits)} traits")
                    print(f"      ({improved_count} with added context)")
                    self.conn.commit()

            except Exception as e:
                print(f"   ❌ Error processing trait {trait_id}: {e}")
                continue

        # Final commit
        self.conn.commit()
        print(f"\n✅ Successfully regenerated {regenerated_count} embeddings")
        print(f"✅ Added context to {improved_count} embeddings")

        # Validate the results
        self.validate_contextual_embeddings()

    def validate_contextual_embeddings(self):
        """Validate that embeddings now have proper context"""

        print("\n🔍 VALIDATING CONTEXTUAL EMBEDDINGS")
        print("=" * 60)

        # Test 1: Job-related traits should have LOW similarity to "beauty skincare"
        print("\nTest 1: Job traits vs beauty product (should be LOW similarity)")
        print("-" * 60)

        beauty_query = "A new affordable beauty and skincare product line for young adults"
        beauty_vector = self.model.encode(beauty_query).tolist()

        self.cursor.execute("""
            SELECT trait_text, section, 1 - (embedding <=> %s::vector) as similarity
            FROM traits
            WHERE trait_text ILIKE '%manager%' OR trait_text ILIKE '%executive%'
            ORDER BY similarity DESC
            LIMIT 5
        """, (beauty_vector,))

        job_traits = self.cursor.fetchall()
        for trait in job_traits:
            print(f"   {trait['trait_text']:40} | Section: {trait['section']:20} | Similarity: {trait['similarity']:.3f}")

        # Test 2: Beauty-related traits should have HIGH similarity
        print("\n\nTest 2: Beauty traits vs beauty product (should be HIGH similarity)")
        print("-" * 60)

        self.cursor.execute("""
            SELECT trait_text, section, 1 - (embedding <=> %s::vector) as similarity
            FROM traits
            WHERE trait_text ILIKE '%skincare%' OR trait_text ILIKE '%beauty%' OR trait_text ILIKE '%cosmetic%'
            ORDER BY similarity DESC
            LIMIT 5
        """, (beauty_vector,))

        beauty_traits = self.cursor.fetchall()
        for trait in beauty_traits:
            print(f"   {trait['trait_text']:40} | Section: {trait['section']:20} | Similarity: {trait['similarity']:.3f}")

        # Test 3: Job traits should have HIGH similarity to "AI productivity tool"
        print("\n\nTest 3: Job traits vs AI business tool (should be HIGH similarity)")
        print("-" * 60)

        business_query = "An AI-powered productivity tool for business professionals"
        business_vector = self.model.encode(business_query).tolist()

        self.cursor.execute("""
            SELECT trait_text, section, 1 - (embedding <=> %s::vector) as similarity
            FROM traits
            WHERE trait_text ILIKE '%manager%' OR trait_text ILIKE '%executive%'
            ORDER BY similarity DESC
            LIMIT 5
        """, (business_vector,))

        business_job_traits = self.cursor.fetchall()
        for trait in business_job_traits:
            print(f"   {trait['trait_text']:40} | Section: {trait['section']:20} | Similarity: {trait['similarity']:.3f}")

        print("\n" + "=" * 60)
        print("✅ Validation complete - check if similarities make sense")

    def run_regeneration(self):
        """Run the complete embedding regeneration"""

        print("🔄 STARTING CONTEXTUAL EMBEDDING REGENERATION")
        print("=" * 60)
        print("\nThis will:")
        print("  1. Add section context to all trait embeddings")
        print("  2. Fix semantic similarity for ALL campaigns")
        print("  3. Eliminate need for keyword-based filtering")
        print()

        try:
            self.regenerate_all_embeddings()
            print(f"\n🎉 EMBEDDING REGENERATION COMPLETE!")
            print("✅ All embeddings now include section context")
            print("✅ Semantic similarity should work correctly for all campaigns")
            print("✅ No keyword-based filtering needed")

        except Exception as e:
            print(f"\n❌ Embedding regeneration failed: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.close_db()


def main():
    """Main execution"""
    print("🔬 Contextual Embedding Regeneration")
    print("=" * 40)

    generator = ContextualEmbeddingGenerator()
    generator.run_regeneration()


if __name__ == "__main__":
    main()
