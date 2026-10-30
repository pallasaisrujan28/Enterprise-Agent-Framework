'use client'

import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'

interface DiversityMetricsData {
  total_personas?: number
  unique_clusters?: number
  silhouette_score?: number
  inertia?: number
  pca_explained_variance?: number[]
  feature_importance?: Record<string, number>
}

interface DiversityMetricsProps {
  data: DiversityMetricsData
}

export const DiversityMetrics: React.FC<DiversityMetricsProps> = ({ data }) => {
  // Prepare feature importance data for chart
  const featureImportanceData = data.feature_importance ?
    Object.entries(data.feature_importance)
      .map(([feature, importance]) => ({
        name: feature.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
        value: Math.round(importance * 100),
        importance: importance
      }))
      .sort((a, b) => b.importance - a.importance) : []

  // Prepare PCA explained variance data
  const pcaData = data.pca_explained_variance ?
    data.pca_explained_variance.map((variance, index) => ({
      component: `PC${index + 1}`,
      variance: Math.round(variance * 100),
      cumulative: Math.round(
        data.pca_explained_variance!.slice(0, index + 1).reduce((sum, v) => sum + v, 0) * 100
      )
    })) : []

  const getScoreLevel = (score?: number, type?: 'silhouette' | 'cluster') => {
    if (!score) return { level: 'Unknown', color: 'text-gray-400', bgColor: 'bg-gray-600' }
    
    if (type === 'silhouette') {
      if (score > 0.7) return { level: 'Excellent', color: 'text-green-400', bgColor: 'bg-green-600' }
      if (score > 0.5) return { level: 'Good', color: 'text-blue-400', bgColor: 'bg-blue-600' }
      if (score > 0.25) return { level: 'Fair', color: 'text-yellow-400', bgColor: 'bg-yellow-600' }
      return { level: 'Poor', color: 'text-red-400', bgColor: 'bg-red-600' }
    }
    
    return { level: 'N/A', color: 'text-gray-400', bgColor: 'bg-gray-600' }
  }

  const silhouetteLevel = getScoreLevel(data.silhouette_score, 'silhouette')
  const clusterEfficiency = data.total_personas && data.unique_clusters ? 
    Math.round((data.unique_clusters / data.total_personas) * 100) : 0

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
          <p className="text-white font-semibold">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }}>
              {`${entry.dataKey}: ${entry.value}${entry.dataKey.includes('variance') || entry.dataKey.includes('cumulative') ? '%' : ''}`}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6">
      {/* Key Metrics Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {data.total_personas !== undefined && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-300">Total Personas</h4>
            <p className="text-2xl font-bold text-white">{data.total_personas}</p>
          </div>
        )}
        
        {data.unique_clusters !== undefined && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-300">Unique Clusters</h4>
            <p className="text-2xl font-bold text-white">{data.unique_clusters}</p>
            <p className="text-xs text-gray-400 mt-1">
              {clusterEfficiency}% efficiency
            </p>
          </div>
        )}
        
        {data.silhouette_score !== undefined && (
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-gray-300">Silhouette Score</h4>
                <p className="text-2xl font-bold text-white">
                  {data.silhouette_score.toFixed(3)}
                </p>
              </div>
              <div className={`px-2 py-1 rounded-full text-xs font-medium ${silhouetteLevel.bgColor} ${silhouetteLevel.color}`}>
                {silhouetteLevel.level}
              </div>
            </div>
          </div>
        )}
        
        {data.inertia !== undefined && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-300">Cluster Inertia</h4>
            <p className="text-2xl font-bold text-white">
              {data.inertia.toFixed(1)}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Lower is better
            </p>
          </div>
        )}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Feature Importance */}
        {featureImportanceData.length > 0 && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-white mb-4">Feature Importance</h4>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={featureImportanceData} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis type="number" tick={{ fill: '#9CA3AF' }} />
                <YAxis 
                  type="category" 
                  dataKey="name" 
                  tick={{ fill: '#9CA3AF', fontSize: 11 }}
                  width={80}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="value" fill="#8B5CF6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* PCA Explained Variance */}
        {pcaData.length > 0 && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-white mb-4">PCA Explained Variance</h4>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={pcaData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="component" tick={{ fill: '#9CA3AF' }} />
                <YAxis tick={{ fill: '#9CA3AF' }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="variance" fill="#06B6D4" />
                <Line 
                  type="monotone" 
                  dataKey="cumulative" 
                  stroke="#F59E0B" 
                  strokeWidth={2}
                  dot={{ fill: '#F59E0B', strokeWidth: 2, r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
            <div className="mt-2 text-xs text-gray-400">
              <span className="inline-block w-3 h-3 bg-cyan-500 mr-2"></span>Individual Variance
              <span className="inline-block w-3 h-3 bg-yellow-500 mr-2 ml-4"></span>Cumulative Variance
            </div>
          </div>
        )}
      </div>

      {/* Diversity Analysis Interpretation */}
      <div className="bg-gray-700 rounded-lg p-4">
        <h4 className="text-lg font-semibold text-white mb-3">Diversity Analysis Interpretation</h4>
        <div className="space-y-3 text-sm text-gray-300">
          <div>
            <strong className="text-white">Silhouette Score ({data.silhouette_score?.toFixed(3)}):</strong>
            <span className={`ml-2 ${silhouetteLevel.color}`}>
              {data.silhouette_score && data.silhouette_score > 0.5 ? (
                "Personas form well-separated, distinct clusters indicating good diversity."
              ) : data.silhouette_score && data.silhouette_score > 0.25 ? (
                "Moderate cluster separation. Some personas may share similar characteristics."
              ) : (
                "Low cluster separation. Personas may be too similar or clustering may not be optimal."
              )}
            </span>
          </div>
          
          <div>
            <strong className="text-white">Cluster Efficiency ({clusterEfficiency}%):</strong>
            <span className="ml-2">
              {clusterEfficiency > 50 ? (
                <span className="text-green-400">High diversity - personas are well-distributed across clusters.</span>
              ) : clusterEfficiency > 25 ? (
                <span className="text-yellow-400">Moderate diversity - some clustering of similar personas.</span>
              ) : (
                <span className="text-red-400">Low diversity - many personas share similar characteristics.</span>
              )}
            </span>
          </div>
          
          {data.pca_explained_variance && data.pca_explained_variance.length > 0 && (
            <div>
              <strong className="text-white">Feature Variance:</strong>
              <span className="ml-2">
                {data.pca_explained_variance[0] > 0.4 ? (
                  <span className="text-yellow-400">First component explains {Math.round(data.pca_explained_variance[0] * 100)}% of variance - may indicate dominant feature patterns.</span>
                ) : (
                  <span className="text-green-400">Well-distributed variance across features indicates balanced persona characteristics.</span>
                )}
              </span>
            </div>
          )}
          
          <div className="mt-4 p-3 bg-gray-600 rounded">
            <strong className="text-white">Recommendations:</strong>
            <ul className="mt-2 space-y-1 text-xs">
              {data.silhouette_score && data.silhouette_score < 0.25 && (
                <li className="text-red-400">• Consider adjusting generation parameters to increase persona diversity</li>
              )}
              {clusterEfficiency < 25 && (
                <li className="text-yellow-400">• Generate more personas with varied characteristics</li>
              )}
              {data.pca_explained_variance && data.pca_explained_variance[0] > 0.5 && (
                <li className="text-yellow-400">• Balance feature distributions to avoid dominant characteristics</li>
              )}
              {data.silhouette_score && data.silhouette_score > 0.5 && clusterEfficiency > 30 && (
                <li className="text-green-400">• Excellent diversity metrics - personas represent distinct user segments</li>
              )}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}