# Database Setup Guide for Synthetic Audience Generation

This directory contains all scripts and data files needed to initialize the PostgreSQL database for the synthetic audience generation system.

## 📁 Directory Structure

```
database_setup/
├── README.md                                    # This file
├── Synthetic Audiences.xlsx                     # SOURCE DATA (all trait data)
├── phase2b_database_migration.py                # MAIN MIGRATION SCRIPT
├── regenerate_embeddings_with_context.py        # Regenerate trait embeddings
├── fix_embedding_storage.py                     # Fix embedding format issues
├── scripts/                                     # Individual table creation scripts
│   ├── create_beauty_table.py
│   ├── create_beauty_relationships.py
│   ├── create_health_sports_table.py
│   ├── create_health_sports_relationships.py
│   ├── create_interests_lifestyle_table.py
│   ├── create_interests_lifestyle_relationships.py
│   ├── create_purchases_table.py
│   ├── create_purchases_relationships.py
│   ├── create_generic_relationships.py
│   ├── fix_database_duplicates.py
│   └── fix_pgvector_dimensions.py
└── converters/                                  # Excel to CSV converters
    ├── convert_beauty_answers.py
    ├── convert_health_sports.py
    ├── convert_interests_lifestyle.py
    ├── convert_purchases.py
    └── fix_csv_converter.py
```

## 🎯 Purpose

These scripts perform a **ONE-TIME SETUP** to:
1. Create normalized PostgreSQL database schema
2. Read trait data from `Synthetic Audiences.xlsx`
3. Populate all database tables
4. Generate and store 384-dimensional embeddings for semantic search
5. Set up audience segments and relationships

**The production code in `features/synthetic_audience/` assumes this setup is already complete.**

## 📊 Database Schema Overview

### Core Tables Created:

1. **`audience_segments`**
   - Stores audience segment definitions (University Students, Business Leaders, etc.)
   - Columns: id, segment_name, description, sample_size, audience_size, gender_split

2. **`trait_categories`**
   - Categorizes traits (demographics, purchasing_behavior, brand_preferences, etc.)
   - Columns: id, category_name, description, priority_level

3. **`traits`** (Master trait table)
   - All unique traits across all segments
   - Columns: id, trait_text, section, source_sheet, category_id, embedding (384-dim vector)
   - Uses **pgvector** extension for embedding storage

4. **`trait_probabilities`**
   - Probability of each trait for each audience segment
   - Columns: id, trait_id, segment_id, probability_value, is_demographic
   - Junction table linking traits to segments with probabilities

5. **`trait_relationships`**
   - Correlations between traits (co-occurrence patterns)
   - Columns: trait_a_id, trait_b_id, correlation_strength, segment_id

6. **`product_patterns`**
   - Product category patterns and typical trait associations
   - Columns: id, product_category, price_point, typical_traits, sample_campaigns

7. **`personas`**
   - Generated personas (runtime data, not setup data)
   - Columns: persona_uuid, segment, traits, demographics, behavioral_traits, narrative, etc.

8. **`query_cache`** (Not used - caching disabled)
   - Originally for caching query results
   - Columns: query_hash, query_text, segment_name, parsed_context, etc.

## 🚀 Setup Instructions

### Prerequisites

1. **PostgreSQL 12+** installed and running
2. **pgvector extension** installed:
   ```bash
   # On macOS with Homebrew
   brew install pgvector
   
   # On Ubuntu/Debian
   sudo apt-get install postgresql-12-pgvector
   ```

3. **Python dependencies**:
   ```bash
   pip install psycopg2-binary pandas openpyxl sentence-transformers numpy
   ```

4. **Database created**:
   ```bash
   createdb synthetic_personas
   # Or use existing database on port 5454
   ```

### Step-by-Step Setup

#### Option A: Complete Migration (Recommended)

Run the main migration script which does everything:

```bash
cd backend/features/synthetic_audience/database_setup
python phase2b_database_migration.py
```

**This script will:**
1. ✅ Create all tables with normalized schema
2. ✅ Read `Synthetic Audiences.xlsx`
3. ✅ Populate audience_segments (9 segments)
4. ✅ Populate trait_categories (15+ categories)
5. ✅ Populate traits master table (~800 unique traits)
6. ✅ Generate and store 384-dim embeddings for all traits
7. ✅ Populate trait_probabilities (traits × segments matrix)
8. ✅ Create trait_relationships (correlation patterns)
9. ✅ Populate product_patterns

**Expected Output:**
```
🏗️ CREATING NORMALIZED DATABASE SCHEMA
================================================================
📦 Enabling pgvector extension...
   ✅ pgvector extension enabled

📊 Creating audience_segments table...
   ✅ Created audience_segments table

📊 Creating trait_categories table...
   ✅ Created trait_categories table

📊 Creating traits_master table...
   ✅ Created traits table with pgvector

...

✅ NORMALIZED SCHEMA CREATION COMPLETE

📊 DATA MIGRATION COMPLETE
   - Audience segments: 9
   - Trait categories: 15
   - Unique traits: 847
   - Trait probabilities: 7623
   - Total embeddings generated: 847
```

**Time:** 5-10 minutes (depending on embedding generation)

#### Option B: Individual Table Creation

If you need to recreate specific tables only:

```bash
cd backend/features/synthetic_audience/database_setup/scripts

# Create specific trait tables
python create_beauty_table.py
python create_health_sports_table.py
python create_interests_lifestyle_table.py
python create_purchases_table.py

# Create relationships
python create_beauty_relationships.py
python create_health_sports_relationships.py
python create_interests_lifestyle_relationships.py
python create_purchases_relationships.py
python create_generic_relationships.py
```

#### Option C: Excel Conversion Only

If you need to convert Excel to CSV first:

```bash
cd backend/features/synthetic_audience/database_setup/converters

python convert_beauty_answers.py
python convert_health_sports.py
python convert_interests_lifestyle.py
python convert_purchases.py
```

This creates CSV files that can be imported separately.

### Troubleshooting

#### Issue: pgvector extension not found

**Error:** `ERROR: extension "pgvector" is not available`

**Solution:**
```bash
# Install pgvector extension
# macOS
brew install pgvector

# Ubuntu/Debian
sudo apt-get install postgresql-12-pgvector

# Then in psql
CREATE EXTENSION vector;
```

#### Issue: Embedding dimension mismatch

**Error:** `ERROR: expected 384 dimensions, not XXX dimensions`

**Solution:**
```bash
python fix_pgvector_dimensions.py
# Or regenerate embeddings
python regenerate_embeddings_with_context.py
```

#### Issue: Duplicate traits

**Error:** `ERROR: duplicate key value violates unique constraint`

**Solution:**
```bash
python scripts/fix_database_duplicates.py
```

#### Issue: Wrong database port

The migration script uses port **5454** by default:
```python
database_url = "postgresql://postgres:postgres@localhost:5454/synthetic_personas"
```

If your PostgreSQL is on port **5432**, edit the script:
```python
# Change to:
database_url = "postgresql://postgres:postgres@localhost:5432/synthetic_personas"
```

## 📋 Verification

After running the migration, verify the setup:

```bash
psql -h localhost -p 5454 -U postgres -d synthetic_personas
```

```sql
-- Check tables exist
\dt

-- Check audience segments
SELECT id, segment_name, sample_size FROM audience_segments;

-- Check trait count
SELECT COUNT(*) FROM traits;

-- Check embeddings are stored
SELECT COUNT(*) FROM traits WHERE embedding IS NOT NULL;

-- Check trait probabilities
SELECT COUNT(*) FROM trait_probabilities;

-- Verify a specific segment's traits
SELECT t.trait_text, tp.probability_value
FROM traits t
JOIN trait_probabilities tp ON t.id = tp.trait_id
JOIN audience_segments s ON tp.segment_id = s.id
WHERE s.segment_name = 'University Students'
ORDER BY tp.probability_value DESC
LIMIT 10;
```

**Expected Results:**
- 9 audience segments
- 15+ trait categories
- 800+ unique traits
- 800+ embeddings (one per trait)
- 7000+ trait probabilities (traits × segments)

## 🔄 When to Re-run

You only need to re-run these scripts if:

1. **Starting fresh** - New database or empty database
2. **Data changes** - `Synthetic Audiences.xlsx` updated with new traits
3. **Schema changes** - Database schema needs modifications
4. **Embedding updates** - Switching embedding models or fixing corrupted embeddings
5. **New segments** - Adding new audience segments

## 📝 Important Notes

1. **Embeddings:** Uses `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
   - These are contextual embeddings for semantic similarity
   - Generation takes 5-10 minutes for 800+ traits

2. **Source Data:** All trait data comes from `Synthetic Audiences.xlsx`
   - Contains sheets: Generic Answers, Beauty Answers, Health/Sports, Interests/Lifestyle, Purchases
   - Each sheet has traits with probabilities per segment

3. **Database:** PostgreSQL with **pgvector** extension is required
   - Standard PostgreSQL cannot store vector embeddings

4. **One-Time Setup:** Production code does NOT recreate tables
   - It only reads from and writes personas to existing tables

## 🎯 Next Steps

After database setup is complete:

1. ✅ Database is ready
2. ✅ Start the backend: `uvicorn main:app --reload --port 8010`
3. ✅ Production code in `features/synthetic_audience/` will work
4. ✅ Trait selection will use embeddings for semantic search
5. ✅ Persona generation will sample from trait probabilities

## 📚 Related Documentation

- **Developer Guide:** `backend/Synthetic_audience/synthetic-persona-developer-guide.md`
- **Migration Summary:** `backend/Synthetic_audience/PHASE2B_MIGRATION_SUMMARY_REPORT.md`
- **API Documentation:** `backend/features/synthetic_audience/api.py` (docstrings)
- **System Overview:** `PLATFORM_SERVICES_OVERVIEW.md` (project root)

---

**For questions or issues, refer to the copilot instructions in `.github/copilot-instructions.md`**
