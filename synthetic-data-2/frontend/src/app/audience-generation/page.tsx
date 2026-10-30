'use client'

import React, { useState, useEffect, useRef, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { Sidebar } from '@/components/ui/sidebar'
import { Header } from '@/components/ui/header'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import LoadingAnimation from '@/components/LoadingAnimation'
import AdvancedRobotScene from '@/components/three/AdvancedRobotScene'
import { apiService } from '@/lib/api'
import {
  Users,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowRight,
  Target,
  TrendingUp,
  Loader2,
  User,
  Brain
} from 'lucide-react'

// Audience segments from backend
const AUDIENCE_SEGMENTS = [
  'University Students',
  'Business Leaders',
  'Finance Professionals',
  'Media Professionals',
  'Healthcare Professionals',
  'Legal Services',
  'Government Workers',
  'Hospitality Workers',
  'Manufacturing Workers'
]

type Step = 'input' | 'traits' | 'generation' | 'complete'

interface Trait {
  trait_id: number
  trait_name: string
  section?: string
  category: string
  trait_type: string
  relevance_score: number
  probability: number
  selected: boolean
}

const AudienceGenerationPage = () => {
  const router = useRouter()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [step, setStep] = useState<Step>('input')

  // Form state
  const [productDescription, setProductDescription] = useState('')
  const [selectedSegment, setSelectedSegment] = useState('')
  const [numPersonas, setNumPersonas] = useState(10)

  // API state
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState('')
  const [traits, setTraits] = useState<Trait[]>([])
  const [traitCategories, setTraitCategories] = useState<Record<string, any>>({})
  const [error, setError] = useState('')
  const [generationResult, setGenerationResult] = useState<any>(null)

  // Robot animation state (robot cycles automatically between walk, wave, and jump)
  const [robotAnimation, setRobotAnimation] = useState<'idle' | 'walking' | 'running' | 'celebrating' | 'thinking' | 'death'>('walking')

  useEffect(() => {
    const userData = localStorage.getItem('user')
    if (userData) {
      setUser(JSON.parse(userData))
    } else {
      router.push('/')
    }
  }, [router])

  const handleTraitSelection = async () => {
    if (!productDescription || !selectedSegment) {
      setError('Please fill in all fields')
      return
    }

    setIsLoading(true)
    setError('')
    setRobotAnimation('death') // Robot dies when processing starts

    try {
      const response = await apiService.selectTraits({
        campaign_query: productDescription,
        audience_segment: selectedSegment,
        max_traits: 50
      })

      if (response.success) {
        setSessionId(response.session_id)
        setTraits(response.traits.map(t => ({ ...t, selected: true })))
        setTraitCategories(response.trait_categories_breakdown)
        setStep('traits')
        setRobotAnimation('idle') // Robot stops and waves
      }
    } catch (err: any) {
      setError(err.message || 'Failed to select traits')
      setRobotAnimation('walking') // Return to walking on error
    } finally {
      setIsLoading(false)
    }
  }

  const handleTraitToggle = (traitId: number) => {
    setTraits(prev =>
      prev.map(t => t.trait_id === traitId ? { ...t, selected: !t.selected } : t)
    )
  }

  const handleGenerateAudience = async () => {
    setIsLoading(true)
    setError('')

    try {
      const selectedTraits = traits.filter(t => t.selected)

      await apiService.updateTraits({
        session_id: sessionId,
        traits: selectedTraits,
        campaign_query: productDescription,
        audience_segment: selectedSegment
      })

      setStep('generation')
      await handleGeneratePersonas()
    } catch (err: any) {
      setError(err.message || 'Failed to update traits')
      setIsLoading(false)
    }
  }

  const handleGeneratePersonas = async () => {
    try {
      const selectedTraits = traits.filter(t => t.selected)

      const response = await apiService.generateAudiencePersonas({
        session_id: sessionId,
        num_personas: numPersonas,
        traits: selectedTraits,
        campaign_query: productDescription,
        audience_segment: selectedSegment,
        include_narratives: true
      })

      if (response.success) {
        setGenerationResult(response)
        setStep('complete')

        // Store generation ID for future reference
        localStorage.setItem('last_generation_id', response.generation_id)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate personas')
    } finally {
      setIsLoading(false)
    }
  }

  const handleViewAudience = () => {
    if (generationResult) {
      router.push(`/synthetic-audience`)
    }
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen" style={{ backgroundColor: '#130f30' }}>
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#130f30' }}>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} currentPage="audience-generation" />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          title="Audience Generation"
          subtitle="Create synthetic audience personas for your product"
          user={user}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          variant="light"
        />

        <main className="flex-1 overflow-hidden flex flex-col h-full">
          {/* TOP SECTION - Two boxes side by side (40-60 split) */}
          <div className="h-full flex">
            {/* LEFT BOX - 40% - Robot */}
            <div className="w-[40%] border-2 border-white/20 bg-gradient-to-br from-slate-900 via-blue-900/30 to-purple-900/30 relative">
              <AdvancedRobotScene animationState={robotAnimation} className="w-full h-full" />
            </div>

            {/* RIGHT BOX - 60% - Form Content */}
            <div className="w-[60%] border-2 border-white/20 bg-gradient-to-br from-purple-900/20 via-blue-900/20 to-indigo-900/20 flex flex-col h-full">
              {/* Form Content Area - Expanded vertically */}
              <div className="flex-1 flex flex-col p-6 h-full">
                {error && (
                  <Alert className="mb-8 bg-red-500/10 border-red-500/50">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                    <AlertDescription className="text-red-200">{error}</AlertDescription>
                  </Alert>
                )}

                {/* Form content takes most of the space with expanded vertical spacing */}
                <div className="flex-1 overflow-y-auto py-4">
                  <AnimatePresence mode="wait">
                    {step === 'input' && (
                      <div className="h-full flex flex-col justify-center">
                        <ProductInputStep
                          productDescription={productDescription}
                          setProductDescription={setProductDescription}
                          selectedSegment={selectedSegment}
                          setSelectedSegment={setSelectedSegment}
                          numPersonas={numPersonas}
                          setNumPersonas={setNumPersonas}
                          onSubmit={handleTraitSelection}
                          isLoading={isLoading}
                        />
                      </div>
                    )}

                    {step === 'traits' && (
                      <div className="h-full flex flex-col">
                        <TraitSelectionStep
                          traits={traits}
                          traitCategories={traitCategories}
                          onTraitToggle={handleTraitToggle}
                          onSubmit={handleGenerateAudience}
                          isLoading={isLoading}
                          onBack={() => setStep('input')}
                        />
                      </div>
                    )}

                    {step === 'generation' && (
                      <div className="h-full flex flex-col justify-center">
                        <GenerationStep numPersonas={numPersonas} />
                      </div>
                    )}

                    {step === 'complete' && generationResult && (
                      <div className="h-full flex flex-col justify-center">
                        <CompleteStep
                          result={generationResult}
                          onViewAudience={handleViewAudience}
                        />
                      </div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Form Pages Indicator - Fixed at bottom with more spacing */}
                <div className="mt-8 pt-6 border-t border-white/20 flex-shrink-0">
                  <div className="flex justify-center space-x-3">
                    <div className={`px-4 py-3 rounded text-sm font-medium ${step === 'input' ? 'bg-blue-500 text-white' : 'bg-gray-600 text-gray-300'}`}>
                      Input
                    </div>
                    <div className={`px-4 py-3 rounded text-sm font-medium ${step === 'traits' ? 'bg-blue-500 text-white' : 'bg-gray-600 text-gray-300'}`}>
                      Traits
                    </div>
                    <div className={`px-4 py-3 rounded text-sm font-medium ${step === 'generation' ? 'bg-blue-500 text-white' : 'bg-gray-600 text-gray-300'}`}>
                      Generate
                    </div>
                    <div className={`px-4 py-3 rounded text-sm font-medium ${step === 'complete' ? 'bg-blue-500 text-white' : 'bg-gray-600 text-gray-300'}`}>
                      Done
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

// Step Indicator Component
const StepIndicator = ({ step, current, completed, label }: { step: number, current: boolean, completed: boolean, label: string }) => (
  <div className="flex flex-col items-center">
    <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all ${
      current ? 'border-blue-400 bg-blue-500/30 text-blue-200' :
      completed ? 'border-green-400 bg-green-500/30 text-green-200' :
      'border-gray-500 bg-gray-700/30 text-gray-400'
    }`}>
      {completed ? <CheckCircle2 className="w-4 h-4" /> : <span className="text-xs font-bold">{step}</span>}
    </div>
    <span className={`text-[10px] mt-1 font-medium ${current ? 'text-blue-200' : completed ? 'text-green-300' : 'text-gray-400'}`}>
      {label}
    </span>
  </div>
)

// Product Input Step Component
const ProductInputStep = ({ productDescription, setProductDescription, selectedSegment, setSelectedSegment, numPersonas, setNumPersonas, onSubmit, isLoading }: any) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -20 }}
  >
    <Card className="bg-white/10 backdrop-blur-md border-white/20 p-8">
      <div className="space-y-6">
        <div>
          <h3 className="text-2xl font-bold text-white mb-2 flex items-center">
            <Target className="w-6 h-6 mr-2 text-blue-400" />
            Define Your Product
          </h3>
          <p className="text-gray-300">Describe your product or service to generate relevant audience personas</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-200 mb-2">
            Product Description
          </label>
          <textarea
            value={productDescription}
            onChange={(e) => setProductDescription(e.target.value)}
            className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[120px]"
            placeholder="e.g., Premium anti-aging serum with retinol - $200 per bottle, scientifically proven to reduce fine lines by 34% in 12 weeks"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-200 mb-2">
            Target Audience Segment
          </label>
          <Select value={selectedSegment} onValueChange={setSelectedSegment}>
            <SelectTrigger className="w-full bg-white/5 border-white/20 text-white">
              <SelectValue placeholder="Select audience segment" />
            </SelectTrigger>
            <SelectContent>
              {AUDIENCE_SEGMENTS.map(segment => (
                <SelectItem key={segment} value={segment}>{segment}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-200 mb-2">
            Number of Personas: {numPersonas}
          </label>
          <input
            type="range"
            min="5"
            max="50"
            value={numPersonas}
            onChange={(e) => setNumPersonas(parseInt(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>5</span>
            <span>50</span>
          </div>
        </div>

        <Button
          onClick={onSubmit}
          disabled={isLoading || !productDescription || !selectedSegment}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white py-3"
          size="lg"
        >
          {isLoading ? (
            <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Selecting Traits...</>
          ) : (
            <>Select Traits <ArrowRight className="w-5 h-5 ml-2" /></>
          )}
        </Button>
      </div>
    </Card>
  </motion.div>
)

// Trait Selection Step Component
const TraitSelectionStep = ({ traits, traitCategories, onTraitToggle, onSubmit, isLoading, onBack }: any) => {
  const selectedCount = traits.filter((t: Trait) => t.selected).length
  const [categoryFilter, setCategoryFilter] = useState<string>('all')

  const categories = ['all', ...Object.keys(traitCategories)]
  const filteredTraits = categoryFilter === 'all'
    ? traits
    : traits.filter((t: Trait) => t.category === categoryFilter)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="h-full flex flex-col"
    >
      <Card className="bg-white/10 backdrop-blur-md border-white/20 p-8 flex-1 flex flex-col">
        <div className="flex flex-col h-full space-y-6">
          {/* Header Section - Fixed */}
          <div className="flex justify-between items-center flex-shrink-0">
            <div>
              <h3 className="text-2xl font-bold text-white mb-2 flex items-center">
                <Sparkles className="w-6 h-6 mr-2 text-blue-400" />
                Select Audience Traits
              </h3>
              <p className="text-gray-300">
                {selectedCount} of {traits.length} traits selected
              </p>
            </div>

            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-56 bg-white/5 border-white/20 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {categories.map(cat => (
                  <SelectItem key={cat} value={cat}>
                    {cat === 'all' ? 'All Categories' : cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Traits List - Expanded to fill available space */}
          <div className="flex-1 overflow-y-auto space-y-3 pr-2">
            {filteredTraits.map((trait: Trait) => (
              <TraitItem key={trait.trait_id} trait={trait} onToggle={onTraitToggle} />
            ))}
          </div>

          {/* Button Section - Fixed at bottom */}
          <div className="flex space-x-4 flex-shrink-0 pt-4 border-t border-white/10">
            <Button
              onClick={onBack}
              variant="outline"
              className="flex-1 border-white/20 text-white hover:bg-white/10"
              size="lg"
            >
              Back
            </Button>
            <Button
              onClick={onSubmit}
              disabled={isLoading || selectedCount === 0}
              className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white"
              size="lg"
            >
              {isLoading ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Generating...</>
              ) : (
                <>Generate Audience <ArrowRight className="w-5 h-5 ml-2" /></>
              )}
            </Button>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}

// Trait Item Component
const TraitItem = ({ trait, onToggle }: { trait: Trait, onToggle: (id: number) => void }) => {
  // Create full display text with section context
  const displayText = trait.section && trait.section !== "Unknown Section"
    ? `${trait.section}: ${trait.trait_name}`
    : trait.trait_name

  return (
    <div
      onClick={() => onToggle(trait.trait_id)}
      className={`flex items-center justify-between p-5 rounded-lg cursor-pointer transition-all ${
        trait.selected
          ? 'bg-blue-500/20 border-2 border-blue-500 shadow-lg shadow-blue-500/20'
          : 'bg-white/5 border-2 border-transparent hover:bg-white/10 hover:border-white/20'
      }`}
    >
      <div className="flex-1 flex items-center space-x-4">
        <div className={`w-6 h-6 rounded border-2 flex items-center justify-center flex-shrink-0 ${
          trait.selected ? 'bg-blue-500 border-blue-500' : 'border-gray-400'
        }`}>
          {trait.selected && <CheckCircle2 className="w-5 h-5 text-white" />}
        </div>
        <div className="flex-1">
          <p className="text-white font-medium text-base mb-1.5">{displayText}</p>
          <div className="flex items-center space-x-3">
            <Badge variant="outline" className="text-xs px-2 py-0.5 border-white/30 text-gray-300">
              {trait.category}
            </Badge>
            <span className="text-xs text-gray-400 flex items-center">
              <span className="inline-block w-2 h-2 rounded-full bg-green-400 mr-1.5"></span>
              Relevance: {(trait.relevance_score * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
      <div className="text-right ml-4 flex-shrink-0">
        <p className="text-lg font-semibold text-white">{(trait.probability * 100).toFixed(1)}%</p>
        <p className="text-xs text-gray-400">probability</p>
      </div>
    </div>
  )
}

// Generation Step Component with Cool Animation
const GenerationStep = ({ numPersonas }: { numPersonas: number }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.9 }}
    animate={{ opacity: 1, scale: 1 }}
    exit={{ opacity: 0, scale: 0.9 }}
  >
    <Card className="bg-white/10 backdrop-blur-md border-white/20 p-12">
      <div className="text-center space-y-8">
        {/* Animated Icon Grid */}
        <div className="flex justify-center">
          <div className="relative w-32 h-32">
            {/* Central rotating circle */}
            <motion.div
              className="absolute inset-0 rounded-full border-4 border-blue-500/30"
              animate={{ rotate: 360 }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            />
            
            {/* Orbiting personas */}
            {[0, 1, 2, 3].map((i) => (
              <motion.div
                key={i}
                className="absolute w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center"
                style={{
                  top: '50%',
                  left: '50%',
                  marginTop: '-20px',
                  marginLeft: '-20px',
                }}
                animate={{
                  x: [0, Math.cos((i * Math.PI) / 2) * 50, 0],
                  y: [0, Math.sin((i * Math.PI) / 2) * 50, 0],
                  scale: [1, 1.2, 1],
                  opacity: [0.5, 1, 0.5],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  delay: i * 0.5,
                  ease: "easeInOut"
                }}
              >
                <User className="w-5 h-5 text-white" />
              </motion.div>
            ))}
            
            {/* Center pulsing icon */}
            <motion.div
              className="absolute inset-0 flex items-center justify-center"
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              <Sparkles className="w-12 h-12 text-blue-400" />
            </motion.div>
          </div>
        </div>

        {/* Title with gradient animation */}
        <div>
          <motion.h3 
            className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 mb-2"
            animate={{ 
              backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'],
            }}
            transition={{ duration: 3, repeat: Infinity }}
            style={{ backgroundSize: '200% 200%' }}
          >
            Generating Your Audience
          </motion.h3>
          <p className="text-gray-300 text-lg">
            Creating {numPersonas} realistic synthetic personas...
          </p>
        </div>

        {/* Progress bar */}
        <div className="max-w-md mx-auto space-y-4">
          <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"
              animate={{ x: ['-100%', '100%'] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
            />
          </div>
          
          {/* Status messages */}
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <p className="text-sm text-gray-400">
              Analyzing demographics, psychographics, and behavioral patterns...
            </p>
          </motion.div>
          
          {/* Stats cards */}
          <div className="grid grid-cols-3 gap-3 mt-6">
            <motion.div 
              className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3"
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 1, repeat: Infinity, delay: 0 }}
            >
              <Users className="w-6 h-6 text-blue-400 mx-auto mb-1" />
              <p className="text-xs text-gray-400">Demographics</p>
            </motion.div>
            
            <motion.div 
              className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3"
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 1, repeat: Infinity, delay: 0.3 }}
            >
              <Brain className="w-6 h-6 text-purple-400 mx-auto mb-1" />
              <p className="text-xs text-gray-400">Psychology</p>
            </motion.div>
            
            <motion.div 
              className="bg-pink-500/10 border border-pink-500/30 rounded-lg p-3"
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 1, repeat: Infinity, delay: 0.6 }}
            >
              <TrendingUp className="w-6 h-6 text-pink-400 mx-auto mb-1" />
              <p className="text-xs text-gray-400">Behaviors</p>
            </motion.div>
          </div>
        </div>
      </div>
    </Card>
  </motion.div>
)

// Complete Step Component
const CompleteStep = ({ result, onViewAudience }: any) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.9 }}
    animate={{ opacity: 1, scale: 1 }}
  >
    <Card className="bg-white/10 backdrop-blur-md border-white/20 p-12">
      <div className="text-center space-y-6">
        <div className="flex justify-center">
          <div className="w-24 h-24 rounded-full bg-green-500/20 flex items-center justify-center">
            <CheckCircle2 className="w-16 h-16 text-green-400" />
          </div>
        </div>

        <div>
          <h3 className="text-3xl font-bold text-white mb-2">
            Audience Generated Successfully!
          </h3>
          <p className="text-gray-300 text-lg">
            {result.personas_generated} personas created and ready for analysis
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
          <div className="bg-white/5 rounded-lg p-4">
            <p className="text-gray-400 text-sm">Personas Generated</p>
            <p className="text-3xl font-bold text-white">{result.personas_generated}</p>
          </div>
          <div className="bg-white/5 rounded-lg p-4">
            <p className="text-gray-400 text-sm">Stored in Database</p>
            <p className="text-3xl font-bold text-white">{result.personas_stored}</p>
          </div>
        </div>

        <Button
          onClick={onViewAudience}
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-4 text-lg"
          size="lg"
        >
          View Your Audience <ArrowRight className="w-5 h-5 ml-2" />
        </Button>
      </div>
    </Card>
  </motion.div>
)

export default AudienceGenerationPage