# Copilot Instructions for Synthetic Persona Generation Platform

## 🎯 Platform Overview
Full-stack AI persona generation platform with **6 major services**: Standard Persona Generator, Text-to-Persona, Persona-to-Persona, Audience Generation, Persona Analysis Dashboard, and Persona Library. Built with Next.js 15 (App Router) frontend and FastAPI backend.

**See `PLATFORM_SERVICES_OVERVIEW.md` for complete service breakdown.**

## ⚠️ Critical Development Rules (CLAUDE.md)

**MUST follow iterative development**:
- Test EVERY feature immediately after implementation
- Verify results match expectations before proceeding
- NEVER use fallback/mock data when connections fail - fix or report the issue
- NO placeholder code, simulations, or rule-based fallbacks in production code
- Report errors immediately - don't continue with broken features
- NO summary .md files - explain through conversation only

## 🏗️ Architecture Overview

### Frontend Services (7 Pages)
1. **Landing Page** (`/`) - Auth bypass, feature showcase
2. **Dashboard** (`/dashboard`) - Navigation hub
3. **Persona Generator** (`/persona-generator`) - 10-step form-driven generation
4. **Text-to-Persona** (`/text-to-persona`) - Extract personas from text
5. **Persona-to-Persona** (`/persona-to-persona`) - Transform/merge/evolve personas
6. **Audience Generation** (`/audience-generation`) - Product-driven trait selection
7. **Persona Analysis** (`/persona-analysis`) - Analytics dashboard with clustering

### Backend Services (2 API Modules)
**Main API** (`backend/main.py`) - 13 endpoints for core persona operations
**Audience API** (`backend/Synthetic_audience/api/`) - 7 endpoints for product-driven generation

### Core Engines (5 Engines)
1. **HybridPersonaEngine** - Orchestrates 6 generation methods
2. **RuleBasedEngine** - Statistical demographic sampling
3. **LLMPersonaEngine** - AWS Bedrock Claude integration
4. **DiversityEngine** - Psychographic variation
5. **ClusteringEngine** - K-means, DBSCAN, hierarchical clustering

## 📁 Critical File Paths

### Backend (`backend/`)
```
main.py                                    # Main API (13 endpoints)
engines/
  ├── hybrid_engine.py                    # HybridPersonaEngine (6 generation methods)
  ├── rule_based_engine.py                # Statistical sampling
  ├── llm_engine.py                       # AWS Bedrock integration
  ├── reinforcement_engine.py             # RL-based generation
  └── adversarial_engine.py               # Quality validation
services/
  ├── clustering_engine.py                # K-means, DBSCAN, hierarchical
  ├── diversity_engine.py                 # Psychographic variation
  ├── evaluation_metrics.py               # Quality scoring
  ├── distribution_matcher.py             # Real-world alignment
  ├── bias_detection_service.py           # Bias analysis
  └── confidence_scoring_service.py       # Confidence calculation
extraction/
  ├── llm_persona_service.py              # Text-to-persona LLM calls
  ├── advanced_nlp_service.py             # NLP preprocessing
  └── demographic_extraction_service.py   # Pattern-based extraction
storage/
  └── file_storage.py                     # JSON persistence
Synthetic_audience/
  └── api/persona_api.py                  # Audience API (7 endpoints)
```

### Frontend (`frontend/src/`)
```
app/
  ├── page.tsx                            # Landing page (auth)
  ├── dashboard/page.tsx                  # Main hub
  ├── persona-generator/page.tsx          # 10-step form generation
  ├── text-to-persona/page.tsx            # Text extraction
  ├── persona-to-persona/page.tsx         # Transformation
  ├── audience-generation/page.tsx        # Product-driven
  ├── persona-analysis/page.tsx           # Analytics dashboard
  └── synthetic-audience/page.tsx         # Persona library
components/
  ├── persona/                            # Form, analytics, visualization
  ├── avatar/                             # 3D avatar configurator
  ├── three/                              # 3D scenes (robot, orbs)
  └── ui/                                 # Shared UI components
lib/
  └── api.ts                              # API client (all services)
store/
  └── avatarConfiguratorStore.ts          # Zustand state
```

### Import Patterns (CRITICAL - See IMPORT_REFERENCE.md)
**WRONG**: `from audience_orchestrator import AudienceOrchestrator`  
**RIGHT**: `from audience_generation_engine.Engine.core.audience_orchestrator import AudienceOrchestrator`

## 🚀 Development Workflows

### Running the System
```bash
# Backend (port 8010 - NOT 8000!)
cd backend && uvicorn main:app --reload --port 8010

# Frontend (port 3000)
cd frontend && npm run dev
```

**API Base URL**: `http://localhost:8010` (check `frontend/src/lib/api.ts`)

### Testing Persona Generation
```python
# In backend directory
from engines.hybrid_engine import HybridPersonaEngine, GenerationConfig, GenerationRequest, GenerationMethod

config = GenerationConfig(
    method=GenerationMethod.HYBRID_ADVANCED,
    sample_size=10,
    quality_threshold=0.7
)
request = GenerationRequest(config=config, persona_name="TestBatch")
result = await engine.generate_personas(request)
```

### AWS Credentials
Loaded from the environment in `backend/main.py` startup_event. Set these in
`backend/.env` (see `backend/.env.example`); never commit real values:
```python
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
```

## Key API Endpoints

### Persona Generation
- `POST /api/personas/generate` - Main generation (all methods)
- `POST /api/personas/batch-generate` - Alias for large batches
- `GET /api/personas` - List personas (pagination, filtering)
- `GET /api/personas/{id}` - Single persona details
- `GET /api/persona-names` - List persona folder names
- `GET /api/personas/by-name/{name}` - Get all variants of a name

### Analytics & Dashboards
- `GET /api/dashboard/analytics/{persona_folder_name}` - Clustering, bias, diversity
- `GET /api/dashboard/metrics` - System-wide quality/performance
- `POST /api/personas/by-name/{name}/analyze` - K-means clustering analysis

### Advanced Features
- `POST /api/text-to-persona` - Extract personas from text
- `POST /api/persona-to-persona` - Merge/evolve existing personas
- `/api/audience/*` - Audience generation router (separate module)

## Data Models & Validation

### Request Structure
```python
class PersonaGenerationRequest(BaseModel):
    sample_size: int = Field(default=10, ge=1, le=1000)
    generation_method: str = "hybrid_advanced"  # See GenerationMethod enum
    quality_threshold: float = 0.3
    enable_clustering: bool = True
    demographic_constraints: Optional[Dict[str, Any]]
    psychographic_preferences: Optional[Dict[str, Any]]
```

### Persona Output Structure
```json
{
  "demographics": {"age": 32, "gender": "female", "location": {...}},
  "psychographics": {"personality_traits": {...}, "values": {...}},
  "behavioral_patterns": {"shopping_habits": [...], "decision_factors": [...]},
  "narrative": "Combined narrative string from PersonaNarrative",
  "confidence_score": 0.85,
  "cluster_id": 2
}
```

### Storage Convention
Personas stored in `backend/data/personas/{persona_name}/persona_{id}.json`
Each folder = batch generation with same base name

## Quality & Evaluation

### Quality Metrics Calculated
- **Completeness**: Required fields populated
- **Consistency**: Logical attribute relationships (age-income, education-occupation)
- **Realism**: Demographic validity against real-world patterns
- **Diversity**: Simpson's index, Shannon entropy across psychographics
- **Bias Detection**: Gender/age/geographic distribution skew

### Clustering Analysis
Uses scikit-learn K-means with:
- Feature vectors: Big Five personality + values + age
- Silhouette score for quality
- PCA for 2D visualization
- Elbow method for optimal K

## LLM Integration Details

### Primary Model (See INFERENCE_MODELS_DOCUMENTATION.md)
- **Model**: Claude 3.5 Sonnet via AWS Bedrock
- **ARN**: `arn:aws:bedrock:us-west-2:866647877267:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0`
- **Ensemble Models**: Claude 3.7 Sonnet, Amazon Nova Pro (with weights)
- **Fallback Chain**: Bedrock → Anthropic Direct API → OpenAI

### Narrative Generation
`PersonaNarrative` object contains: background_story, day_in_life, goals_and_motivations, pain_points, decision_making_process, quote
Converted to string in API response (see `main.py` line 700-730)

## Common Gotchas

1. **Port Mismatch**: Backend runs on 8010, not 8000
2. **NumPy Serialization**: Use `convert_numpy_types()` helper before JSON responses
3. **Narrative Format**: PersonaNarrative is object, not string - convert for API
4. **Import Paths**: audience_generation_engine has deep nested structure
5. **Quality Threshold**: Default 0.3 (low) from env var - adjust per use case
6. **NLTK Downloads**: SSL cert handling needed (`ssl._create_unverified_context`)

## Frontend-Backend Integration

### API Call Pattern
```typescript
// In frontend/src/lib/api.ts
const response = await fetch(`${API_BASE_URL}/api/personas/generate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(transformFormDataToRequest(formData))
});
```

### Form Data Transformation
10-step form (`MultiStepForm.tsx`) → `transformFormDataToRequest()` → API request
Steps: Basic Info, Demographics, Personality, Behavioral, Media, Decision Making, Interests, Context, Goals, Review

### Visualization Stack
- **Clustering**: D3.js scatter plots with PCA projection
- **Charts**: Recharts for distributions (bar, pie, radar)
- **3D Avatar**: React Three Fiber (@react-three/fiber, @react-three/drei)
- **Animations**: Framer Motion, Lottie

## Dependencies of Note

### Backend Critical
- `fastapi==0.104.1`, `uvicorn==0.24.0` - API framework
- `boto3==1.35.60` - AWS Bedrock access
- `anthropic==0.7.8` - Direct API fallback
- `scikit-learn==1.3.0` - Clustering/ML
- `langgraph==0.6.7` - Conversation state (if using)
- `spacy`, `textblob`, `nltk` - NLP (text-to-persona)

### Frontend Critical
- `next@15.4.6` - App Router, Turbopack
- `react@19.1.0` - Latest React
- `zustand@5.0.7` - State management
- `d3@7.9.0` - Clustering viz
- `recharts@3.1.2` - Charts
- `@react-three/fiber@9.3.0` - 3D avatars

## When to Use Which Engine

- **rule_based**: Fast prototyping, deterministic output, no LLM costs
- **llm_only**: Rich narratives, creative personas, slower
- **hybrid_advanced**: Best quality, clustering + LLM + rules, default choice
- **distribution_matched**: Population-level accuracy, benchmarking
- **diversity_only**: Edge cases, maximum variation

## Environment Variables
```bash
# backend/.env
DEFAULT_QUALITY_THRESHOLD=0.3
AWS_ACCESS_KEY_ID=<set in code>
AWS_SECRET_ACCESS_KEY=<set in code>
AWS_DEFAULT_REGION=us-west-2
ANTHROPIC_API_KEY=<optional fallback>
OPENAI_API_KEY=<optional fallback>
```

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8010
```

---

**When in doubt**: Check CLAUDE.md for workflow rules, IMPORT_REFERENCE.md for paths, INFERENCE_MODELS_DOCUMENTATION.md for model configs
