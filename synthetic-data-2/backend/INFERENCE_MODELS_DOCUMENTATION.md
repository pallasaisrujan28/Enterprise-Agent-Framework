# Inference Models Documentation

## Overview
This document provides a comprehensive list of all inference models currently used in the Synthetic Data Generation System.

## Primary Models Used

### 1. AWS Bedrock Models

#### Anthropic Claude Models (Inference Profiles)
- **arn:aws:bedrock:us-west-2:866647877267:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0** (Primary)
  - Used in: Main generation engine, all agents (demographic, behavioral, narrative), LLM engine
  - Purpose: Primary model for persona generation using latest Claude Sonnet 4
  - Configuration: Default model in GenerationConfig
  - Location: `src/models/models.py`, `src/core/audience_engine.py`, `engines/llm_engine.py`

- **arn:aws:bedrock:us-west-2:866647877267:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0**
  - Used in: Ensemble configuration, test configurations
  - Purpose: Secondary model in ensemble mode
  - Weight: 0.9 in ensemble configuration
  - Location: `src/models/models.py`, `tests/test_bedrock.py`, `tests/bedrock_smoke.py`

- **arn:aws:bedrock:us-west-2:866647877267:inference-profile/us.amazon.nova-pro-v1:0**
  - Used in: Ensemble configuration, test configurations
  - Purpose: Alternative model for generation using Amazon Nova Pro
  - Weight: 0.8 in ensemble configuration
  - Location: `src/models/models.py`, `tests/test_bedrock.py`, `tests/bedrock_smoke.py`

#### Legacy Model References (Deprecated)
- **anthropic.claude-3-5-sonnet-20241022-v2:0** (Legacy)
  - Status: Replaced by inference profile ARN
  - Migration: Use global.anthropic.claude-sonnet-4-20250514-v1:0 inference profile

- **anthropic.claude-3-sonnet-20240229-v1:0** (Legacy)
  - Status: Replaced by inference profile ARN
  - Migration: Use us.anthropic.claude-3-7-sonnet-20250219-v1:0 inference profile

- **amazon.nova-pro-v1:0** (Legacy)
  - Status: Replaced by inference profile ARN
  - Migration: Use us.amazon.nova-pro-v1:0 inference profile

### 2. OpenAI Models

#### GPT Models
- **gpt-4-turbo-preview**
  - Used in: LLM persona service
  - Purpose: Fallback model for persona extraction
  - Location: `extraction/llm_persona_service.py`

- **gpt-3.5-turbo**
  - Used in: Legacy persona generation engine
  - Purpose: Basic persona generation
  - Location: `src/core/persona_generation_engine.py`

- **gpt-4**
  - Used in: Configuration validation
  - Purpose: Advanced model option
  - Location: `src/core/config_validation.py`

- **gpt-4-turbo**
  - Used in: Configuration validation
  - Purpose: Latest GPT model option
  - Location: `src/core/config_validation.py`

### 3. Anthropic Direct API Models

- **claude-3-5-sonnet-20241022**
  - Used in: Direct Anthropic API calls
  - Purpose: Persona extraction service
  - Location: `extraction/llm_persona_service.py`

## Model Configuration

### Default Configuration
```python
model_id: str = 'arn:aws:bedrock:us-west-2:866647877267:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0'
ensemble_model_ids: List[str] = [
    'arn:aws:bedrock:us-west-2:866647877267:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0',
    'arn:aws:bedrock:us-west-2:866647877267:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0',
    'arn:aws:bedrock:us-west-2:866647877267:inference-profile/us.amazon.nova-pro-v1:0'
]
```

### Ensemble Weights
```python
ensemble_weights: Dict[str, float] = {
    'arn:aws:bedrock:us-west-2:866647877267:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0': 1.0,
    'arn:aws:bedrock:us-west-2:866647877267:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0': 0.9,
    'arn:aws:bedrock:us-west-2:866647877267:inference-profile/us.amazon.nova-pro-v1:0': 0.8
}
```

## Inference Profiles

### Active Inference Profile ARNs
- **arn:aws:bedrock:us-west-2:866647877267:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0**
  - Profile: global.anthropic.claude-sonnet-4-20250514-v1:0
  - Region: Global (us-west-2 endpoint)
  - Model: Claude Sonnet 4 (Latest)

- **arn:aws:bedrock:us-west-2:866647877267:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0**
  - Profile: us.anthropic.claude-3-7-sonnet-20250219-v1:0
  - Region: US-specific
  - Model: Claude 3.7 Sonnet

- **arn:aws:bedrock:us-west-2:866647877267:inference-profile/us.amazon.nova-pro-v1:0**
  - Profile: us.amazon.nova-pro-v1:0
  - Region: US-specific
  - Model: Amazon Nova Pro

## Model Usage by Component

### Core Engine Components
1. **AudienceGenerationEngine**: Uses primary model_id and ensemble
2. **DemographicAgent**: anthropic.claude-3-5-sonnet-20241022-v2:0
3. **BehavioralAgent**: anthropic.claude-3-5-sonnet-20241022-v2:0
4. **NarrativeAgent**: anthropic.claude-3-5-sonnet-20241022-v2:0
5. **OutputFormatter**: anthropic.claude-3-sonnet-20240229-v1:0

### Supporting Services
1. **LLM Engine**: anthropic.claude-sonnet-4-20250514-v1:0
2. **LLM Persona Service**: Multiple (Anthropic, OpenAI, Bedrock)
3. **Persona Generation Engine**: gpt-3.5-turbo

## Environment Configuration

### Environment Variables
- `BEDROCK_MODEL_ID`: Primary Bedrock model
- `ENSEMBLE_MODEL_IDS`: Comma-separated list of ensemble models
- `OPENAI_API_KEY`: OpenAI API access
- `ANTHROPIC_API_KEY`: Direct Anthropic API access

### Configuration Files
- `.env.permanent`: Contains default Bedrock model ID
- `src/models/models.py`: Default model configurations
- `requirements.txt`: Model provider dependencies

## Model Selection Strategy

### Ensemble Mode
- **Rotation Strategy**: performance_based, round_robin, random
- **Aggregation Method**: consensus, first_success, weighted_voting, quality_ranking
- **Performance Tracking**: 50-request window for adaptive weighting

### Fallback Strategy
1. Primary Bedrock model
2. Ensemble models (if enabled)
3. Direct Anthropic API
4. OpenAI API
5. Legacy methods

## Model Performance Tracking

### Metrics Tracked
- Success rate
- Response time
- Quality scores
- Token usage
- Error rates

### Performance History
- Rolling window of recent requests
- Model-specific performance data
- Adaptive weight adjustment

## Dependencies

### Required Packages
- `boto3==1.35.60`: AWS Bedrock integration
- `anthropic==0.7.8`: Direct Anthropic API
- `openai`: OpenAI API integration
- `transformers==4.35.0`: Model utilities
- `sentence-transformers==2.2.2`: Embedding models

## Regional Configuration

### AWS Regions
- Primary: us-west-2
- Fallback: us-east-1
- Test: Various regions for inference profiles

## Security Considerations

- API keys stored in environment variables
- No hardcoded credentials in source code
- Secure credential management for production
- Rate limiting and retry mechanisms

## Future Model Integration

### Planned Models
- Additional Nova models
- Updated Claude versions
- Custom fine-tuned models
- Specialized domain models

### Integration Points
- Model factory pattern for easy addition
- Configuration-driven model selection
- Performance-based automatic switching
- A/B testing framework for new models

---

**Last Updated**: January 2025  
**Version**: 2.0.0  
**Maintainer**: Audience Generation System Team