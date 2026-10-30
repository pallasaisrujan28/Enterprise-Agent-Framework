// API service layer for backend communication

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

// Types matching backend models
export interface PersonaGenerationRequest {
  sample_size: number;
  demographic_constraints?: Record<string, any>;
  psychographic_preferences?: Record<string, any>;
  behavioral_patterns?: Record<string, any>;
  generation_method: string;
  quality_threshold: number;
  enable_clustering: boolean;
  distribution_matching: boolean;
  target_clusters?: number;
  industry_context?: string;
  use_case_context?: string;
  export_format: string;
  project_name?: string;
  tags?: string[];
}

export interface PersonaResponse {
  id?: string;
  demographics: Record<string, any>;
  psychographics: Record<string, any>;
  behavioral_patterns: Record<string, any>;
  narrative?: string;
  generation_method: string;
  confidence_score: number;
  cluster_id?: number;
  component_scores?: Record<string, any>;
}

export interface GenerationResponse {
  personas: PersonaResponse[];
  generation_metadata: Record<string, any>;
  quality_metrics: Record<string, any>;
  clustering_results?: Record<string, any>;
  distribution_analysis?: Record<string, any>;
  storage_ids?: string[];
  export_paths?: string[];
  execution_time: number;
  success: boolean;
  message: string;
  warnings?: string[];
  errors?: string[];
}

export interface DashboardMetrics {
  total_personas: number;
  generation_methods: Record<string, number>;
  quality_distribution: Record<string, number>;
  recent_activity: Array<{
    timestamp: string;
    action: string;
    count: number;
  }>;
}

export interface PersonaNameInfo {
  persona_name: string;
  persona_count: number;
  created_at: string;
  last_updated: string;
}

export interface PersonaFolderInfo {
  name: string;
  persona_count: number;
  folder_path: string;
}

export interface PersonaAnalytics {
  folder_name: string;
  total_personas: number;
  relationship_analysis: {
    silhouette_score: number;
    cluster_visualization: Array<{
      persona_id: string;
      name: string;
      x: number;
      y: number;
      cluster: number;
      age: number;
      gender: string;
    }>;
    similarity_matrix: number[][];
    cluster_centers: Array<{
      cluster: number;
      x: number;
      y: number;
      size: number;
    }>;
  };
  quality_assessment: {
    average_quality_scores: Record<string, {
      mean: number;
      std: number;
      min: number;
      max: number;
    }>;
    uniqueness_distribution: number[];
    completeness_stats: Record<string, any>;
    consistency_metrics: Record<string, any>;
  };
  diversity_metrics: {
    diversity_index: number;
    psychographic_diversity: Record<string, {
      mean: number;
      std: number;
      range: number;
    }>;
    demographic_coverage: Record<string, number>;
    feature_importance: Record<string, number>;
  };
  bias_indicators: {
    gender_bias_score: number;
    age_distribution_skew: number;
    geographic_concentration: number;
    bias_alerts: string[];
  };
  demographic_distribution: {
    age_distribution: Record<string, number>;
    gender_distribution: Record<string, number>;
    income_distribution: Record<string, number>;
    education_distribution: Record<string, number>;
  };
  timestamp: string;
}

export interface AnalysisData {
  clustering: {
    personas: Array<{
      id: string;
      x: number;
      y: number;
      cluster: number;
      [key: string]: any;
    }>;
    cluster_centers: Array<{ x: number; y: number; cluster: number }>;
    feature_names: string[];
  };
  bias: {
    gender_distribution?: Record<string, number>;
    gender_bias_score?: number;
    age_distribution?: {
      mean: number;
      std: number;
      min: number;
      max: number;
    };
    income_distribution?: Record<string, number>;
    education_distribution?: Record<string, number>;
    location_distribution?: Record<string, number>;
  };
  diversity: {
    total_personas?: number;
    unique_clusters?: number;
    silhouette_score?: number;
    inertia?: number;
    pca_explained_variance?: number[];
    feature_importance?: Record<string, number>;
  };
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          message: `HTTP ${response.status}: ${response.statusText}`
        }));
        throw new ApiError(response.status, errorData.message || response.statusText);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(0, `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // Generate personas
  async generatePersonas(request: PersonaGenerationRequest): Promise<GenerationResponse> {
    return this.request<GenerationResponse>('/api/personas/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Batch generate personas
  async batchGeneratePersonas(request: PersonaGenerationRequest): Promise<GenerationResponse> {
    return this.request<GenerationResponse>('/api/personas/batch-generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Get dashboard metrics
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    return this.request<DashboardMetrics>('/api/dashboard/metrics');
  }

  // Get personas with pagination and filtering
  async getPersonas(params: {
    limit?: number;
    offset?: number;
    sort_by?: string;
    sort_order?: string;
    search?: string;
    project_name?: string;
  } = {}): Promise<{
    personas: PersonaResponse[];
    total: number;
    limit: number;
    offset: number;
  }> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, value.toString());
      }
    });

    const endpoint = `/api/personas${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return this.request(endpoint);
  }

  // Get single persona by ID
  async getPersona(personaId: string): Promise<PersonaResponse> {
    return this.request<PersonaResponse>(`/api/personas/${personaId}`);
  }

  // Persona folder-based methods
  async getPersonaFolders(): Promise<PersonaFolderInfo[]> {
    const response = await this.request<{
      persona_folders: PersonaFolderInfo[];
      total_folders: number;
      timestamp: string;
    }>('/api/persona-names');
    return response.persona_folders;
  }

  async getPersonaAnalytics(folderName: string): Promise<PersonaAnalytics> {
    return this.request<PersonaAnalytics>(`/api/dashboard/analytics/${encodeURIComponent(folderName)}`);
  }

  async getPersonasByName(personaName: string): Promise<PersonaResponse[]> {
    return this.request<PersonaResponse[]>(`/api/personas/by-name/${encodeURIComponent(personaName)}`);
  }

  async analyzePersonasByName(personaName: string, nClusters: number = 5): Promise<AnalysisData> {
    return this.request<AnalysisData>(`/api/personas/by-name/${encodeURIComponent(personaName)}/analyze?n_clusters=${nClusters}`, {
      method: 'POST'
    });
  }

  async deletePersonasByName(personaName: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(`/api/personas/by-name/${encodeURIComponent(personaName)}`, {
      method: 'DELETE'
    });
  }

  async healthCheck(): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>('/api/health');
  }

  // ========== AUDIENCE GENERATION API METHODS ==========

  // Get evaluation templates
  async getEvaluationTemplates(): Promise<{
    success: boolean;
    templates: Record<string, {
      name: string;
      description: string;
      focus_areas: string[];
      rating_scale: string;
    }>;
    count: number;
  }> {
    return this.request('/api/audience/templates');
  }

  // Select traits for audience generation
  async selectTraits(params: {
    campaign_query: string;
    audience_segment: string;
    max_traits?: number;
  }): Promise<{
    success: boolean;
    campaign_info: Record<string, any>;
    selection_summary: Record<string, any>;
    traits: Array<Record<string, any>>;
    trait_categories_breakdown: Record<string, any>;
    session_id: string;
  }> {
    return this.request('/api/audience/select-traits', {
      method: 'POST',
      body: JSON.stringify({
        campaign_query: params.campaign_query,
        audience_segment: params.audience_segment,
        max_traits: params.max_traits || 50,
      }),
    });
  }

  // Update selected traits
  async updateTraits(params: {
    session_id: string;
    traits: Array<Record<string, any>>;
    campaign_query: string;
    audience_segment: string;
  }): Promise<{
    success: boolean;
    message: string;
    traits_count: number;
    session_id: string;
  }> {
    return this.request('/api/audience/update-traits', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  // Generate audience personas
  async generateAudiencePersonas(params: {
    session_id: string;
    num_personas: number;
    traits: Array<Record<string, any>>;
    campaign_query: string;
    audience_segment: string;
    include_narratives?: boolean;
  }): Promise<{
    success: boolean;
    generation_id: string;
    personas_generated: number;
    personas_stored: number;
    persona_uuids: string[];
    summary: Record<string, any>;
  }> {
    return this.request('/api/audience/generate-personas', {
      method: 'POST',
      body: JSON.stringify({
        ...params,
        include_narratives: params.include_narratives ?? true,
      }),
    });
  }

  // Get audience personas
  async getAudiencePersonas(params: {
    generation_id?: string;
    audience_segment?: string;
    campaign_query?: string;
    limit?: number;
  } = {}): Promise<{
    success: boolean;
    personas: Array<{
      persona_uuid: string;
      campaign_context: string;
      generation_timestamp: string;
      segment_id: number;
      segment_name?: string;
      narrative_summary?: string;
    }>;
    groups?: Array<{
      group_name: string;
      segment_name: string;
      campaign_context: string;
      persona_count: number;
    }>;
    count: number;
  }> {
    return this.request('/api/audience/get-personas', {
      method: 'POST',
      body: JSON.stringify({
        generation_id: params.generation_id,
        audience_segment: params.audience_segment,
        campaign_query: params.campaign_query,
        limit: params.limit || 100,
      }),
    });
  }

  // Get persona detail
  async getPersonaDetail(persona_uuid: string): Promise<{
    success: boolean;
    persona: {
      uuid: string;
      segment: string;
      campaign_context: string;
      generation_timestamp: string;
      demographics: Record<string, any>;
      behavioral_traits: Record<string, any>;
      all_traits: Record<string, any>;
      narrative: string | null;
      metadata: Record<string, any>;
    };
  }> {
    return this.request('/api/audience/get-persona-detail', {
      method: 'POST',
      body: JSON.stringify({ persona_uuid }),
    });
  }

  // Evaluate audience with template
  async evaluateAudience(params: {
    product_description: string;
    audience_segment: string;
    template_key: string;
    num_personas?: number;
    existing_generation_id?: string;
  }): Promise<{
    success: boolean;
    evaluation_metadata: Record<string, any>;
    template_details: Record<string, any>;
    collective_feedback: {
      summary: string;
      num_evaluations: number;
      consensus_level: string;
    };
    individual_evaluations: Array<{
      persona_uuid: string;
      segment: string;
      evaluation: string;
      persona_summary: Record<string, any>;
    }>;
    statistical_summary: Record<string, any>;
    key_insights: string[];
  }> {
    return this.request('/api/audience/evaluate-audience', {
      method: 'POST',
      body: JSON.stringify({
        product_description: params.product_description,
        audience_segment: params.audience_segment,
        template_key: params.template_key,
        num_personas: params.num_personas || 10,
        existing_generation_id: params.existing_generation_id,
      }),
    });
  }

  // Chat with persona using LangGraph memory
  async chatWithPersona(params: {
    persona_uuid: string;
    user_message: string;
    conversation_id?: string;
    template_context?: Record<string, any>;
    product_context?: string;
  }): Promise<{
    conversation_id: string;
    persona_uuid: string;
    user_message: string;
    assistant_message: string;
    full_history: Array<{ role: string; content: string }>;
    persona_context: Record<string, any>;
    timestamp: string;
  }> {
    return this.request('/api/audience/chat-with-memory', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  // Get conversation history
  async getConversationHistory(conversation_id: string): Promise<{
    success: boolean;
    conversation_id: string;
    history: Record<string, any>;
  }> {
    return this.request(`/api/audience/conversation/${conversation_id}`);
  }

  // ========== GROUP AND MEDIA CHAT METHODS ==========

  // Chat with entire audience group (supports optional media upload)
  async chatWithGroup(params: {
    audience_group: string;
    user_message: string;
    mediaFile?: File | null;
    conversation_id?: string | null;
  }): Promise<{
    success: boolean;
    audience_group: string;
    num_personas: number;
    collective_response: string;
    individual_responses: Array<{ persona_uuid: string; response: string; persona_summary: string }>;
    has_media: boolean;
    timestamp: string;
  }> {
    const formData = new FormData();
    formData.append('audience_group', params.audience_group);
    formData.append('user_message', params.user_message);
    if (params.conversation_id) formData.append('conversation_id', params.conversation_id);
    if (params.mediaFile) formData.append('media_file', params.mediaFile);

    const response = await fetch(`${API_BASE_URL}/api/audience/chat-with-group`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError(response.status, errorText || 'Failed to chat with group');
    }

    return response.json();
  }

  // Enhanced individual persona chat (supports optional media upload)
  async chatWithPersonaEnhanced(params: {
    persona_uuid: string;
    user_message: string;
    mediaFile?: File | null;
    conversation_id?: string | null;
  }): Promise<{
    success: boolean;
    persona_uuid: string;
    response: string;
    conversation_history: Array<{ role: string; content: string }>;
    has_media: boolean;
    timestamp: string;
  }> {
    const formData = new FormData();
    formData.append('persona_uuid', params.persona_uuid);
    formData.append('user_message', params.user_message);
    if (params.conversation_id) formData.append('conversation_id', params.conversation_id);
    if (params.mediaFile) formData.append('media_file', params.mediaFile);

    const response = await fetch(`${API_BASE_URL}/api/audience/chat-with-persona-enhanced`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError(response.status, errorText || 'Failed to chat with persona');
    }

    return response.json();
  }
}

// Export singleton instance
export const apiService = new ApiService();
export { ApiError };

// Utility function to transform frontend form data to backend request
export function transformFormDataToRequest(
  formData: any,
  generationSettings: {
    sample_size: number;
    generation_method: string;
    quality_threshold: number;
    enable_clustering: boolean;
    distribution_matching: boolean;
    target_clusters?: number;
    export_format: string;
    project_name?: string;
    tags?: string[];
  }
): PersonaGenerationRequest {
  return {
    sample_size: generationSettings.sample_size,
    generation_method: generationSettings.generation_method,
    quality_threshold: generationSettings.quality_threshold,
    enable_clustering: generationSettings.enable_clustering,
    distribution_matching: generationSettings.distribution_matching,
    target_clusters: generationSettings.target_clusters,
    export_format: generationSettings.export_format,
    project_name: generationSettings.project_name,
    tags: generationSettings.tags,
    
    // Transform form data to backend constraints
    demographic_constraints: {
      age_range: formData.basicInfo?.ageRange,
      gender_distribution: formData.basicInfo?.genderDistribution ? (() => {
        const malePercent = formData.basicInfo.genderDistribution.male / 100;
        const femalePercent = formData.basicInfo.genderDistribution.female / 100;
        const nonBinaryPercent = 0.02;
        const totalBinaryPercent = malePercent + femalePercent;
        const adjustmentFactor = (1.0 - nonBinaryPercent) / totalBinaryPercent;
        
        return {
          Male: malePercent * adjustmentFactor,
          Female: femalePercent * adjustmentFactor,
          'Non-binary': nonBinaryPercent
        };
      })() : undefined,
      location_preferences: formData.basicInfo?.location ? [JSON.stringify(formData.basicInfo.location)] : undefined,
      occupation_categories: formData.demographics?.occupation ? [formData.demographics.occupation] : undefined,
      education_requirements: formData.demographics?.education ? [formData.demographics.education] : undefined,
      income_constraints: formData.demographics?.income,
      family_status_options: formData.demographics?.familyStatus ? [formData.demographics.familyStatus] : undefined,
    },
    
    psychographic_preferences: {
      personality_traits: formData.personality?.traits,
      values: formData.personality?.values,
      lifestyle: formData.personality?.lifestyle,
      interests: formData.interests?.primary,
      interest_categories: formData.interests?.categories,
    },
    
    behavioral_patterns: {
      price_sensitivity: formData.behavioral?.priceSensitivity,
      brand_loyalty: formData.behavioral?.brandLoyalty,
      online_shopping_preference: formData.behavioral?.onlineShoppingPreference,
      innovation_vs_tradition: formData.behavioral?.innovationVsTradition,
      individual_vs_community: formData.behavioral?.individualVsCommunity,
      security_vs_adventure: formData.behavioral?.securityVsAdventure,
      media_platforms: formData.mediaConsumption?.platforms,
      media_influences: formData.mediaConsumption?.influences,
      decision_making_style: formData.decisionMaking?.style,
      decision_influences: formData.decisionMaking?.influences,
    },
    
    industry_context: formData.context?.industry,
    use_case_context: `${formData.context?.productCategory} - ${formData.context?.useCase}`,
  };
}