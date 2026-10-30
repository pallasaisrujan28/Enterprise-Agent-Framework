#!/usr/bin/env python3
"""
Fix Database Duplicates: Remove conflicting duplicate entries and establish section priorities
"""

import psycopg2
import psycopg2.extras

class DatabaseDuplicateFixer:
    def __init__(self, database_url: str = "postgresql://postgres:postgres@localhost:5432/synthetic_personas"):
        self.database_url = database_url
        self.conn = None
        self.cursor = None

        # Define section priorities (higher number = higher priority)
        self.section_priorities = {
            # Purchases - prioritize "Last Month" over "Online Last Month"
            "Minor Purchases: All Products - Purchased in Last Month": 10,
            "Minor Purchases: All Products - Purchased Online in Last Month": 5,
            "Major Purchases: All Products - Purchased in Last 3-6 Months": 8,
            "Major Purchases: All Products - Planning to Purchase": 6,

            # Health/Sports - prioritize "Sports Played" over "Sports Followed"
            "Sports Played": 10,
            "Sports Followed": 7,
            "Healthy Food": 9,
            "Dieting / Food Control": 8,

            # Interests/Lifestyle - keep all lifestyle segmentations but prioritize drive car
            "Lifestyle Segmentation: Drive a car": 10,
            "Lifestyle Segmentation: Donate to charity": 9,
            "Lifestyle Segmentation: Visit the cinema": 8,
            "Lifestyle Segmentation: Eat out at a restauran": 7,
            "Lifestyle Segmentation: Use public transport": 6,
            "Lifestyle Segmentation: Drink alcohol": 5,
            "Lifestyle Segmentation: Eat fast food": 4,

            # Beauty - prioritize actual product usage over general categories
            "Minor Purchases: Personal Care Items": 10,
            "Haircare Products Used in the Last Week*": 9,
            "Skincare Products Used in the Last Week*": 8,
            "Cosmetic Products Used in the Last Week*": 7,
            "Haircare / Skincare / Cosmetic Products Used in the Last Week*": 6,
            "Cosmetic Brands Used in the Last Week*": 5,
            "Health, Fitness & Beauty Interests": 4,

            # Generic - prioritize specific categories
            "Number of Children": 10,
            "Property Ownership": 9,
            "Employment Status": 8,
            "Relationship Status": 7,
            "Vacation Types": 6,
            "Online Product Research": 9,
            "Brand Discovery": 8,
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

    def get_section_priority(self, section):
        """Get priority for a section, default to 1"""
        return self.section_priorities.get(section, 1)

    def fix_table_duplicates(self, table_name):
        """Fix duplicates in a specific table"""
        print(f"\n🔧 Fixing duplicates in {table_name}...")

        # Find all duplicate trait_text entries
        self.cursor.execute(f"""
            SELECT trait_text, COUNT(*) as count_occurrences
            FROM {table_name}
            GROUP BY trait_text
            HAVING COUNT(*) > 1
            ORDER BY trait_text;
        """)

        duplicates = self.cursor.fetchall()

        if not duplicates:
            print(f"  ✅ No duplicates found in {table_name}")
            return

        print(f"  📊 Found {len(duplicates)} duplicate traits to fix")

        fixed_count = 0

        for dup in duplicates:
            trait_text = dup['trait_text']

            # Get all entries for this trait
            self.cursor.execute(f"""
                SELECT trait_id, trait_text, section
                FROM {table_name}
                WHERE trait_text = %s
                ORDER BY section;
            """, (trait_text,))

            entries = self.cursor.fetchall()

            if len(entries) <= 1:
                continue

            # Sort by priority (highest first)
            entries_with_priority = []
            for entry in entries:
                priority = self.get_section_priority(entry['section'])
                entries_with_priority.append({
                    'trait_id': entry['trait_id'],
                    'section': entry['section'],
                    'priority': priority
                })

            # Sort by priority descending, then by section name for consistency
            entries_with_priority.sort(key=lambda x: (-x['priority'], x['section']))

            # Keep the highest priority entry, delete the rest
            entries_to_keep = entries_with_priority[0]
            entries_to_delete = entries_with_priority[1:]

            print(f"    🎯 {trait_text}:")
            print(f"      ✅ KEEPING: {entries_to_keep['section']} (priority: {entries_to_keep['priority']})")

            for entry in entries_to_delete:
                print(f"      ❌ DELETING: {entry['section']} (priority: {entry['priority']})")

                # Delete the lower priority entry
                self.cursor.execute(f"""
                    DELETE FROM {table_name}
                    WHERE trait_id = %s;
                """, (entry['trait_id'],))

            fixed_count += 1

        print(f"  ✅ Fixed {fixed_count} duplicate traits in {table_name}")

    def add_unique_constraints(self):
        """Add UNIQUE constraints to prevent future duplicates"""
        print(f"\n🔒 Adding UNIQUE constraints to prevent future duplicates...")

        tables = ['purchases_traits', 'interests_lifestyle_traits', 'health_sports_traits', 'beauty_traits', 'generic_traits']

        for table in tables:
            try:
                # Drop existing constraint if it exists
                self.cursor.execute(f"""
                    ALTER TABLE {table}
                    DROP CONSTRAINT IF EXISTS {table}_trait_text_section_unique;
                """)

                # Add new unique constraint
                self.cursor.execute(f"""
                    ALTER TABLE {table}
                    ADD CONSTRAINT {table}_trait_text_section_unique
                    UNIQUE (trait_text, section);
                """)

                print(f"  ✅ Added UNIQUE constraint to {table}")

            except Exception as e:
                print(f"  ❌ Failed to add constraint to {table}: {e}")

    def fix_all_duplicates(self):
        """Fix duplicates in all tables"""
        print("🔧 Starting comprehensive duplicate fix...")

        tables = ['purchases_traits', 'interests_lifestyle_traits', 'health_sports_traits', 'beauty_traits', 'generic_traits']

        for table in tables:
            self.fix_table_duplicates(table)

        # Add unique constraints
        self.add_unique_constraints()

        # Commit all changes
        self.conn.commit()
        print(f"\n🎉 All duplicate fixes committed to database!")

def main():
    """Main execution"""
    print("🔧 Database Duplicate Fixer")
    print("=" * 50)

    fixer = DatabaseDuplicateFixer()
    fixer.connect_db()
    fixer.fix_all_duplicates()

    print(f"\n✅ Database duplicate fix complete!")

if __name__ == "__main__":
    main()