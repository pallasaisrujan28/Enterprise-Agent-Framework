'use client'

import React, { lazy, Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { useRouter } from 'next/navigation'
import { useAvatarConfiguratorStore } from '@/store/avatarConfiguratorStore'
import { Card } from '@/components/ui/card'
import { Sidebar } from '@/components/ui/sidebar'
import MultiStepForm from '@/components/persona/MultiStepForm'

// Lazy load heavy 3D components
const Experience = lazy(() => import('@/components/avatar/Experience').then(module => ({ default: module.Experience })))
import { 
  BasicInformationStep, 
  DemographicsStep, 
  PersonalityStep,
  BehavioralStep,
  InterestsStep,
  ReviewStep
} from '@/components/persona/FormSteps'
import GenerationSettings from '@/components/persona/GenerationSettings'
import PersonaResults from '@/components/persona/PersonaResults'
import { FormProvider, useFormContext } from '@/components/persona/FormContext'
import { apiService, transformFormDataToRequest, GenerationResponse, PersonaGenerationRequest } from '@/lib/api';
import { Header } from '@/components/ui/header'

import { useState, useEffect } from 'react'

interface GeneratedPersona {
  name: string;
  age: string;
  location: string;
  occupation: string;
  personality: string;
  interests: string[];
  goals: string;
  challenges: string;
}

const PersonaGeneratorContent = () => {
  const router = useRouter()
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [generatedPersona, setGeneratedPersona] = useState<GeneratedPersona | null>(null);
  const [currentView, setCurrentView] = useState<'form' | 'settings' | 'results'>('form');
  const [generationResults, setGenerationResults] = useState<GenerationResponse | null>(null);
  const [user, setUser] = useState<any>(null);
  const [showTypeSelector, setShowTypeSelector] = useState(false)
  const [selectedPersonaType, setSelectedPersonaType] = useState<'audience' | null>('audience');
  const [activeTab, setActiveTab] = useState<'configure' | 'results'>('configure');
  const { formData, updateFormData } = useFormContext();

  // Check authentication
  useEffect(() => {
    const userData = localStorage.getItem('user')
    if (userData) {
      setUser(JSON.parse(userData))
    } else {
      router.push('/')
    }
  }, [])
  
  const {
    fetchCategories
  } = useAvatarConfiguratorStore()

  useEffect(() => {
    fetchCategories()
    setMounted(true)
  }, [])

  const getFormSteps = (personaType: 'audience') => {
    const steps = [
      {
        id: 'basic',
        title: 'Basic Information',
        component: BasicInformationStep,
        isCompleted: false
      },
      {
        id: 'demographics',
        title: 'Demographics',
        component: DemographicsStep,
        isCompleted: false
      },
      {
        id: 'personality',
        title: 'Personality & Values',
        component: PersonalityStep,
        isCompleted: false
      },
      {
        id: 'behavioral',
        title: 'Behavioral Traits & Shopping',
        component: BehavioralStep,
        isCompleted: false
      },
      {
        id: 'interests',
        title: 'Interests & Brand Preferences',
        component: InterestsStep,
        isCompleted: false
      },
      {
        id: 'review',
        title: 'Review & Generate',
        component: ReviewStep,
        isCompleted: false
      },
      {
        id: 'settings',
        title: 'Generation Settings',
        component: () => (
          <GenerationSettings
            onGenerate={handleGeneratePersonas}
            isGenerating={isGenerating}
          />
        ),
        isCompleted: false
      }
    ];

    return steps;
  };

  const handleStepChange = (stepIndex: number) => {
  };

  const handleFormComplete = async (formData: any) => {
    // Form data is already managed by the FormContext through MultiStepForm
    // Settings is now part of the multi-step form, so this means generation should start
  };

  const handleDirectGeneration = async (formDataParam?: any) => {
    setIsGenerating(true);
    setCurrentView('results');
    
    try {
      // Use form data from context or parameter
      const currentFormData = formDataParam || formData;
      
      // Debug: Log the form data being used
      
      // Use the transformFormDataToRequest function for consistent field mapping
      const generationSettings = {
        sample_size: currentFormData.generationSettings?.sample_size || 10,
        generation_method: currentFormData.generationSettings?.generation_method || 'hybrid_basic',
        quality_threshold: currentFormData.generationSettings?.quality_threshold || 0.8,
        enable_clustering: currentFormData.generationSettings?.enable_clustering ?? true,
        distribution_matching: currentFormData.generationSettings?.distribution_matching ?? true,
        export_format: currentFormData.generationSettings?.export_format || 'json'
      };
      
      const request: PersonaGenerationRequest = transformFormDataToRequest(currentFormData, generationSettings);
      
      // Debug: Log the transformed request
      
      const results = await apiService.generatePersonas(request);
      setGenerationResults(results);
      
      // Automatically switch to Results tab after successful generation
      setActiveTab('results');
    } catch (error) {
      console.error('Error generating personas:', error);
      setGenerationResults({
        success: false,
        message: 'Failed to generate personas. Please try again.',
        personas: [],
        generation_metadata: {
          generation_method: 'hybrid_basic',
          sample_size: 5,
          quality_threshold: 0.8
        },
        quality_metrics: {},
        execution_time: 0,
        errors: [error instanceof Error ? error.message : 'Unknown error occurred']
      });
      
      // Switch to Results tab even on error to show error message
      setActiveTab('results');
    } finally {
      setIsGenerating(false);
    }
  };

  const handlePersonaTypeSelect = (type: 'audience') => {
    setSelectedPersonaType(type);
    setShowTypeSelector(false);
  };

  const handleBackToTypeSelection = () => {
    setShowTypeSelector(true);
    setSelectedPersonaType(null);
    setCurrentView('form');
  };

  const handleGeneratePersonas = async (configOrSettings: any) => {
    setIsGenerating(true);
    setCurrentView('results');
    
    try {
      // Debug: Log the configuration received
      
      let request: PersonaGenerationRequest;
      
      // Check if we received a comprehensive config or just settings
      if (configOrSettings.personaConfiguration && configOrSettings.generationSettings) {
        // Handle comprehensive configuration
        const config = configOrSettings;
        
        request = {
          sample_size: config.generationSettings.sample_size,
          generation_method: config.generationSettings.generation_method,
          quality_threshold: config.generationSettings.quality_threshold,
          enable_clustering: config.generationSettings.enable_clustering,
          distribution_matching: config.generationSettings.distribution_matching,
          target_clusters: config.generationSettings.target_clusters,
          export_format: config.generationSettings.export_format,
          project_name: config.generationSettings.project_name,
          tags: config.generationSettings.tags,
          
          // Transform persona configuration to backend format
          demographic_constraints: {
            age_range: config.personaConfiguration.basicInfo?.ageRange,
            gender_distribution: config.personaConfiguration.basicInfo?.genderDistribution,
            location_preferences: config.personaConfiguration.basicInfo?.location ? [JSON.stringify(config.personaConfiguration.basicInfo.location)] : undefined,
            occupation_categories: config.personaConfiguration.demographics?.occupation ? [config.personaConfiguration.demographics.occupation] : undefined,
            education_requirements: config.personaConfiguration.demographics?.education ? [config.personaConfiguration.demographics.education] : undefined,
            income_constraints: config.personaConfiguration.demographics?.income,
            family_status_options: config.personaConfiguration.demographics?.familyStatus ? [config.personaConfiguration.demographics.familyStatus] : undefined,
          },
          
          psychographic_preferences: {
            personality_traits: config.personaConfiguration.personality?.traits,
            values: config.personaConfiguration.personality?.values,
            lifestyle: config.personaConfiguration.personality?.lifestyle,
            interests: config.personaConfiguration.interests?.primary,
            interest_categories: config.personaConfiguration.interests?.categories,
          },
          
          behavioral_patterns: {
            price_sensitivity: config.personaConfiguration.behavioral?.priceSensitivity,
            brand_loyalty: config.personaConfiguration.behavioral?.brandLoyalty,
            online_shopping_preference: config.personaConfiguration.behavioral?.onlineShoppingPreference,
            innovation_vs_tradition: config.personaConfiguration.behavioral?.innovationVsTradition,
            individual_vs_community: config.personaConfiguration.behavioral?.individualVsCommunity,
            security_vs_adventure: config.personaConfiguration.behavioral?.securityVsAdventure,
            media_platforms: config.personaConfiguration.mediaConsumption?.platforms,
            media_influences: config.personaConfiguration.mediaConsumption?.influences,
            decision_making_style: config.personaConfiguration.decisionMaking?.style,
            decision_influences: config.personaConfiguration.decisionMaking?.influences,
          },
          
          industry_context: config.personaConfiguration.context?.industry,
          use_case_context: `${config.personaConfiguration.context?.productCategory} - ${config.personaConfiguration.context?.useCase}`,
        };
      } else {
        // Handle legacy settings format
        request = transformFormDataToRequest(formData, configOrSettings);
      }
      
      // Debug: Log the final request
      
      const results = await apiService.generatePersonas(request);
      setGenerationResults(results);
    } catch (error) {
      console.error('Error generating personas:', error);
      setGenerationResults({
        success: false,
        message: 'Failed to generate personas. Please try again.',
        personas: [],
        generation_metadata: {
          generation_method: configOrSettings.generation_method || configOrSettings.generationSettings?.generation_method,
          sample_size: configOrSettings.sample_size || configOrSettings.generationSettings?.sample_size,
          quality_threshold: configOrSettings.quality_threshold || configOrSettings.generationSettings?.quality_threshold
        },
        quality_metrics: {},
        execution_time: 0,
        errors: [error instanceof Error ? error.message : 'Unknown error occurred']
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleBackToForm = () => {
    setCurrentView('form');
  };

  const handleBackToSettings = () => {
    setCurrentView('settings');
  };

  const handleEditForm = () => {
    setCurrentView('form');
  };

  const handleNewGeneration = () => {
    setGenerationResults(null);
    setCurrentView('form');
  };

  const handleComplete = () => {
    // This function is now handled by handleFormComplete which uses the real API
    handleFormComplete(formData);
  };

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#130f30' }}>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} currentPage="persona-generator" />
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          title="Persona Generator"
          subtitle="Generate personas with visual representation"
          user={user}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          variant="light"
        />



        {/* Main Content Area - Fixed Height */}
        <main className="flex-1 flex px-6 pb-6 overflow-hidden">
          <div className="flex w-full space-x-6 h-full">
             {/* 3D Avatar Preview Area */}
             <div className="w-1/3 relative">
               <Card className={`bg-white/5 backdrop-blur-md border-gray-200/20 overflow-hidden transition-all duration-1000 ${
                 isGenerating ? 'ring-4 ring-yellow-400/50 shadow-2xl shadow-yellow-400/20' : ''
               }`} style={{height: 'calc(100% - 50px)'}}>
                 <div className="h-full p-4">
                   {mounted && (
                     <Canvas
                         shadows
                         camera={{ position: [0, -2, 18], fov: 60 }}
                         className="h-full w-full"
                       >
                       <Suspense fallback={<mesh><boxGeometry args={[1, 1, 1]} /><meshBasicMaterial color="#444" /></mesh>}>
                         <Experience isGenerating={isGenerating} />
                       </Suspense>
                     </Canvas>
                   )}
                 </div>
                 
                 {/* Golden Aura Effect */}
                 {isGenerating && (
                   <div className="absolute inset-0 bg-gradient-to-br from-yellow-400/10 via-orange-500/5 to-yellow-600/10 rounded-lg animate-pulse pointer-events-none">
                     <div className="absolute inset-0 bg-gradient-to-br from-yellow-400/5 to-orange-500/5 rounded-lg animate-ping"></div>
                   </div>
                 )}
               </Card>
             </div>

             {/* Tabbed Interface */}
              <div className="w-2/3 bg-transparent relative flex flex-col">
                {/* Tab Navigation */}
                <div className="flex border-b border-white/20 mb-6">
                  <button
                    onClick={() => setActiveTab('configure')}
                    className={`px-6 py-3 font-semibold transition-all duration-200 border-b-2 ${
                      activeTab === 'configure'
                        ? 'text-white border-blue-400 bg-white/5'
                        : 'text-gray-400 border-transparent hover:text-white hover:border-gray-400'
                    }`}
                  >
                    Configure
                  </button>
                  <button
                    onClick={() => setActiveTab('results')}
                    className={`px-6 py-3 font-semibold transition-all duration-200 border-b-2 ${
                      activeTab === 'results'
                        ? 'text-white border-blue-400 bg-white/5'
                        : 'text-gray-400 border-transparent hover:text-white hover:border-gray-400'
                    }`}
                  >
                    Results
                    {generationResults && (
                      <span className="ml-2 px-2 py-1 bg-green-500 text-white text-xs rounded-full">
                        {generationResults.personas?.length || 0}
                      </span>
                    )}
                  </button>
                </div>

                {/* Tab Content */}
                <div className="flex-1 overflow-y-auto scrollbar-dark">
                  {activeTab === 'configure' && (
                    <div className="p-6 relative">
                      <FormProvider>
                        <MultiStepForm 
                          steps={getFormSteps('audience')}
                          onStepChange={handleStepChange}
                          onComplete={handleFormComplete}
                        />
                      </FormProvider>
                      
                      {/* Loading Animation Overlay for Form Section */}
                      {isGenerating && (
                        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-purple-900/20 to-blue-900/20 backdrop-blur-sm rounded-lg transition-all duration-1000 z-50">
                          <div className="text-center">
                            <div className="w-20 h-20 bg-gradient-to-br from-yellow-400 via-orange-500 to-yellow-600 rounded-full animate-pulse flex items-center justify-center mb-4 mx-auto shadow-2xl">
                              <div className="w-12 h-12 bg-gradient-to-br from-yellow-300 to-orange-400 rounded-full animate-spin"></div>
                            </div>
                            <p className="text-white text-lg font-semibold animate-pulse">Generating Persona...</p>
                            <div className="mt-2 flex justify-center space-x-1">
                              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {activeTab === 'results' && (
                    <div className="p-6">
                      {!generationResults ? (
                        <div className="text-center py-12">
                          <div className="text-gray-400 mb-4">
                            <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                          </div>
                          <h3 className="text-xl font-semibold text-white mb-2">No Personas Generated Yet</h3>
                          <p className="text-gray-400 mb-6">Configure your persona settings and generate personas to see results here.</p>
                          <button
                            onClick={() => setActiveTab('configure')}
                            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all duration-200"
                          >
                            Go to Configure
                          </button>
                        </div>
                      ) : (
                        <div>
                          <PersonaResults 
                            results={generationResults} 
                            isLoading={isGenerating}
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  }

const PersonaGenerator = () => {
  return (
    <FormProvider>
      <PersonaGeneratorContent />
    </FormProvider>
  );
};

export default PersonaGenerator;