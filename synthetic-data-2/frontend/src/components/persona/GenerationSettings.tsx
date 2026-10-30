'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { useFormContext } from './FormContext';
import personaConfig from '@/config/persona-config.json';

interface GenerationSettingsProps {
  onGenerate: (settings: GenerationSettings | ComprehensiveConfig) => void;
  onEditForm: () => void;
  isGenerating: boolean;
}

export interface GenerationSettings {
  sample_size: number;
  generation_method: string;
  quality_threshold: number;
  enable_clustering: boolean;
  distribution_matching: boolean;
  target_clusters?: number;
  export_format: string;
  project_name?: string;
  tags?: string[];
  formData?: any;
}

interface ComprehensiveConfig {
  personaConfiguration: any;
  generationSettings: any;
  validationRules: any;
  metadata: any;
}

const generationMethods = [
  { value: 'hybrid_advanced', label: 'Hybrid Advanced (Recommended)', description: 'Combines rule-based sampling with AI narratives' },
  { value: 'hybrid_basic', label: 'Hybrid Basic', description: 'Basic hybrid approach with standard features' },
  { value: 'rule_based', label: 'Rule-Based Only', description: 'Fast generation using predefined rules' },
  { value: 'llm_only', label: 'AI-Only', description: 'Full AI generation (slower but more creative)' },
  { value: 'diversity_only', label: 'Diversity Focused', description: 'Optimized for maximum persona diversity' },
  { value: 'distribution_matched', label: 'Distribution Matched', description: 'Matches real-world demographic distributions' }
];

const exportFormats = [
  { value: 'json', label: 'JSON' },
  { value: 'csv', label: 'CSV' },
  { value: 'both', label: 'Both (JSON + CSV)' }
];

export default function GenerationSettings({ onGenerate, onEditForm, isGenerating }: GenerationSettingsProps) {
  const { formData } = useFormContext();
  const [settings, setSettings] = useState<GenerationSettings>({
    sample_size: 10,
    generation_method: 'hybrid_advanced',
    quality_threshold: 0.3,
    enable_clustering: true,
    distribution_matching: true,
    target_clusters: undefined,
    export_format: 'json',
    project_name: '',
    tags: []
  });

  const [tagInput, setTagInput] = useState('');

  const handleSettingChange = (key: keyof GenerationSettings, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const addTag = () => {
    if (tagInput.trim() && !settings.tags?.includes(tagInput.trim())) {
      handleSettingChange('tags', [...(settings.tags || []), tagInput.trim()]);
      setTagInput('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    handleSettingChange('tags', settings.tags?.filter(tag => tag !== tagToRemove) || []);
  };

  const handleGenerate = () => {
    
    // Create comprehensive configuration by merging form data with config
    const comprehensiveConfig = {
      // Use form data if available, otherwise fall back to config defaults
      personaConfiguration: {
        basicInfo: formData.basicInfo || personaConfig.personaConfiguration.basicInfo,
        demographics: formData.demographics || personaConfig.personaConfiguration.demographics,
        personality: formData.personality || personaConfig.personaConfiguration.personality,
        behavioral: formData.behavioral || personaConfig.personaConfiguration.behavioral,
        mediaConsumption: formData.mediaConsumption || personaConfig.personaConfiguration.mediaConsumption,
        decisionMaking: formData.decisionMaking || personaConfig.personaConfiguration.decisionMaking,
        interests: formData.interests || personaConfig.personaConfiguration.interests,
        context: formData.context || personaConfig.personaConfiguration.context,
        goals: formData.goals || personaConfig.personaConfiguration.goals
      },
      generationSettings: {
        ...personaConfig.generationSettings,
        ...settings // Override with current UI settings
      },
      validationRules: personaConfig.validationRules,
      metadata: personaConfig.metadata
    };
    
    onGenerate(comprehensiveConfig);
  };

  return (
    <Card className="p-6 bg-white/5 backdrop-blur-sm border border-white/10">
      <h3 className="text-xl font-semibold text-white mb-6">Generation Settings</h3>
      
      <div className="space-y-6">
        {/* Sample Size */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Number of Personas
          </label>
          <input
            type="number"
            min="1"
            max="1000"
            value={settings.sample_size}
            onChange={(e) => handleSettingChange('sample_size', parseInt(e.target.value) || 1)}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Generation Method */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Generation Method
          </label>
          <select
            value={settings.generation_method}
            onChange={(e) => handleSettingChange('generation_method', e.target.value)}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {generationMethods.map(method => (
              <option key={method.value} value={method.value} className="bg-gray-800">
                {method.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-1">
            {generationMethods.find(m => m.value === settings.generation_method)?.description}
          </p>
        </div>

        {/* Quality Threshold */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Quality Threshold
          </label>
          <input
            type="number"
            min="0"
            max="1"
            step="0.1"
            value={settings.quality_threshold}
            onChange={(e) => handleSettingChange('quality_threshold', parseFloat(e.target.value) || 0)}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="0.0 - 1.0"
          />
          <p className="text-xs text-gray-400 mt-1">
            Range: 0.0 (Low) to 1.0 (High)
          </p>
        </div>

        {/* Advanced Options */}
        <div className="space-y-4">
          <h4 className="text-lg font-medium text-white">Advanced Options</h4>
          
          {/* Clustering */}
          <div className="flex items-center space-x-3">
            <input
              type="checkbox"
              id="clustering"
              checked={settings.enable_clustering}
              onChange={(e) => handleSettingChange('enable_clustering', e.target.checked)}
              className="w-4 h-4 text-indigo-600 bg-white/10 border-white/20 rounded focus:ring-indigo-500"
            />
            <label htmlFor="clustering" className="text-sm text-gray-300">
              Enable Clustering Analysis
            </label>
          </div>

          {/* Target Clusters */}
          {settings.enable_clustering && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Target Clusters (optional)
              </label>
              <input
                type="number"
                min="2"
                max="20"
                value={settings.target_clusters || ''}
                onChange={(e) => handleSettingChange('target_clusters', e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="Auto-detect"
                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          )}

          {/* Distribution Matching */}
          <div className="flex items-center space-x-3">
            <input
              type="checkbox"
              id="distribution"
              checked={settings.distribution_matching}
              onChange={(e) => handleSettingChange('distribution_matching', e.target.checked)}
              className="w-4 h-4 text-indigo-600 bg-white/10 border-white/20 rounded focus:ring-indigo-500"
            />
            <label htmlFor="distribution" className="text-sm text-gray-300">
              Enable Distribution Matching
            </label>
          </div>
        </div>

        {/* Export Format */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Export Format
          </label>
          <select
            value={settings.export_format}
            onChange={(e) => handleSettingChange('export_format', e.target.value)}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {exportFormats.map(format => (
              <option key={format.value} value={format.value} className="bg-gray-800">
                {format.label}
              </option>
            ))}
          </select>
        </div>

        {/* Project Name */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Project Name (optional)
          </label>
          <input
            type="text"
            value={settings.project_name || ''}
            onChange={(e) => handleSettingChange('project_name', e.target.value || undefined)}
            placeholder="Enter project name"
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Tags
          </label>
          <div className="flex space-x-2 mb-2">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addTag()}
              placeholder="Add tag"
              className="flex-1 px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={addTag}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Add
            </button>
          </div>
          {settings.tags && settings.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {settings.tags.map(tag => (
                <span
                  key={tag}
                  className="inline-flex items-center px-2 py-1 bg-indigo-600/20 text-indigo-300 text-sm rounded-md"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => removeTag(tag)}
                    className="ml-1 text-indigo-400 hover:text-indigo-200"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="space-y-3">
          {/* Edit Form Button */}
          {onEditForm && (
            <button
              onClick={onEditForm}
              disabled={isGenerating}
              className="w-full py-2 px-6 bg-gray-600 text-white font-medium rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              Edit Form Data
            </button>
          )}
          
          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="w-full py-3 px-6 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold rounded-lg hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
          >
            {isGenerating ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Generating Personas...</span>
              </div>
            ) : (
              'Generate Personas'
            )}
          </button>
        </div>
      </div>
    </Card>
  );
}