'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { PersonaResponse, GenerationResponse } from '@/lib/api';

interface PersonaResultsProps {
  results: GenerationResponse | null;
  isLoading: boolean;
}

export default function PersonaResults({ results, isLoading }: PersonaResultsProps) {
  const [selectedPersona, setSelectedPersona] = useState<PersonaResponse | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  if (isLoading) {
    return (
      <Card className="p-6 bg-white/5 backdrop-blur-sm border border-white/10">
        <div className="flex items-center justify-center space-x-2">
          <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
          <span className="text-white">Generating personas...</span>
        </div>
      </Card>
    );
  }

  if (!results) {
    return (
      <Card className="p-6 bg-white/5 backdrop-blur-sm border border-white/10">
        <div className="text-center text-gray-400">
          <p>No personas generated yet. Configure your settings and click "Generate Personas" to begin.</p>
        </div>
      </Card>
    );
  }

  const { personas, generation_metadata, quality_metrics, clustering_results, execution_time, success, message, warnings, errors } = results;

  if (!success) {
    return (
      <Card className="p-6 bg-red-500/10 backdrop-blur-sm border border-red-500/20">
        <div className="text-red-400">
          <h3 className="text-lg font-semibold mb-2">Generation Failed</h3>
          <p className="mb-4">{message}</p>
          {errors && errors.length > 0 && (
            <div>
              <h4 className="font-medium mb-2">Errors:</h4>
              <ul className="list-disc list-inside space-y-1">
                {errors.map((error, index) => (
                  <li key={index} className="text-sm">{error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Generation Summary */}
      <Card className="p-6 bg-white/5 backdrop-blur-sm border border-white/10">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-xl font-semibold text-white mb-2">Generation Results</h3>
            <p className="text-gray-300">{message}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-400">Execution Time</p>
            <p className="text-lg font-semibold text-white">{execution_time.toFixed(2)}s</p>
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="bg-white/5 rounded-lg p-4">
            <p className="text-sm text-gray-400">Personas Generated</p>
            <p className="text-2xl font-bold text-white">{personas.length}</p>
          </div>
          <div className="bg-white/5 rounded-lg p-4">
            <p className="text-sm text-gray-400">Average Quality</p>
            <p className="text-2xl font-bold text-white">
              {personas.length > 0 ? (personas.reduce((sum, p) => sum + p.confidence_score, 0) / personas.length).toFixed(2) : 'N/A'}
            </p>
          </div>
          <div className="bg-white/5 rounded-lg p-4">
            <p className="text-sm text-gray-400">Generation Method</p>
            <p className="text-lg font-semibold text-white capitalize">
              {generation_metadata.generation_method?.replace('_', ' ')}
            </p>
          </div>
        </div>

        {/* Warnings */}
        {warnings && warnings.length > 0 && (
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 mb-4">
            <h4 className="text-yellow-400 font-medium mb-2">Warnings:</h4>
            <ul className="list-disc list-inside space-y-1 text-yellow-300 text-sm">
              {warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          </div>
        )}

        {/* View Mode Toggle */}
        <div className="flex justify-between items-center">
          <div className="flex space-x-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`px-3 py-1 rounded-md text-sm transition-colors ${
                viewMode === 'grid'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white/10 text-gray-300 hover:bg-white/20'
              }`}
            >
              Grid View
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1 rounded-md text-sm transition-colors ${
                viewMode === 'list'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white/10 text-gray-300 hover:bg-white/20'
              }`}
            >
              List View
            </button>
          </div>
          
          {clustering_results && (
            <div className="text-sm text-gray-400">
              Clusters: {clustering_results.n_clusters || 'N/A'}
            </div>
          )}
        </div>
      </Card>

      {/* Personas Display */}
      {personas.length > 0 ? (
        <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-4'}>
          {personas.map((persona, index) => (
            <PersonaCard
              key={persona.id || index}
              persona={persona}
              index={index}
              viewMode={viewMode}
              onClick={() => setSelectedPersona(persona)}
            />
          ))}
        </div>
      ) : (
        <Card className="p-6 bg-white/5 backdrop-blur-sm border border-white/10">
          <div className="text-center text-gray-400">
            <p>No personas were generated. Try adjusting your quality threshold or generation settings.</p>
          </div>
        </Card>
      )}

      {/* Detailed Persona Modal */}
      {selectedPersona && (
        <PersonaDetailModal
          persona={selectedPersona}
          onClose={() => setSelectedPersona(null)}
        />
      )}
    </div>
  );
}

interface PersonaCardProps {
  persona: PersonaResponse;
  index: number;
  viewMode: 'grid' | 'list';
  onClick: () => void;
}

function PersonaCard({ persona, index, viewMode, onClick }: PersonaCardProps) {
  const getPersonaName = () => {
    return persona.demographics?.name || 
           persona.demographics?.full_name || 
           `Persona ${index + 1}`;
  };

  const getPersonaAge = () => {
    return persona.demographics?.age || 
           persona.demographics?.age_range || 
           'Unknown';
  };



  const getPersonaLocation = () => {
    const location = persona.demographics?.location;
    if (typeof location === 'string') return location;
    if (typeof location === 'object' && location) {
      return `${location.city || ''}, ${location.state || ''}, ${location.country || ''}`.replace(/^,\s*|,\s*$/g, '');
    }
    return 'Unknown';
  };

  if (viewMode === 'list') {
    return (
      <Card 
        className="p-4 bg-white/5 backdrop-blur-sm border border-white/10 hover:bg-white/10 cursor-pointer transition-all duration-200"
        onClick={onClick}
      >
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center space-x-4">
              <div>
                <h4 className="text-lg font-semibold text-white">{getPersonaName()}</h4>
                <p className="text-gray-300">{getPersonaAge()}</p>
                <p className="text-gray-400 text-sm">{getPersonaLocation()}</p>
              </div>
            </div>
            {persona.narrative && (
              <p className="text-gray-300 text-sm mt-2 line-clamp-2">
                {persona.narrative.substring(0, 150)}...
              </p>
            )}
          </div>
          <div className="text-right">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-400">Quality:</span>
              <span className={`text-sm font-semibold ${
                persona.confidence_score >= 0.8 ? 'text-green-400' :
                persona.confidence_score >= 0.6 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {(persona.confidence_score * 100).toFixed(0)}%
              </span>
            </div>
            {persona.cluster_id !== undefined && (
              <div className="mt-1">
                <span className="text-xs bg-indigo-600/20 text-indigo-300 px-2 py-1 rounded">
                  Cluster {persona.cluster_id}
                </span>
              </div>
            )}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card 
      className="p-4 bg-white/5 backdrop-blur-sm border border-white/10 hover:bg-white/10 cursor-pointer transition-all duration-200"
      onClick={onClick}
    >
      <div className="text-center mb-4">
        <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full mx-auto mb-3 flex items-center justify-center">
          <span className="text-white font-bold text-xl">
            {getPersonaName().charAt(0).toUpperCase()}
          </span>
        </div>
        <h4 className="text-lg font-semibold text-white">{getPersonaName()}</h4>
        <p className="text-gray-300 text-sm">{getPersonaAge()}</p>
        <p className="text-gray-400 text-xs">{getPersonaLocation()}</p>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-400">Quality Score</span>
          <span className={`text-sm font-semibold ${
            persona.confidence_score >= 0.8 ? 'text-green-400' :
            persona.confidence_score >= 0.6 ? 'text-yellow-400' : 'text-red-400'
          }`}>
            {(persona.confidence_score * 100).toFixed(0)}%
          </span>
        </div>
        
        {persona.cluster_id !== undefined && (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400">Cluster</span>
            <span className="text-xs bg-indigo-600/20 text-indigo-300 px-2 py-1 rounded">
              {persona.cluster_id}
            </span>
          </div>
        )}
      </div>

      {persona.narrative && (
        <div className="mt-3 pt-3 border-t border-white/10">
          <p className="text-gray-300 text-xs line-clamp-3">
            {persona.narrative.substring(0, 100)}...
          </p>
        </div>
      )}
    </Card>
  );
}

interface PersonaDetailModalProps {
  persona: PersonaResponse;
  onClose: () => void;
}

// Component to format and display persona narrative with proper styling
function FormattedNarrative({ narrative }: { narrative: string }) {
  const formatNarrative = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let currentList: string[] = [];
    
    const flushList = () => {
      if (currentList.length > 0) {
        elements.push(
          <ul key={`list-${elements.length}`} className="list-disc list-inside space-y-1 ml-4 mb-3">
            {currentList.map((item, idx) => (
              <li key={idx} className="text-gray-300">
                {item}
              </li>
            ))}
          </ul>
        );
        currentList = [];
      }
    };
    
    lines.forEach((line, index) => {
      const trimmedLine = line.trim();
      
      // Handle headers
      if (trimmedLine.startsWith('# ')) {
        flushList();
        elements.push(
          <h1 key={index} className="text-2xl font-bold text-white mt-8 mb-4 first:mt-0 border-b border-gray-600 pb-2">
            {trimmedLine.substring(2)}
          </h1>
        );
      } else if (trimmedLine.startsWith('## ')) {
        flushList();
        elements.push(
          <h2 key={index} className="text-xl font-semibold text-blue-300 mt-6 mb-3">
            {trimmedLine.substring(3)}
          </h2>
        );
      } else if (trimmedLine.startsWith('### ')) {
        flushList();
        elements.push(
          <h3 key={index} className="text-lg font-medium text-green-300 mt-5 mb-2">
            {trimmedLine.substring(4)}
          </h3>
        );
      } else if (trimmedLine.startsWith('- ')) {
        // Collect list items
        currentList.push(trimmedLine.substring(2));
      } else if (trimmedLine.startsWith('**') && trimmedLine.endsWith('**')) {
        flushList();
        elements.push(
          <div key={index} className="font-semibold text-yellow-300 mt-4 mb-2 bg-yellow-300/10 px-3 py-2 rounded">
            {trimmedLine.slice(2, -2)}
          </div>
        );
      } else if (trimmedLine === '') {
        flushList();
        elements.push(<div key={index} className="h-2" />);
      } else if (trimmedLine.length > 0) {
        flushList();
        // Handle inline formatting
        const formattedText = trimmedLine
          .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-white">$1</strong>')
          .replace(/\*(.*?)\*/g, '<em class="italic text-blue-200">$1</em>');
        
        elements.push(
          <p 
            key={index} 
            className="text-gray-300 leading-relaxed mb-3 text-sm"
            dangerouslySetInnerHTML={{ __html: formattedText }}
          />
        );
      }
    });
    
    // Flush any remaining list items
    flushList();
    
    return elements;
  };

  return (
    <div className="max-h-96 overflow-y-auto pr-2 space-y-1">
      {formatNarrative(narrative)}
    </div>
  );
}

function PersonaDetailModal({ persona, onClose }: PersonaDetailModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <h2 className="text-2xl font-bold text-white">
              {persona.demographics?.name || persona.demographics?.full_name || 'Persona Details'}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Demographics */}
            <div className="bg-white/5 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-3">Demographics</h3>
              <div className="space-y-2 text-sm">
                {Object.entries(persona.demographics || {}).map(([key, value]) => {
                  // Handle location object
                  if (key === 'location' && typeof value === 'object' && value !== null) {
                    const locationStr = `${value.city || ''}, ${value.state || ''}, ${value.country || ''}`.replace(/^,\s*|,\s*$/g, '');
                    return (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                        <span className="text-white">{locationStr}</span>
                      </div>
                    );
                  }
                  // Handle device_preferences object
                  if (key === 'device_preferences' && typeof value === 'object' && value !== null) {
                    return (
                      <div key={key}>
                        <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                        <div className="ml-4 mt-1">
                          {Object.entries(value).map(([subKey, subValue]) => (
                            <div key={subKey} className="flex justify-between">
                              <span className="text-gray-500 capitalize">{subKey.replace('_', ' ')}:</span>
                              <span className="text-white">{String(subValue)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  }
                  // Handle arrays
                  if (Array.isArray(value)) {
                    return (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                        <span className="text-white">{value.join(', ')}</span>
                      </div>
                    );
                  }
                  // Handle other objects
                  if (typeof value === 'object' && value !== null) {
                    return (
                      <div key={key}>
                        <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                        <div className="ml-4 mt-1">
                          {Object.entries(value).map(([subKey, subValue]) => (
                            <div key={subKey} className="flex justify-between">
                              <span className="text-gray-500 capitalize">{subKey.replace('_', ' ')}:</span>
                              <span className="text-white">{String(subValue)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  }
                  // Handle primitive values
                  return (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                      <span className="text-white">{String(value)}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Psychographics */}
            <div className="bg-white/5 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-3">Psychographics</h3>
              <div className="space-y-4 text-sm">
                {/* Personality Traits */}
                {persona.psychographics?.personality && (
                  <div>
                    <h4 className="text-md font-medium text-gray-300 mb-2">Personality</h4>
                    <div className="space-y-1">
                      {Object.entries(persona.psychographics.personality).map(([trait, score]) => (
                        <div key={trait} className="flex justify-between">
                          <span className="text-gray-400 capitalize">{trait}:</span>
                          <span className="text-white">{typeof score === 'number' ? (score * 100).toFixed(1) + '%' : String(score)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Values */}
                {persona.psychographics?.values && (
                  <div>
                    <h4 className="text-md font-medium text-gray-300 mb-2">Values</h4>
                    <div className="space-y-1">
                      {Object.entries(persona.psychographics.values).map(([value, score]) => (
                        <div key={value} className="flex justify-between">
                          <span className="text-gray-400 capitalize">{value}:</span>
                          <span className="text-white">{typeof score === 'number' ? (score * 100).toFixed(1) + '%' : String(score)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Lifestyle */}
                {persona.psychographics?.lifestyle && (
                  <div>
                    <h4 className="text-md font-medium text-gray-300 mb-2">Lifestyle</h4>
                    <div className="space-y-1">
                      {Object.entries(persona.psychographics.lifestyle).map(([key, value]) => {
                        if (key === 'preferred_activities' && Array.isArray(value)) {
                          return (
                            <div key={key} className="flex justify-between">
                              <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                              <span className="text-white">{value.join(', ')}</span>
                            </div>
                          );
                        }
                        if (key === 'media_consumption' && typeof value === 'object' && value !== null) {
                           return (
                             <div key={key}>
                               <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                               <div className="ml-4 mt-1">
                                 {Object.entries(value).map(([subKey, subValue]) => (
                                   <div key={subKey} className="flex justify-between">
                                     <span className="text-gray-500 capitalize">{subKey.replace('_', ' ')}:</span>
                                     <span className="text-white">{String(subValue)}</span>
                                   </div>
                                 ))}
                               </div>
                             </div>
                           );
                         }
                        return (
                          <div key={key} className="flex justify-between">
                            <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                            <span className="text-white">{typeof value === 'number' ? (value * 100).toFixed(1) + '%' : String(value)}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                
                {/* Technology */}
                {persona.psychographics?.technology && (
                  <div>
                    <h4 className="text-md font-medium text-gray-300 mb-2">Technology</h4>
                    <div className="space-y-1">
                      {Object.entries(persona.psychographics.technology).map(([key, value]) => {
                        if (Array.isArray(value)) {
                          return (
                            <div key={key} className="flex justify-between">
                              <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                              <span className="text-white">{value.join(', ')}</span>
                            </div>
                          );
                        }
                        return (
                          <div key={key} className="flex justify-between">
                            <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                            <span className="text-white">{typeof value === 'number' ? (value * 100).toFixed(1) + '%' : String(value)}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Behavioral Patterns */}
            <div className="bg-white/5 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-3">Behavioral Patterns</h3>
              <div className="space-y-2 text-sm">
                {Object.entries(persona.behavioral_patterns || {}).map(([key, value]) => {
                  if (Array.isArray(value)) {
                    return (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                        <span className="text-white">{value.join(', ')}</span>
                      </div>
                    );
                  }
                  if (typeof value === 'object' && value !== null) {
                    return (
                      <div key={key}>
                        <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                        <div className="ml-4 mt-1">
                          {Object.entries(value).map(([subKey, subValue]) => (
                            <div key={subKey} className="flex justify-between">
                              <span className="text-gray-500 capitalize">{subKey.replace('_', ' ')}:</span>
                              <span className="text-white">{String(subValue)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  }
                  return (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                      <span className="text-white">{String(value)}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Quality Metrics */}
            <div className="bg-white/5 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-3">Quality Metrics</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Confidence Score:</span>
                  <span className={`font-semibold ${
                    persona.confidence_score >= 0.8 ? 'text-green-400' :
                    persona.confidence_score >= 0.6 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {(persona.confidence_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Generation Method:</span>
                  <span className="text-white capitalize">{persona.generation_method.replace('_', ' ')}</span>
                </div>
                {persona.cluster_id !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Cluster ID:</span>
                    <span className="text-white">{persona.cluster_id}</span>
                  </div>
                )}
                {persona.component_scores && Object.keys(persona.component_scores).length > 0 && (
                  <div className="mt-3">
                    <span className="text-gray-400 block mb-2">Component Scores:</span>
                    {Object.entries(persona.component_scores).map(([component, score]) => (
                      <div key={component} className="flex justify-between ml-4">
                        <span className="text-gray-500 text-xs capitalize">{component.replace('_', ' ')}:</span>
                        <span className="text-gray-300 text-xs">{Number(score).toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Narrative */}
          {persona.narrative && (
            <div className="mt-6 bg-white/5 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-3">Persona Narrative</h3>
              <FormattedNarrative narrative={persona.narrative} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}