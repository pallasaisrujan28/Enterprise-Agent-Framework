'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { apiService, PersonaFolderInfo, PersonaAnalytics } from '@/lib/api'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, PieChart, Pie, Cell, LineChart, Line,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend
} from 'recharts'
import { AlertTriangle, TrendingUp, Users, Target, Brain, BarChart3 } from 'lucide-react'

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#8dd1e1', '#d084d0']

export const NewPersonaAnalyticsDashboard: React.FC = () => {
  const [selectedFolder, setSelectedFolder] = useState<string>('')
  const [folders, setFolders] = useState<PersonaFolderInfo[]>([])
  const [analytics, setAnalytics] = useState<PersonaAnalytics | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load persona folders on component mount
  useEffect(() => {
    loadPersonaFolders()
  }, [])

  // Load analytics when folder is selected
  useEffect(() => {
    if (selectedFolder) {
      loadAnalytics(selectedFolder)
    }
  }, [selectedFolder])

  const loadPersonaFolders = async () => {
    try {
      const folderData = await apiService.getPersonaFolders()
      setFolders(folderData)
      if (folderData.length > 0 && !selectedFolder) {
        setSelectedFolder(folderData[0].name)
      }
    } catch (err) {
      // Silently handle - old API endpoint not available in new system
      setFolders([])
    }
  }

  const loadAnalytics = async (folderName: string) => {
    setLoading(true)
    setError(null)
    try {
      const analyticsData = await apiService.getPersonaAnalytics(folderName)
      setAnalytics(analyticsData)
    } catch (err) {
      setError('Failed to load analytics data')
      console.error('Error loading analytics:', err)
    } finally {
      setLoading(false)
    }
  }

  const renderClusterVisualization = () => {
    if (!analytics?.relationship_analysis.cluster_visualization) return null

    const data = analytics.relationship_analysis.cluster_visualization
    
    // Helper function to get cluster labels for diversity and persona variation
    const getClusterLabel = (clusterNum: number) => {
      // Map clusters to diversity and persona variation categories
      const clusterNames = {
        0: "High Diversity",
        1: "Medium Diversity", 
        2: "Low Diversity",
        3: "High Persona Variation",
        4: "Medium Persona Variation",
        5: "Low Persona Variation"
      }
      return clusterNames[clusterNum as keyof typeof clusterNames] || `Cluster ${clusterNum + 1}`
    }

    const getAgeGroup = (age: number) => {
      if (age < 25) return "Gen Z (18-24)"
      if (age < 35) return "Millennials (25-34)"
      if (age < 45) return "Gen X (35-44)"
      if (age < 55) return "Gen X (45-54)"
      return "Boomers (55+)"
    }
    
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Target className="w-5 h-5" />
          Persona Diversity & Variation Analysis
        </h3>
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                type="number" 
                dataKey="x" 
                name="Clustering Dimension 1"
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                tick={false}
                axisLine={false}
                label={{ value: 'Clustering Analysis →', position: 'insideBottom', offset: -10 }}
              />
              <YAxis 
                type="number" 
                dataKey="y" 
                name="Clustering Dimension 2"
                domain={['dataMin - 0.5', 'dataMax + 0.5']}
                tick={false}
                axisLine={false}
                label={{ value: 'Pattern Recognition ↑', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip 
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) => {
                  if (active && payload && payload[0]) {
                    const data = payload[0].payload
                    return (
                      <div className="bg-white p-4 border rounded-lg shadow-lg max-w-xs">
                        <p className="font-bold text-lg mb-2">{data.name}</p>
                        <div className="space-y-1 text-sm">
                          <p><span className="font-semibold text-blue-600">Category:</span> {getClusterLabel(data.cluster)}</p>
                          <p><span className="font-semibold text-green-600">Age Group:</span> {getAgeGroup(data.age)}</p>
                          <p><span className="font-semibold text-purple-600">Demographics:</span> {data.gender}, {data.age} years</p>
                          <p><span className="font-semibold text-orange-600">Cluster ID:</span> {data.cluster}</p>
                          <p><span className="font-semibold text-red-600">Persona ID:</span> {data.persona_id}</p>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Legend 
                verticalAlign="top" 
                height={36}
                iconType="circle"
                wrapperStyle={{ paddingBottom: '20px' }}
              />
              {/* Render separate scatter plots for diversity and persona variation */}
              {Array.from(new Set(data.map(d => d.cluster))).map((clusterNum, index) => {
                const clusterData = data.filter(d => d.cluster === clusterNum)
                // Use distinct colors for diversity vs persona variation
                const diversityColors = ['#8884d8', '#82ca9d', '#ffc658'] // Blues and greens for diversity
                const variationColors = ['#ff7300', '#8dd1e1', '#d084d0'] // Oranges and purples for variation
                const colors = clusterNum < 3 ? diversityColors : variationColors
                const colorIndex = clusterNum < 3 ? clusterNum : clusterNum - 3
                
                return (
                  <Scatter 
                    key={clusterNum}
                    data={clusterData}
                    dataKey="y" 
                    fill={colors[colorIndex % colors.length]}
                    name={getClusterLabel(clusterNum)}
                  />
                )
              })}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-4 space-y-3">
          <p className="text-sm text-gray-600">
            <span className="font-semibold">Clustering Quality Score:</span> {analytics.relationship_analysis.silhouette_score.toFixed(3)}
            <span className="ml-2 text-xs">(Higher = better defined clusters, max 1.0)</span>
          </p>

          <p className="text-xs text-gray-500">
            This visualization analyzes persona diversity and variation patterns using machine learning clustering. 
            Diversity clusters show how different personas are from each other, while variation clusters show the range of characteristics within persona groups.
          </p>
        </div>
      </Card>
    )
  }

  const renderQualityMetrics = () => {
    if (!analytics?.quality_assessment.average_quality_scores) return null

    const qualityData = Object.entries(analytics.quality_assessment.average_quality_scores).map(
      ([key, value]) => ({
        name: key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
        score: value.mean,
        min: value.min,
        max: value.max
      })
    )

    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          Quality Assessment
        </h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={qualityData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
              <YAxis domain={[0, 1]} />
              <Tooltip 
                formatter={(value: number, name: string) => [
                  `${(value * 100).toFixed(1)}%`, 
                  name
                ]}
              />
              <Bar dataKey="score" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    )
  }

  const renderDemographicDistribution = () => {
    if (!analytics?.demographic_distribution) return null

    const { age_distribution, gender_distribution, income_distribution, education_distribution } = analytics.demographic_distribution

    const ageData = Object.entries(age_distribution).map(([range, count]) => ({ name: range, value: count }))
    const genderData = Object.entries(gender_distribution).map(([gender, count]) => ({ name: gender, value: count }))

    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Age Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ageData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#82ca9d" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Gender Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={genderData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${percent ? (percent * 100).toFixed(0) : 0}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {genderData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    )
  }

  const renderBiasIndicators = () => {
    if (!analytics?.bias_indicators) return null

    const { gender_bias_score, age_distribution_skew, geographic_concentration, bias_alerts } = analytics.bias_indicators

    const getBiasLevel = (score: number, thresholds: [number, number]) => {
      if (score < thresholds[0]) return { level: 'Low', color: 'bg-green-500' }
      if (score < thresholds[1]) return { level: 'Medium', color: 'bg-yellow-500' }
      return { level: 'High', color: 'bg-red-500' }
    }

    const genderBias = getBiasLevel(gender_bias_score, [0.1, 0.3])
    const ageBias = getBiasLevel(age_distribution_skew / 20, [0.25, 0.5]) // Normalize age skew
    const geoBias = getBiasLevel(geographic_concentration, [0.4, 0.7])

    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          Bias Detection Dashboard
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="text-center">
            <div className="mb-2">
              <div className={`w-4 h-4 rounded-full ${genderBias.color} mx-auto mb-1`}></div>
              <p className="text-sm font-medium">Gender Bias</p>
              <p className="text-xs text-gray-600">{genderBias.level}</p>
            </div>
            <Progress value={gender_bias_score * 100} className="h-2" />
            <p className="text-xs mt-1">{(gender_bias_score * 100).toFixed(1)}%</p>
          </div>
          
          <div className="text-center">
            <div className="mb-2">
              <div className={`w-4 h-4 rounded-full ${ageBias.color} mx-auto mb-1`}></div>
              <p className="text-sm font-medium">Age Skew</p>
              <p className="text-xs text-gray-600">{ageBias.level}</p>
            </div>
            <Progress value={(age_distribution_skew / 20) * 100} className="h-2" />
            <p className="text-xs mt-1">{age_distribution_skew.toFixed(1)} years</p>
          </div>
          
          <div className="text-center">
            <div className="mb-2">
              <div className={`w-4 h-4 rounded-full ${geoBias.color} mx-auto mb-1`}></div>
              <p className="text-sm font-medium">Geographic Concentration</p>
              <p className="text-xs text-gray-600">{geoBias.level}</p>
            </div>
            <Progress value={geographic_concentration * 100} className="h-2" />
            <p className="text-xs mt-1">{(geographic_concentration * 100).toFixed(1)}%</p>
          </div>
        </div>

        {bias_alerts.length > 0 && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              <div className="space-y-1">
                {bias_alerts.map((alert, index) => (
                  <p key={index} className="text-sm">{alert}</p>
                ))}
              </div>
            </AlertDescription>
          </Alert>
        )}
      </Card>
    )
  }

  const renderDiversityMetrics = () => {
    if (!analytics?.diversity_metrics) return null

    const { diversity_index, psychographic_diversity, feature_importance } = analytics.diversity_metrics

    const personalityData = Object.entries(psychographic_diversity).map(([trait, stats]) => ({
      trait: trait.charAt(0).toUpperCase() + trait.slice(1),
      mean: stats.mean,
      std: stats.std,
      range: stats.range
    }))

    const featureData = Object.entries(feature_importance).map(([feature, importance]) => ({
      feature: feature.charAt(0).toUpperCase() + feature.slice(1),
      importance
    }))

    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5" />
            Psychographic Diversity
          </h3>
          <div className="mb-4">
            <p className="text-sm text-gray-600">
              Overall Diversity Index: <span className="font-semibold">{diversity_index.toFixed(3)}</span>
            </p>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={personalityData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="trait" />
                <PolarRadiusAxis domain={[0, 1]} />
                <Radar
                  name="Standard Deviation"
                  dataKey="std"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.3}
                />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Feature Importance</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={featureData} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="feature" type="category" width={100} />
                <Tooltip />
                <Bar dataKey="importance" fill="#ffc658" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold">Persona Analytics Dashboard</h1>
          <p className="text-gray-600 mt-1">Comprehensive analysis of persona quality, clustering, and diversity</p>
        </div>
        
        <div className="flex items-center gap-4">
          <Select value={selectedFolder} onValueChange={setSelectedFolder}>
            <SelectTrigger className="w-64">
              <SelectValue placeholder="Select persona folder" />
            </SelectTrigger>
            <SelectContent className="max-h-[200px] overflow-y-auto z-[100]">
              {folders.map((folder) => (
                <SelectItem key={folder.name} value={folder.name}>
                  {folder.name} ({folder.persona_count} personas)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Button 
            onClick={() => selectedFolder && loadAnalytics(selectedFolder)}
            disabled={loading || !selectedFolder}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-sm text-gray-600">Total Personas</p>
                <p className="text-2xl font-bold">{analytics.total_personas}</p>
              </div>
            </div>
          </Card>
          
          <Card className="p-4">
            <div className="flex items-center gap-2">
              <Target className="w-5 h-5 text-green-500" />
              <div>
                <p className="text-sm text-gray-600">Silhouette Score</p>
                <p className="text-2xl font-bold">{analytics.relationship_analysis.silhouette_score.toFixed(3)}</p>
              </div>
            </div>
          </Card>
          
          <Card className="p-4">
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-500" />
              <div>
                <p className="text-sm text-gray-600">Diversity Index</p>
                <p className="text-2xl font-bold">{analytics.diversity_metrics.diversity_index.toFixed(3)}</p>
              </div>
            </div>
          </Card>
          
          <Card className="p-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-orange-500" />
              <div>
                <p className="text-sm text-gray-600">Avg Quality</p>
                <p className="text-2xl font-bold">
                  {analytics.quality_assessment.average_quality_scores.overall_quality ? 
                    (analytics.quality_assessment.average_quality_scores.overall_quality.mean * 100).toFixed(0) + '%' : 
                    'N/A'
                  }
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Main Content */}
      {analytics && (
        <Tabs defaultValue="clustering" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="clustering">Clustering</TabsTrigger>
            <TabsTrigger value="quality">Quality</TabsTrigger>
            <TabsTrigger value="demographics">Demographics</TabsTrigger>
            <TabsTrigger value="bias">Bias Detection</TabsTrigger>
            <TabsTrigger value="diversity">Diversity</TabsTrigger>
          </TabsList>

          <TabsContent value="clustering" className="space-y-6">
            {renderClusterVisualization()}
          </TabsContent>

          <TabsContent value="quality" className="space-y-6">
            {renderQualityMetrics()}
          </TabsContent>

          <TabsContent value="demographics" className="space-y-6">
            {renderDemographicDistribution()}
          </TabsContent>

          <TabsContent value="bias" className="space-y-6">
            {renderBiasIndicators()}
          </TabsContent>

          <TabsContent value="diversity" className="space-y-6">
            {renderDiversityMetrics()}
          </TabsContent>
        </Tabs>
      )}

      {loading && (
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading analytics...</p>
          </div>
        </div>
      )}
    </div>
  )
}