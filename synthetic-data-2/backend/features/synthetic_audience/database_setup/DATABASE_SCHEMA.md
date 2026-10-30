# Database Schema - Table Relationships

## Entity Relationship Diagram

```
┌─────────────────────┐
│ audience_segments   │
│─────────────────────│
│ id (PK)            │◄────┐
│ segment_name       │     │
│ description        │     │
│ sample_size        │     │
│ audience_size      │     │
└─────────────────────┘     │
                            │
                            │
┌─────────────────────┐     │     ┌──────────────────────┐
│ trait_categories    │     │     │ trait_probabilities  │
│─────────────────────│     │     │──────────────────────│
│ id (PK)            │◄────┼─────┤ segment_id (FK)      │
│ category_name      │     │     │ trait_id (FK)        │
│ description        │     │     │ probability_value    │
│ priority_level     │     │     │ is_demographic       │
└─────────────────────┘     │     └──────────────────────┘
         ▲                  │              ▲
         │                  │              │
         │                  │              │
┌─────────────────────┐     │              │
│ traits (MASTER)     │     │              │
│─────────────────────│     │              │
│ id (PK)            │─────┘──────────────┘
│ trait_text         │
│ section            │
│ source_sheet       │
│ category_id (FK)   │
│ embedding (vector) │ ◄─── 384-dimensional semantic embedding
└─────────────────────┘
         ▲
         │
         │
┌─────────────────────┐
│ trait_relationships │
│─────────────────────│
│ trait_a_id (FK)    │
│ trait_b_id (FK)    │
│ correlation_strength│
│ segment_id (FK)    │
└─────────────────────┘
```

## Detailed Table Schemas

### 1. audience_segments
**Purpose:** Stores all target audience segment definitions

| Column              | Type         | Description                                |
|---------------------|--------------|-------------------------------------------|
| id                  | SERIAL PK    | Auto-incrementing primary key             |
| segment_name        | VARCHAR(100) | "University Students", "Business Leaders" |
| description         | TEXT         | Segment description                       |
| sample_size         | INTEGER      | Survey sample size                        |
| audience_size       | BIGINT       | Estimated total population size           |
| gender_split        | VARCHAR(50)  | Gender distribution (e.g., "50/50")      |
| original_column_name| VARCHAR(100) | Original Excel column reference          |
| created_at          | TIMESTAMP    | Record creation timestamp                 |

**Sample Data:**
```sql
| id | segment_name              | sample_size | audience_size |
|----|---------------------------|-------------|---------------|
| 1  | University Students       | 500         | 2000000       |
| 2  | Business Leaders          | 300         | 500000        |
| 3  | Healthcare Professionals  | 400         | 1200000       |
```

---

### 2. trait_categories
**Purpose:** Organizes traits into logical categories for weighting

| Column         | Type         | Description                                      |
|----------------|--------------|--------------------------------------------------|
| id             | SERIAL PK    | Auto-incrementing primary key                   |
| category_name  | VARCHAR(100) | "demographics", "purchasing_behavior", etc.     |
| description    | TEXT         | Category explanation                            |
| priority_level | INTEGER      | Weighting priority (1=high, 3=low)             |
| created_at     | TIMESTAMP    | Record creation timestamp                       |

**Sample Categories:**
- demographics
- purchasing_behavior
- brand_preferences
- social_influence
- technology_digital
- health_fitness
- media_consumption
- convenience_usage
- lifestyle_values
- decision_making
- online_behavior
- product_preferences
- shopping_habits
- payment_methods
- sustainability

---

### 3. traits (Master Trait Table)
**Purpose:** Central repository of all unique traits with embeddings

| Column       | Type         | Description                                    |
|--------------|--------------|-----------------------------------------------|
| id           | SERIAL PK    | Auto-incrementing primary key                |
| trait_text   | TEXT         | Human-readable trait description             |
| section      | VARCHAR(200) | Excel section/grouping                       |
| source_sheet | VARCHAR(100) | Excel sheet name ("Beauty Answers", etc.)    |
| category_id  | INTEGER FK   | Foreign key → trait_categories.id            |
| embedding    | VECTOR(384)  | Semantic embedding (pgvector)                |
| trait_type   | VARCHAR(50)  | "binary", "continuous", "categorical"        |
| created_at   | TIMESTAMP    | Record creation timestamp                    |

**Unique Index:** `trait_text` (no duplicates allowed)

**Sample Data:**
```sql
| id  | trait_text                        | section           | category        | embedding |
|-----|-----------------------------------|-------------------|-----------------|-----------|
| 1   | Social media updates              | Brand Discovery   | social_influence| [0.23...] |
| 2   | Product reviews                   | Research Methods  | online_behavior | [0.18...] |
| 3   | Premium skincare products         | Product Usage     | brand_pref      | [0.31...] |
```

---

### 4. trait_probabilities
**Purpose:** Junction table linking traits to segments with probability values

| Column            | Type      | Description                                  |
|-------------------|-----------|---------------------------------------------|
| id                | SERIAL PK | Auto-incrementing primary key              |
| trait_id          | INTEGER FK| Foreign key → traits.id                    |
| segment_id        | INTEGER FK| Foreign key → audience_segments.id         |
| probability_value | DECIMAL   | 0.0 to 1.0 (e.g., 0.75 = 75% probability) |
| is_demographic    | BOOLEAN   | True if demographic trait, False if behavioral|
| created_at        | TIMESTAMP | Record creation timestamp                  |

**Unique Index:** `(trait_id, segment_id)` (one probability per trait-segment pair)

**Sample Data:**
```sql
| trait_id | segment_id | trait_text           | segment_name      | probability |
|----------|------------|----------------------|-------------------|-------------|
| 1        | 1          | Social media updates | University Students| 0.89       |
| 1        | 2          | Social media updates | Business Leaders   | 0.42       |
| 2        | 1          | Product reviews      | University Students| 0.76       |
```

**Usage:** When generating personas for "University Students", sample traits based on these probabilities.

---

### 5. trait_relationships
**Purpose:** Stores correlations between traits (traits that co-occur)

| Column               | Type       | Description                              |
|---------------------|------------|------------------------------------------|
| trait_a_id          | INTEGER FK | Foreign key → traits.id (first trait)   |
| trait_b_id          | INTEGER FK | Foreign key → traits.id (second trait)  |
| correlation_strength| DECIMAL    | -1.0 to 1.0 (correlation coefficient)   |
| segment_id          | INTEGER FK | Foreign key → audience_segments.id       |
| created_at          | TIMESTAMP  | Record creation timestamp                |

**Primary Key:** `(trait_a_id, trait_b_id, segment_id)`

**Sample Data:**
```sql
| trait_a                  | trait_b                    | correlation | segment          |
|--------------------------|----------------------------|-------------|------------------|
| Premium brands           | High income                | 0.72        | Business Leaders |
| Social media updates     | Online shopping            | 0.65        | Uni Students     |
| Organic products         | Sustainability concerns    | 0.81        | Healthcare Pros  |
```

**Usage:** Used in archetype generation to ensure realistic trait combinations.

---

### 6. product_patterns
**Purpose:** Template patterns for common product categories and campaigns

| Column           | Type         | Description                                    |
|------------------|--------------|-----------------------------------------------|
| id               | SERIAL PK    | Auto-incrementing primary key                |
| product_category | VARCHAR(100) | "skincare", "fitness", "finance", etc.       |
| price_point      | VARCHAR(50)  | "luxury", "premium", "mid-range", "budget"   |
| typical_traits   | JSONB        | Array of commonly associated trait IDs       |
| sample_campaigns | TEXT         | Example campaign descriptions                |
| success_metrics  | JSONB        | Historical performance data                  |
| created_at       | TIMESTAMP    | Record creation timestamp                    |

**Sample Data:**
```json
{
  "product_category": "premium_fitness_tracker",
  "price_point": "premium",
  "typical_traits": [34, 67, 89, 102, 145],
  "sample_campaigns": "Smart fitness devices for health-conscious professionals"
}
```

---

### 7. personas (Runtime Generated Data)
**Purpose:** Stores generated personas (not setup data)

| Column             | Type      | Description                                  |
|-------------------|-----------|---------------------------------------------|
| id                | SERIAL PK | Auto-incrementing primary key              |
| persona_uuid      | UUID      | Unique identifier for persona              |
| segment           | VARCHAR   | Audience segment                           |
| campaign_query    | TEXT      | Product/campaign description               |
| traits            | JSONB     | All assigned traits                        |
| demographics      | JSONB     | Demographic traits subset                  |
| behavioral_traits | JSONB     | Behavioral traits subset                   |
| narrative         | TEXT      | LLM-generated persona narrative            |
| confidence_score  | DECIMAL   | Generation quality score (0-1)             |
| created_at        | TIMESTAMP | Generation timestamp                       |

**Sample JSON Structure:**
```json
{
  "persona_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "segment": "University Students",
  "traits": {
    "Social media updates": true,
    "Product reviews": true,
    "Budget shopping": true
  },
  "demographics": {
    "Age": "18-24",
    "Gender": "Female",
    "Location": "Urban"
  },
  "narrative": "Sarah is a 22-year-old university student..."
}
```

---

### 8. query_cache (Currently Disabled)
**Purpose:** Cache query results for performance (not currently used)

| Column            | Type      | Description                                |
|-------------------|-----------|--------------------------------------------|
| query_hash        | VARCHAR PK| SHA256 hash of query + segment             |
| query_text        | TEXT      | Original query string                      |
| segment_name      | VARCHAR   | Target segment                             |
| parsed_context    | JSONB     | Extracted context (price, category, etc.)  |
| selected_trait_ids| INTEGER[] | Array of selected trait IDs                |
| relevance_scores  | JSONB     | Scoring breakdown                          |
| hit_count         | INTEGER   | Number of times cache hit                  |
| last_accessed     | TIMESTAMP | Last cache access                          |
| created_at        | TIMESTAMP | Cache creation time                        |

**Note:** Query caching has been disabled per user request. System performs fresh searches every time.

---

## Data Flow

### 1. Database Setup (One-Time)
```
Synthetic Audiences.xlsx
         ↓
  phase2b_database_migration.py
         ↓
    ┌────────────────┐
    │ Create Tables  │
    └────────────────┘
         ↓
    ┌────────────────┐
    │ Read Excel     │
    └────────────────┘
         ↓
    ┌────────────────┐
    │ Generate       │
    │ Embeddings     │ ← sentence-transformers
    └────────────────┘
         ↓
    ┌────────────────┐
    │ Populate       │
    │ All Tables     │
    └────────────────┘
```

### 2. Trait Selection (Runtime)
```
User Query: "premium fitness tracker for University Students"
         ↓
  trait_selector.py (4-Layer System)
         ↓
Layer 1: Semantic Layer
    - Generate query embedding
    - Compare to all trait embeddings (cosine similarity)
         ↓
Layer 2: Contextual Layer
    - Extract price point (premium)
    - Extract category (fitness)
         ↓
Layer 3: Domain Knowledge Layer
    - Apply segment-specific weights (University Students)
    - Apply price point multipliers
         ↓
Layer 4: Dynamic Scoring
    - Combine: 70% semantic + 30% domain knowledge
    - Filter by minimum thresholds
    - Return top N traits with scores
         ↓
Selected Traits with Probabilities
```

### 3. Persona Generation (Runtime)
```
Selected Traits + Probabilities
         ↓
persona_generator.py
         ↓
Generate Archetypes (LLM)
    - "Budget-Conscious Student"
    - "Tech-Savvy Fitness Enthusiast"
    - etc.
         ↓
Assign Personas to Archetypes
         ↓
For Each Persona:
    - Sample traits based on archetype + probabilities
    - Ensure statistical accuracy
    - Generate LLM narrative (optional)
         ↓
Store in personas table
```

---

## Key Relationships

1. **Traits ← Probabilities → Segments**
   - One trait can have different probabilities for different segments
   - Example: "Social media updates" = 89% for Students, 42% for Business Leaders

2. **Traits → Categories**
   - Each trait belongs to one category
   - Categories have priority weights

3. **Traits ↔ Traits (Relationships)**
   - Traits can correlate with other traits
   - Used for realistic archetype generation

4. **Segments → Personas**
   - Generated personas belong to one segment
   - Inherit trait probabilities from that segment

---

## Indexes and Performance

**Critical Indexes:**
- `traits.trait_text` - UNIQUE index for fast lookups
- `trait_probabilities(trait_id, segment_id)` - UNIQUE composite index
- `traits.embedding` - pgvector index for semantic search (IVFFlat or HNSW)

**Embedding Search Performance:**
- 384-dimensional vectors
- ~800 traits = ~1ms search time with proper indexing
- Uses cosine similarity for semantic matching

---

## Summary

- **9 audience segments** (expandable)
- **15+ trait categories** (behavioral, demographic, preferences)
- **800+ unique traits** (from Excel source data)
- **7000+ trait-segment probabilities** (traits × segments matrix)
- **384-dim embeddings** for semantic search
- **Real-world statistical distributions** from survey data

**This schema enables:**
✅ Multi-segment persona generation
✅ Semantic trait selection (understands "premium skincare" = luxury + beauty)
✅ Statistical accuracy (personas match real-world distributions)
✅ Scalable trait library (add new traits/segments easily)
✅ Fast semantic search (pgvector indexing)
