'use client'

import React from 'react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface BiasMetricsData {
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

interface BiasMetricsProps {
  data: BiasMetricsData
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16']

export const BiasMetrics: React.FC<BiasMetricsProps> = ({ data }) => {
  // Prepare data for charts
  const genderData = data.gender_distribution ? 
    Object.entries(data.gender_distribution).map(([key, value]) => ({
      name: key,
      value: Math.round(value * 100),
      percentage: value
    })) : []

  const incomeData = data.income_distribution ?
    Object.entries(data.income_distribution).map(([key, value]) => ({
      name: key,
      value: Math.round(value * 100),
      percentage: value
    })) : []

  const educationData = data.education_distribution ?
    Object.entries(data.education_distribution).map(([key, value]) => ({
      name: key.replace("'s", "'s"), // Fix apostrophe encoding
      value: Math.round(value * 100),
      percentage: value
    })) : []

  const locationData = data.location_distribution ?
    Object.entries(data.location_distribution)
      .sort((a, b) => b[1] - a[1]) // Sort by percentage descending
      .slice(0, 10) // Show top 10 locations
      .map(([key, value]) => ({
        name: key,
        value: Math.round(value * 100),
        percentage: value
      })) : []

  const getBiasLevel = (score?: number) => {
    if (!score) return { level: 'Unknown', color: 'text-gray-400', bgColor: 'bg-gray-600' }
    if (score < 0.1) return { level: 'Low', color: 'text-green-400', bgColor: 'bg-green-600' }
    if (score < 0.2) return { level: 'Moderate', color: 'text-yellow-400', bgColor: 'bg-yellow-600' }
    return { level: 'High', color: 'text-red-400', bgColor: 'bg-red-600' }
  }

  const genderBias = getBiasLevel(data.gender_bias_score)

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
          <p className="text-white font-semibold">{label}</p>
          <p className="text-blue-400">
            {`${payload[0].value}% (${payload[0].payload.percentage.toFixed(3)})`}
          </p>
        </div>
      )
    }
    return null
  }

  const CustomPieTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
          <p className="text-white font-semibold">{payload[0].name}</p>
          <p className="text-blue-400">
            {`${payload[0].value}% (${payload[0].payload.percentage.toFixed(3)})`}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6">
      {/* Bias Score Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.gender_bias_score !== undefined && (
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-gray-300">Gender Bias Score</h4>
                <p className="text-2xl font-bold text-white">
                  {(data.gender_bias_score * 100).toFixed(1)}%
                </p>
              </div>
              <div className={`px-3 py-1 rounded-full text-xs font-medium ${genderBias.bgColor} ${genderBias.color}`}>
                {genderBias.level}
              </div>
            </div>
          </div>
        )}
        
        {data.age_distribution && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-300 mb-2">Age Distribution</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-400">Mean:</span>
                <span className="ml-2 text-white">{data.age_distribution.mean.toFixed(1)}</span>
              </div>
              <div>
                <span className="text-gray-400">Std:</span>
                <span className="ml-2 text-white">{data.age_distribution.std.toFixed(1)}</span>
              </div>
              <div>
                <span className="text-gray-400">Min:</span>
                <span className="ml-2 text-white">{data.age_distribution.min}</span>
              </div>
              <div>
                <span className="text-gray-400">Max:</span>
                <span className="ml-2 text-white">{data.age_distribution.max}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Distribution Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gender Distribution */}
        {genderData.length > 0 && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-white mb-4">Gender Distribution</h4>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={genderData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {genderData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomPieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Income Distribution */}
        {incomeData.length > 0 && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-white mb-4">Income Distribution</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={incomeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fill: '#9CA3AF', fontSize: 10 }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis tick={{ fill: '#9CA3AF' }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="value" fill="#3B82F6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Education Distribution */}
        {educationData.length > 0 && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-white mb-4">Education Distribution</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={educationData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fill: '#9CA3AF', fontSize: 10 }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis tick={{ fill: '#9CA3AF' }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="value" fill="#10B981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Location Distribution */}
        {locationData.length > 0 && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-white mb-4">Top Locations</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={locationData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fill: '#9CA3AF', fontSize: 10 }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis tick={{ fill: '#9CA3AF' }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="value" fill="#F59E0B" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Bias Interpretation */}
      <div className="bg-gray-700 rounded-lg p-4">
        <h4 className="text-lg font-semibold text-white mb-3">Bias Analysis Interpretation</h4>
        <div className="space-y-2 text-sm text-gray-300">
          <p>
            <strong className="text-white">Gender Bias Score:</strong> Measures deviation from balanced gender representation. 
            Lower scores indicate more balanced distribution.
          </p>
          <p>
            <strong className="text-white">Distribution Analysis:</strong> Shows how personas are distributed across different demographic categories. 
            Uneven distributions may indicate potential bias in generation.
          </p>
          <p>
            <strong className="text-white">Recommendations:</strong> 
            {data.gender_bias_score && data.gender_bias_score > 0.2 ? (
              <span className="text-red-400"> Consider adjusting generation parameters to achieve more balanced gender representation.</span>
            ) : (
              <span className="text-green-400"> Current generation shows good demographic balance.</span>
            )}
          </p>
        </div>
      </div>
    </div>
  )
}