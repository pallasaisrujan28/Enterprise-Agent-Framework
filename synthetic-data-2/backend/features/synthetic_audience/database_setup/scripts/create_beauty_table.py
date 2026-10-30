#!/usr/bin/env python3
"""
Create Beauty Traits Table and Load Data
"""

import pandas as pd
import psycopg2
import psycopg2.extras
from pathlib import Path

class BeautyTableCreator:
    def __init__(self, database_url: str = "postgresql://postgres:postgres@localhost:5432/synthetic_personas"):
        self.database_url = database_url
        self.conn = None
        self.cursor = None
        self.csv_dir = Path("csv_outputs")

    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            print("✅ Connected to database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    def create_beauty_traits_table(self):
        """Create beauty_traits table"""
        print("💄 Creating beauty_traits table...")

        # Get the column names from the beauty_answers.csv
        csv_file = self.csv_dir / "beauty_answers.csv"
        df = pd.read_csv(csv_file, nrows=1)

        # Get segment columns (skip trait_text and section)
        segment_columns = [col for col in df.columns if col not in ['trait_text', 'section']]

        print(f"✅ Found {len(segment_columns)} segment columns in CSV")

        # Create table with dynamic columns for each segment
        column_definitions = []
        for col in segment_columns:
            # Clean column name for SQL
            clean_col = col.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').replace('&', 'and').replace(',', '').replace('/', '_')
            column_definitions.append(f"{clean_col} DECIMAL(8,5)")

        columns_sql = ",\n            ".join(column_definitions)

        sql = f"""
        CREATE TABLE beauty_traits (
            trait_id SERIAL PRIMARY KEY,
            trait_text VARCHAR(500) NOT NULL,
            section VARCHAR(200),
            {columns_sql},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create unique index to handle duplicates
        CREATE UNIQUE INDEX idx_beauty_traits_unique
        ON beauty_traits (trait_text, COALESCE(section, 'NO_SECTION'));

        CREATE INDEX idx_beauty_traits_text ON beauty_traits(trait_text);
        CREATE INDEX idx_beauty_traits_section ON beauty_traits(section);

        COMMENT ON TABLE beauty_traits IS 'Beauty-related traits and attitudes for all audience segments';
        """

        try:
            self.cursor.execute(sql)
            self.conn.commit()
            print("✅ Created beauty_traits table")

            # Store column mapping for later use
            self.segment_columns = segment_columns
            self.clean_columns = [col.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').replace('&', 'and').replace(',', '').replace('/', '_') for col in segment_columns]

        except Exception as e:
            print(f"❌ Error creating beauty_traits table: {e}")
            self.conn.rollback()
            raise

    def load_beauty_traits_data(self):
        """Load beauty traits data from CSV"""
        print("📥 Loading beauty traits data...")

        csv_file = self.csv_dir / "beauty_answers.csv"
        if not csv_file.exists():
            print(f"❌ CSV file not found: {csv_file}")
            return False

        try:
            df = pd.read_csv(csv_file)
            print(f"✅ Loaded {len(df)} traits from CSV")

            # Clean duplicates at pandas level before insertion
            print("🧹 Cleaning duplicates...")
            original_count = len(df)

            # Create a unique key for deduplication
            df['unique_key'] = df['trait_text'] + '|' + df['section'].fillna('NO_SECTION')

            # Remove duplicates, keeping the first occurrence
            df_clean = df.drop_duplicates(subset=['unique_key'], keep='first')
            df_clean = df_clean.drop('unique_key', axis=1)

            print(f"✅ Removed {original_count - len(df_clean)} duplicates, {len(df_clean)} unique traits remain")

            # Use UPSERT approach from the start
            placeholders = ", ".join(["%s"] * (2 + len(self.clean_columns)))
            insert_columns = ["trait_text", "section"] + self.clean_columns
            update_columns = [f"{col} = EXCLUDED.{col}" for col in self.clean_columns]

            upsert_sql = f"""
                INSERT INTO beauty_traits ({', '.join(insert_columns)})
                VALUES ({placeholders})
                ON CONFLICT (trait_text, COALESCE(section, 'NO_SECTION'))
                DO UPDATE SET {', '.join(update_columns)}
            """

            inserted_count = 0
            error_count = 0

            for _, row in df_clean.iterrows():
                try:
                    # Prepare values
                    values = [row['trait_text'], row['section']]

                    # Add segment values
                    for orig_col in self.segment_columns:
                        value = row[orig_col]
                        if pd.notna(value):
                            values.append(float(value))
                        else:
                            values.append(None)

                    self.cursor.execute(upsert_sql, values)
                    inserted_count += 1

                except Exception as e:
                    error_count += 1
                    if error_count <= 5:  # Show first 5 errors
                        print(f"❌ Error inserting '{row['trait_text']}' (section: {row.get('section', 'None')}): {e}")

            self.conn.commit()
            print(f"✅ Inserted/Updated {inserted_count} beauty traits")
            if error_count > 0:
                print(f"⚠️  {error_count} errors encountered")

            return True

        except Exception as e:
            print(f"❌ Error loading beauty traits: {e}")
            self.conn.rollback()
            raise

    def validate_beauty_table(self):
        """Validate the beauty traits table"""
        print("\n🔍 Validating beauty_traits table...")

        # Check record count
        self.cursor.execute("SELECT COUNT(*) as count FROM beauty_traits")
        count = self.cursor.fetchone()['count']
        print(f"  📊 beauty_traits: {count:,} records")

        # Check section distribution
        self.cursor.execute("""
            SELECT section, COUNT(*) as count
            FROM beauty_traits
            GROUP BY section
            ORDER BY count DESC
            LIMIT 10
        """)

        print(f"\n📋 Section Distribution:")
        for row in self.cursor.fetchall():
            section_name = row['section'] or 'NULL'
            print(f"  {section_name}: {row['count']} traits")

        # Sample high-probability traits for different segments
        segments_to_test = ['university_students', 'healthcare_professionals', 'business_leaders']

        for segment in segments_to_test:
            print(f"\n💄 TOP BEAUTY TRAITS - {segment.replace('_', ' ').title()}:")

            self.cursor.execute(f"""
                SELECT trait_text, section, {segment} as probability
                FROM beauty_traits
                WHERE {segment} > 0.4
                ORDER BY {segment} DESC
                LIMIT 5
            """)

            for row in self.cursor.fetchall():
                trait_text = row['trait_text'][:50]
                section = row['section'] or 'General'
                prob = row['probability']
                print(f"  {trait_text:<50} | {section:<25} | {prob:.1%}")

    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

def main():
    """Main execution"""
    print("💄 Creating Beauty Traits Table")
    print("=" * 50)

    creator = BeautyTableCreator()

    try:
        creator.connect_db()
        creator.create_beauty_traits_table()
        creator.load_beauty_traits_data()
        creator.validate_beauty_table()

        print(f"\n🎉 SUCCESS! Beauty traits table created and data loaded.")
        print(f"💄 Ready to query beauty-related audience characteristics!")

    except Exception as e:
        print(f"💥 Error: {e}")
        raise
    finally:
        creator.close()

if __name__ == "__main__":
    main()