#!/usr/bin/env python3
"""
Create Generic Traits Relationships with Audience Segments
"""

import psycopg2
import psycopg2.extras

class GenericRelationshipManager:
    def __init__(self, database_url: str = "postgresql://postgres:postgres@localhost:5432/synthetic_personas"):
        self.database_url = database_url
        self.conn = None
        self.cursor = None

        # Mapping from audience_segments names to generic_traits columns
        self.segment_mapping = {
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

    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            print("✅ Connected to database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    def create_segment_mapping_table(self):
        """Create a mapping table between audience segments and generic trait columns"""
        print("🔗 Creating generic segment mapping table...")

        sql = """
        CREATE TABLE IF NOT EXISTS generic_segment_mapping (
            mapping_id SERIAL PRIMARY KEY,
            segment_id INTEGER NOT NULL REFERENCES audience_segments(segment_id),
            segment_name VARCHAR(200) NOT NULL,
            generic_column_name VARCHAR(200) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(segment_id, generic_column_name)
        );

        CREATE INDEX IF NOT EXISTS idx_generic_segment_mapping_segment_id ON generic_segment_mapping(segment_id);
        CREATE INDEX IF NOT EXISTS idx_generic_segment_mapping_column ON generic_segment_mapping(generic_column_name);

        COMMENT ON TABLE generic_segment_mapping IS 'Maps audience segments to generic_traits table columns';
        """

        try:
            self.cursor.execute(sql)
            self.conn.commit()
            print("✅ Created generic_segment_mapping table")
        except Exception as e:
            print(f"❌ Error creating mapping table: {e}")
            self.conn.rollback()
            raise

    def populate_segment_mapping(self):
        """Populate the segment mapping table"""
        print("📥 Populating generic segment mapping...")

        # Get audience segments
        self.cursor.execute("SELECT segment_id, segment_name FROM audience_segments ORDER BY segment_id")
        segments = self.cursor.fetchall()

        inserted_count = 0
        for segment in segments:
            segment_id = segment['segment_id']
            segment_name = segment['segment_name']

            if segment_name in self.segment_mapping:
                generic_column = self.segment_mapping[segment_name]

                # Check if generic column actually exists
                self.cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'generic_traits'
                    AND column_name = %s
                """, (generic_column,))

                if self.cursor.fetchone():
                    # Insert mapping
                    insert_sql = """
                        INSERT INTO generic_segment_mapping (segment_id, segment_name, generic_column_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (segment_id, generic_column_name) DO NOTHING
                    """
                    self.cursor.execute(insert_sql, (segment_id, segment_name, generic_column))
                    inserted_count += 1
                    print(f"  ✅ {segment_name} -> {generic_column}")
                else:
                    print(f"  ❌ {segment_name} -> {generic_column} (column not found)")
            else:
                print(f"  ⚠️  No mapping for: {segment_name}")

        self.conn.commit()
        print(f"✅ Inserted {inserted_count} generic segment mappings")

    def create_generic_segment_view(self):
        """Create a view that properly joins generic traits with audience segments"""
        print("👁️ Creating generic_segment_view...")

        # Build dynamic CASE statements for each segment
        case_statements = []
        for segment_name, column_name in self.segment_mapping.items():
            case_statements.append(f"""
                CASE WHEN m.segment_name = '{segment_name}' THEN gt.{column_name} END
            """)

        probability_case = " + ".join([f"COALESCE({stmt.strip()}, 0)" for stmt in case_statements])

        sql = f"""
        CREATE OR REPLACE VIEW generic_segment_view AS
        SELECT
            gt.trait_id,
            gt.trait_text,
            gt.section,
            a.segment_id,
            a.segment_name,
            a.male_percentage,
            a.female_percentage,
            ({probability_case}) as trait_probability,
            gt.created_at
        FROM generic_traits gt
        CROSS JOIN audience_segments a
        LEFT JOIN generic_segment_mapping m ON a.segment_id = m.segment_id
        WHERE ({probability_case}) IS NOT NULL AND ({probability_case}) > 0;

        COMMENT ON VIEW generic_segment_view IS 'Normalized view linking generic traits with audience segments';
        """

        try:
            self.cursor.execute(sql)
            self.conn.commit()
            print("✅ Created generic_segment_view")
        except Exception as e:
            print(f"❌ Error creating view: {e}")
            self.conn.rollback()
            raise

    def validate_relationships(self):
        """Validate the relationships and show sample data"""
        print("\n🔍 Validating generic trait relationships...")

        # Check mapping table
        self.cursor.execute("SELECT COUNT(*) as count FROM generic_segment_mapping")
        mapping_count = self.cursor.fetchone()['count']
        print(f"  📊 Segment mappings: {mapping_count}")

        # Check view
        self.cursor.execute("SELECT COUNT(*) as count FROM generic_segment_view")
        view_count = self.cursor.fetchone()['count']
        print(f"  📊 Generic-segment relationships: {view_count:,}")

        # Sample high-probability generic traits by segment
        print(f"\n🎯 Sample Generic Traits by Segment:")
        self.cursor.execute("""
            SELECT
                segment_name,
                trait_text,
                section,
                trait_probability
            FROM generic_segment_view
            WHERE trait_probability > 0.7
            ORDER BY segment_name, trait_probability DESC
            LIMIT 15
        """)

        current_segment = None
        for row in self.cursor.fetchall():
            if row['segment_name'] != current_segment:
                current_segment = row['segment_name']
                print(f"\n  🎯 {current_segment}:")

            trait = row['trait_text'][:50]
            section = row['section'][:25] if row['section'] else 'General'
            prob = row['trait_probability']
            print(f"    {trait:<50} | {section:<25} | {prob:.1%}")

    def create_referential_integrity_check(self):
        """Create a function to check referential integrity for generic traits"""
        print("🔒 Creating generic referential integrity check...")

        sql = """
        CREATE OR REPLACE FUNCTION check_generic_segment_integrity()
        RETURNS TABLE(
            issue_type TEXT,
            description TEXT,
            count BIGINT
        ) AS $$
        BEGIN
            -- Check for orphaned mappings (segments not in audience_segments)
            RETURN QUERY
            SELECT
                'Orphaned Mapping'::TEXT,
                'Generic segment mappings without corresponding audience_segments record'::TEXT,
                COUNT(*)::BIGINT
            FROM generic_segment_mapping m
            LEFT JOIN audience_segments a ON m.segment_id = a.segment_id
            WHERE a.segment_id IS NULL;

            -- Check for missing columns in generic_traits
            RETURN QUERY
            SELECT
                'Missing Column'::TEXT,
                'Mapped columns that do not exist in generic_traits table'::TEXT,
                COUNT(*)::BIGINT
            FROM generic_segment_mapping m
            WHERE NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'generic_traits'
                AND column_name = m.generic_column_name
            );

            -- Check for unmapped segments
            RETURN QUERY
            SELECT
                'Unmapped Segment'::TEXT,
                'Audience segments without corresponding generic trait columns'::TEXT,
                COUNT(*)::BIGINT
            FROM audience_segments a
            LEFT JOIN generic_segment_mapping m ON a.segment_id = m.segment_id
            WHERE m.segment_id IS NULL;
        END;
        $$ LANGUAGE plpgsql;

        COMMENT ON FUNCTION check_generic_segment_integrity() IS 'Checks referential integrity between generic traits and audience segments';
        """

        try:
            self.cursor.execute(sql)
            self.conn.commit()
            print("✅ Created generic integrity check function")

            # Run the check
            print("\n🔍 Running generic integrity check:")
            self.cursor.execute("SELECT * FROM check_generic_segment_integrity()")

            for row in self.cursor.fetchall():
                status = "✅" if row['count'] == 0 else "⚠️"
                print(f"  {status} {row['issue_type']}: {row['count']} issues")
                if row['count'] > 0:
                    print(f"     {row['description']}")

        except Exception as e:
            print(f"❌ Error creating integrity check: {e}")
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
    print("🔗 Creating Generic Traits Relationships")
    print("=" * 50)

    manager = GenericRelationshipManager()

    try:
        manager.connect_db()
        manager.create_segment_mapping_table()
        manager.populate_segment_mapping()
        manager.create_generic_segment_view()
        manager.validate_relationships()
        manager.create_referential_integrity_check()

        print(f"\n🎉 SUCCESS! Generic traits are now properly linked to audience segments.")
        print(f"🔗 Use 'generic_segment_view' for normalized queries")
        print(f"🔍 Use 'check_generic_segment_integrity()' to validate relationships")

    except Exception as e:
        print(f"💥 Error: {e}")
        raise
    finally:
        manager.close()

if __name__ == "__main__":
    main()