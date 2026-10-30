'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ClusteringVisualization } from './ClusteringVisualization'
import { BiasMetrics } from './BiasMetrics'
import { DiversityMetrics } from './DiversityMetrics'
import { TraitDistributionCharts } from './TraitDistributionCharts'
import { SessionSelector } from './SessionSelector'
import { apiService } from '@/lib/api'

interface Session {
  session_id: string
  created_at: string
  persona_count: number
  generation_method: string
}

interface AnalysisData {
  session_id: string
  analysis_timestamp: string
  clustering: {
    n_clusters: number
    personas: Array<{
      persona_id: string
      cluster: number
      x: number
      y: number
      age: number
      gender: string
      income: string
      education: string
      location: string
    }>
    cluster_centers: Array<{
      cluster: number
      x: number
      y: number
      size: number
    }>
    algorithm: string
  }
  bias_metrics: {
    gender_distribution?: Record<string, number>
    gender_bias_score?: number
    age_distribution?: {
      mean: number
      std: number
      min: number
      max: number
    }
    income_distribution?: Record<string, number>
    education_distribution?: Record<string, number>
    location_distribution?: Record<string, number>
  }
  diversity_metrics: {
    total_personas: number
    unique_clusters: number
    silhouette_score: number
    inertia: number
    pca_explained_variance: number[]
    feature_importance?: Record<string, number>
  }
  feature_importance: {
    pca_components: number[][]
    feature_names: string[]
  }
  trait_distribution?: {
    personality_traits_distribution?: {
      openness: { mean: number; std: number; distribution: number[] }
      conscientiousness: { mean: number; std: number; distribution: number[] }
      extraversion: { mean: number; std: number; distribution: number[] }
      agreeableness: { mean: number; std: number; distribution: number[] }
      neuroticism: { mean: number; std: number; distribution: number[] }
    }
    values_distribution?: Record<string, number>
    interests_distribution?: Record<string, number>
    behavioral_patterns_distribution?: {
      shopping_behavior?: Record<string, number>
      technology_adoption?: Record<string, number>
      social_media_usage?: Record<string, number>
      communication_preference?: Record<string, number>
    }
    average_personality?: {
      openness: number
      conscientiousness: number
      extraversion: number
      agreeableness: number
      neuroticism: number
    }
  }
}

export const PersonaAnalysisDashboard: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([])
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nClusters, setNClusters] = useState(5)

  // Fetch available sessions
  useEffect(() => {
    fetchSessions()
  }, [])

  const fetchSessions = async () => {
    try {
      const sessions = await apiService.getSessions()
      setSessions(sessions || [])
    } catch (err) {
      setError('Failed to load sessions')
      console.error('Error fetching sessions:', err)
    }
  }

  const analyzeSession = async (sessionId: string) => {
    if (!sessionId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(
        `http://localhost:8000/api/sessions/${sessionId}/analyze?n_clusters=${nClusters}`,
        { method: 'POST' }
      )
      
      if (!response.ok) {
        throw new Error('Failed to analyze session')
      }
      
      const data = await response.json()
      setAnalysisData(data)
    } catch (err) {
      setError('Failed to analyze session')
      console.error('Error analyzing session:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSessionSelect = (sessionId: string) => {
    setSelectedSession(sessionId)
    setAnalysisData(null)
  }

  const handleAnalyze = () => {
    if (selectedSession) {
      analyzeSession(selectedSession)
    }
  }

  const handleSessionDelete = async (sessionId: string) => {
    try {
      await apiService.deleteSession(sessionId)
      
      // Refresh sessions list
      await fetchSessions()
      
      // Clear selected session if it was deleted
      if (selectedSession === sessionId) {
        setSelectedSession(null)
        setAnalysisData(null)
      }
    } catch (err) {
      setError('Failed to delete session')
      console.error('Error deleting session:', err)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-white">Persona Analysis</h2>
          <p className="text-gray-400 mt-2">
            Analyze persona diversity, clustering patterns, and bias metrics
          </p>
        </div>
      </div>

      {/* Session Selection */}
      <Card className="bg-gray-800 border-gray-700">
        <div className="p-6">
          <h3 className="text-xl font-semibold text-white mb-4">Select Session to Analyze</h3>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <SessionSelector
                sessions={sessions}
                selectedSession={selectedSession}
                onSessionSelect={handleSessionSelect}
                onSessionDelete={handleSessionDelete}
              />
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Number of Clusters
                </label>
                <input
                  type="number"
                  min="2"
                  max="10"
                  value={nClusters}
                  onChange={(e) => setNClusters(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <Button
                onClick={handleAnalyze}
                disabled={!selectedSession || loading}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600"
              >
                {loading ? 'Analyzing...' : 'Analyze Session'}
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Error Display */}
      {error && (
        <Card className="bg-red-900 border-red-700">
          <div className="p-4">
            <p className="text-red-200">{error}</p>
          </div>
        </Card>
      )}

      {/* Analysis Results */}
      {analysisData && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-6"
        >
          {/* Overview Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="bg-gray-800 border-gray-700">
              <div className="p-4">
                <div className="flex items-center">
                  <div className="p-2 bg-blue-500 rounded-lg">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-400">Total Personas</p>
                    <p className="text-2xl font-bold text-white">{analysisData.diversity_metrics.total_personas}</p>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="bg-gray-800 border-gray-700">
              <div className="p-4">
                <div className="flex items-center">
                  <div className="p-2 bg-green-500 rounded-lg">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-400">Clusters</p>
                    <p className="text-2xl font-bold text-white">{analysisData.clustering.n_clusters}</p>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="bg-gray-800 border-gray-700">
              <div className="p-4">
                <div className="flex items-center">
                  <div className="p-2 bg-purple-500 rounded-lg">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-400">Diversity Score</p>
                    <p className="text-2xl font-bold text-white">
                      {(analysisData.diversity_metrics.silhouette_score * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="bg-gray-800 border-gray-700">
              <div className="p-4">
                <div className="flex items-center">
                  <div className="p-2 bg-orange-500 rounded-lg">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-400">Variance Explained</p>
                    <p className="text-2xl font-bold text-white">
                      {(analysisData.diversity_metrics.pca_explained_variance.reduce((a, b) => a + b, 0) * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Main Analysis Components */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {/* Clustering Visualization */}
            <Card className="bg-gray-800 border-gray-700">
              <div className="p-6">
                <h3 className="text-xl font-semibold text-white mb-4">K-means Clustering</h3>
                <ClusteringVisualization data={analysisData.clustering} />
              </div>
            </Card>

            {/* Bias Metrics */}
            <Card className="bg-gray-800 border-gray-700">
              <div className="p-6">
                <h3 className="text-xl font-semibold text-white mb-4">Bias Detection</h3>
                <BiasMetrics data={analysisData.bias_metrics} />
              </div>
            </Card>
          </div>

          {/* Diversity Metrics */}
          <Card className="bg-gray-800 border-gray-700">
            <div className="p-6">
              <h3 className="text-xl font-semibold text-white mb-4">Diversity Analysis</h3>
              <DiversityMetrics 
                data={{
                  ...analysisData.diversity_metrics,
                  feature_importance: analysisData.feature_importance ? 
                    Object.fromEntries(
                      analysisData.feature_importance.feature_names.map((name, i) => [
                        name, 
                        Math.abs(analysisData.feature_importance.pca_components[0]?.[i] || 0)
                      ])
                    ) : undefined
                }}
              />
            </div>
          </Card>

          {/* Trait Distribution Charts */}
          {analysisData.trait_distribution && (
            <Card className="bg-gray-800 border-gray-700">
              <div className="p-6">
                <h3 className="text-xl font-semibold text-white mb-4">Trait Distribution Analysis</h3>
                <TraitDistributionCharts data={analysisData.trait_distribution} />
              </div>
            </Card>
          )}
        </motion.div>
      )}
    </div>
  )
}