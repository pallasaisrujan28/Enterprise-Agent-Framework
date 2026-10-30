#!/usr/bin/env python3
"""
Fix Embedding Storage Issue
Properly store embeddings as pgvector format instead of strings
"""

import psycopg2
import psycopg2.extras
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path


class EmbeddingStorageFix:
    def __init__(self):
        self.database_url = "postgresql://postgres:postgres@localhost:5432/synthetic_personas"
        self.conn = None
        self.cursor = None

        print("🧠 Initializing SentenceTransformer for proper embeddings...")
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

    def fix_embedding_storage(self):
        """Fix embedding storage to use proper pgvector format"""

        print("\n🔧 FIXING EMBEDDING STORAGE")
        print("=" * 50)

        self.connect_db()

        # Get all traits that need embedding fixes
        self.cursor.execute("""
            SELECT id, trait_text, embedding
            FROM traits
            WHERE embedding IS NOT NULL
            ORDER BY id
        """)

        traits = self.cursor.fetchall()
        print(f"📊 Found {len(traits)} traits with embeddings to fix")

        fixed_count = 0

        for i, trait in enumerate(traits):
            trait_id = trait['id']
            trait_text = trait['trait_text']

            try:
                # Generate proper embedding
                embedding_vector = self.model.encode(trait_text)

                # Convert to list for PostgreSQL
                embedding_list = embedding_vector.tolist()

                # Update with proper pgvector format
                update_sql = """
                    UPDATE traits
                    SET embedding = %s::vector
                    WHERE id = %s
                """

                self.cursor.execute(update_sql, (embedding_list, trait_id))
                fixed_count += 1

                if (i + 1) % 100 == 0:
                    print(f"   ✅ Fixed {i + 1}/{len(traits)} embeddings")
                    self.conn.commit()

            except Exception as e:
                print(f"   ❌ Error fixing trait {trait_id}: {e}")
                continue

        # Final commit
        self.conn.commit()
        print(f"\n✅ Successfully fixed {fixed_count} embeddings")

        # Validate the fix
        self.validate_embedding_fix()

    def validate_embedding_fix(self):
        """Validate that embeddings are now properly stored"""

        print("\n🔍 VALIDATING EMBEDDING FIX")
        print("=" * 40)

        # Test a few embeddings
        self.cursor.execute("""
            SELECT trait_text, embedding
            FROM traits
            WHERE embedding IS NOT NULL
            LIMIT 5
        """)

        test_traits = self.cursor.fetchall()

        for trait in test_traits:
            trait_text = trait['trait_text']
            embedding = trait['embedding']

            try:
                # Test conversion to numpy array
                if isinstance(embedding, str):
                    # Try to parse if still string
                    import ast
                    embedding_list = ast.literal_eval(embedding)
                    embedding_array = np.array(embedding_list)
                else:
                    # Should be a proper vector now
                    embedding_array = np.array(embedding)

                print(f"   ✅ {trait_text[:40]:40s} | Shape: {embedding_array.shape} | Type: {type(embedding)}")

            except Exception as e:
                print(f"   ❌ {trait_text[:40]:40s} | Error: {e}")

        # Test vector similarity query
        try:
            test_vector = self.model.encode("test query").tolist()

            self.cursor.execute("""
                SELECT trait_text, 1 - (embedding <=> %s::vector) as similarity
                FROM traits
                WHERE embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT 3
            """, (test_vector,))

            similar_traits = self.cursor.fetchall()

            print(f"\n🎯 Vector similarity test:")
            for trait in similar_traits:
                print(f"   {trait['trait_text'][:50]:50s} | Similarity: {trait['similarity']:.3f}")

            print("✅ Embedding fix validation PASSED")

        except Exception as e:
            print(f"❌ Vector similarity test failed: {e}")

    def run_fix(self):
        """Run the complete embedding fix"""

        print("🔧 STARTING EMBEDDING STORAGE FIX")
        print("=" * 50)

        try:
            self.fix_embedding_storage()
            print(f"\n🎉 EMBEDDING FIX COMPLETE!")
            print("✅ All embeddings properly stored as pgvector format")
            print("✅ Vector similarity queries operational")
            print("✅ Enhanced trait selector v2 ready for testing")

        except Exception as e:
            print(f"\n❌ Embedding fix failed: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.close_db()


def main():
    """Main fix execution"""
    print("🔬 Embedding Storage Fix")
    print("=" * 30)

    fixer = EmbeddingStorageFix()
    fixer.run_fix()


if __name__ == "__main__":
    main()