#!/usr/bin/env python3
"""
Fixed Excel to CSV Converter - Correct Section Detection
Based on the detailed analysis, fix the section mapping logic
"""

import pandas as pd
import numpy as np
from pathlib import Path

class FixedExcelToCsvConverter:
    def __init__(self, excel_file: str = "Synthetic Audiences.xlsx"):
        self.excel_file = excel_file
        self.output_dir = Path("csv_outputs")
        self.output_dir.mkdir(exist_ok=True)

    def load_excel_file(self):
        """Load all sheets from Excel file"""
        print(f"📊 Loading Excel file: {self.excel_file}")
        try:
            self.excel_data = pd.read_excel(self.excel_file, sheet_name=None)
            print(f"✅ Loaded {len(self.excel_data)} sheets")
            return True
        except Exception as e:
            print(f"❌ Error loading Excel file: {e}")
            return False

    def extract_audience_segments(self):
        """Extract and clean audience segments data (same as before)"""
        print("\n🎯 Processing Audience Segments sheet...")

        if "Audience Segments" not in self.excel_data:
            print("❌ Audience Segments sheet not found")
            return False

        df = self.excel_data["Audience Segments"].copy()
        segment_data = []

        # University Students
        university_split = df.iloc[7, 2]
        if pd.notna(university_split):
            split_text = str(university_split).strip()
            import re
            match = re.search(r'(\d+)%\s*Male\s*-\s*(\d+)%\s*Female', split_text)
            if match:
                male_pct = float(match.group(1))
                female_pct = float(match.group(2))
            else:
                male_pct, female_pct = 50.0, 50.0
        else:
            male_pct, female_pct = 50.0, 50.0

        segment_data.append({
            'segment_name': 'University Students',
            'male_percentage': male_pct,
            'female_percentage': female_pct
        })

        # Other segments
        for col_idx in range(2, 10):
            segment_name = df.iloc[10, col_idx]
            gender_split = df.iloc[14, col_idx]

            if pd.notna(segment_name) and pd.notna(gender_split):
                segment_str = str(segment_name).strip()
                split_str = str(gender_split).strip()

                import re
                match = re.search(r'(\d+)%\s*Male\s*-\s*(\d+)%\s*Female', split_str)
                if match:
                    male_pct = float(match.group(1))
                    female_pct = float(match.group(2))
                else:
                    male_pct, female_pct = 50.0, 50.0

                segment_data.append({
                    'segment_name': segment_str,
                    'male_percentage': male_pct,
                    'female_percentage': female_pct
                })

        segments_df = pd.DataFrame(segment_data)
        output_file = self.output_dir / "audience_segments.csv"
        segments_df.to_csv(output_file, index=False)
        print(f"✅ Saved audience segments to: {output_file}")
        return True

    def transform_generic_answers_fixed(self):
        """Transform Generic Answers with CORRECT section detection"""
        print("\n🔍 Processing Generic Answers with FIXED section detection...")

        if "Generic Answers" not in self.excel_data:
            print("❌ Generic Answers sheet not found")
            return False

        df = self.excel_data["Generic Answers"].copy()
        print(f"📊 Raw sheet shape: {df.shape}")

        # Get headers from row 2
        headers = df.iloc[2].values
        segment_columns = {}
        for col_idx in range(2, len(headers)):
            if col_idx < len(headers) and pd.notna(headers[col_idx]):
                header_str = str(headers[col_idx]).strip()
                segment_columns[header_str] = col_idx

        print(f"✅ Found {len(segment_columns)} segment columns")

        # Define the EXACT section mapping based on our analysis
        section_definitions = {
            # Row number: Section name
            2: "Gender",
            9: "Age Groups",
            14: "Generations",
            25: "UK Annual HH Income",
            41: "Urban Context",
            46: "UK Regions",
            62: "Household Living Arrangements",
            71: "Relationship Status",
            78: "Number of Children",
            84: "Age of Children",
            95: "Shopping Preferences - Online vs In-Store",
            99: "Shopping Preferences - Products vs Experiences",
            103: "Shopping Preferences - Big vs Local Retailers",
            107: "Shopping Preferences - Eco-Friendly vs Price",
            111: "Sports Played",
            123: "Vacation Types",
            135: "Vehicle Ownership",
            145: "Property Ownership",
            161: "Employment Status",
            184: "Brand Discovery",
            189: "Brand Communication Channels",
            220: "Brand Qualities",
            232: "Online Product Research",
            250: "Online Purchase Drivers",
            267: "Internet Usage Reasons",
            289: "Media Consumption",
            300: "Social Media Platforms"
        }

        # Extract trait data with CORRECT section mapping
        trait_data = []
        current_section = None

        for idx in range(len(df)):
            # Check if this row starts a new section
            if idx in section_definitions:
                current_section = section_definitions[idx]
                print(f"  📁 Section {idx}: {current_section}")
                continue

            # Skip non-data rows
            if idx <= 2:
                continue

            row = df.iloc[idx]
            trait_cell = row.iloc[1] if len(row) > 1 else None

            if pd.isna(trait_cell):
                continue

            trait_text = str(trait_cell).strip()

            # Skip subsection headers and notes
            skip_patterns = [
                'Average Age', 'Sample Size', 'Audience Size',
                'In-Store vs Online', 'Products vs Experiences',
                'Big vs Local Retailers', 'Eco-Friendly vs Price',
                'Property Rental', 'Property by Type of Ownership',
                'Job Seniority', 'Online Product Research',
                'UK Average Annual HH Income'
            ]

            if any(pattern in trait_text for pattern in skip_patterns):
                continue

            # Check if this row has valid probability data
            has_prob_data = False
            for col_idx in range(2, min(len(row), 8)):
                if pd.notna(row.iloc[col_idx]):
                    try:
                        val = float(row.iloc[col_idx])
                        if 0 <= val <= 1:
                            has_prob_data = True
                            break
                    except:
                        pass

            if not has_prob_data:
                continue

            # Ensure we have a valid section
            if not current_section:
                current_section = "General"

            row_data = {
                'trait_text': trait_text,
                'section': current_section
            }

            # Add segment values
            for segment_name, col_idx in segment_columns.items():
                value = row.iloc[col_idx] if col_idx < len(row) else None

                if pd.notna(value):
                    try:
                        value = float(value)
                        row_data[segment_name] = value
                    except (ValueError, TypeError):
                        row_data[segment_name] = None
                else:
                    row_data[segment_name] = None

            trait_data.append(row_data)

        # Create DataFrame and save
        traits_df = pd.DataFrame(trait_data)
        traits_df = traits_df.dropna(subset=['trait_text'])
        traits_df = traits_df[traits_df['trait_text'].str.strip() != '']

        output_file = self.output_dir / "generic_answers_fixed.csv"
        traits_df.to_csv(output_file, index=False)

        print(f"✅ Saved FIXED Generic Answers to: {output_file}")
        print(f"📊 Total traits: {len(traits_df)}")

        # Show section summary
        section_counts = traits_df['section'].value_counts()
        print(f"\n📋 Section Summary:")
        for section, count in section_counts.items():
            print(f"  {section}: {count} traits")

        return True

    def run_conversion(self):
        """Run the fixed conversion process"""
        print("🚀 Starting FIXED Excel to CSV conversion")
        print("=" * 60)

        if not self.load_excel_file():
            return False

        if not self.extract_audience_segments():
            return False

        if not self.transform_generic_answers_fixed():
            return False

        print(f"\n🎉 FIXED conversion complete!")
        return True

def main():
    """Main execution"""
    converter = FixedExcelToCsvConverter()

    try:
        success = converter.run_conversion()
        if success:
            print(f"\n✅ SUCCESS! Fixed conversion completed.")
        else:
            print(f"\n❌ FAILED! Check errors above")
    except Exception as e:
        print(f"💥 Error: {e}")
        raise

if __name__ == "__main__":
    main()