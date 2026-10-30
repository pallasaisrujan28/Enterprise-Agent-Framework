#!/usr/bin/env python3
"""
Convert Purchases - NEW Sheet to Clean CSV
"""

import pandas as pd
import numpy as np
from pathlib import Path

def convert_purchases():
    """Convert Purchases sheet to clean CSV format"""
    print("💳 Converting Purchases to CSV")
    print("=" * 50)

    try:
        df = pd.read_excel("Synthetic Audiences.xlsx", sheet_name="Purchases - NEW")
        print(f"📊 Sheet shape: {df.shape}")

        # Find the header row (contains segment names)
        header_row = None
        for idx in range(min(10, len(df))):
            row = df.iloc[idx]
            # Look for "University Students" in the row
            if any(pd.notna(cell) and "University Students" in str(cell) for cell in row):
                header_row = idx
                break

        if header_row is None:
            print("❌ Could not find header row")
            return False

        print(f"✅ Found header row at: {header_row}")

        # Extract segment columns
        headers = df.iloc[header_row].values
        segment_columns = {}

        for col_idx in range(1, len(headers)):  # Start from column 1
            if col_idx < len(headers) and pd.notna(headers[col_idx]):
                header_str = str(headers[col_idx]).strip()
                # Only include actual segment names, not section descriptions
                if any(segment in header_str for segment in [
                    'University Students', 'Business Leaders', 'Finance Professionals',
                    'Media Professionals', 'Healthcare Professionals', 'Legal Services',
                    'Government Workers', 'Hospitality Workers', 'Manufacturing'
                ]):
                    segment_columns[header_str] = col_idx

        print(f"✅ Found {len(segment_columns)} segment columns:")
        for seg, col in segment_columns.items():
            print(f"  - {seg}: column {col}")

        # Extract trait data
        trait_data = []
        current_section = None

        for idx in range(len(df)):
            if idx <= header_row:  # Skip header and above
                continue

            row = df.iloc[idx]
            trait_cell = row.iloc[1] if len(row) > 1 else None

            if pd.isna(trait_cell):
                continue

            trait_text = str(trait_cell).strip()

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
                # This might be a section header
                if any(keyword in trait_text for keyword in [
                    'Purchase', 'Buy', 'Shopping', 'Spend', 'Brand', 'Product',
                    'Consumer', 'Retail', 'Store', 'Online', 'Payment', 'Price'
                ]):
                    current_section = trait_text
                    print(f"  📁 Section: {current_section}")
                continue

            # This is a trait with data
            row_data = {
                'trait_text': trait_text,
                'section': current_section or "Purchases General"
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

        output_dir = Path("csv_outputs")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "purchases.csv"
        traits_df.to_csv(output_file, index=False)

        print(f"✅ Saved Purchases to: {output_file}")
        print(f"📊 Total traits: {len(traits_df)}")

        # Show section summary
        if 'section' in traits_df.columns:
            section_counts = traits_df['section'].value_counts()
            print(f"\n📋 Section Summary:")
            for section, count in section_counts.items():
                print(f"  {section}: {count} traits")

        # Show sample data
        print(f"\n📋 Sample traits:")
        for idx, row in traits_df.head(3).iterrows():
            print(f"  Section: {row['section']}")
            print(f"  Trait: {row['trait_text']}")
            university_val = row.get('University Students', 'N/A')
            business_val = row.get('Business Leaders', 'N/A')
            print(f"  Sample values: University={university_val}, Business={business_val}")
            print()

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    convert_purchases()