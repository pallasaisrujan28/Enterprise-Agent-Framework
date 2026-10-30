'use client'

import React from 'react'
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell } from 'recharts'

interface PersonalityTraits {
  openness: number
  conscientiousness: number
  extraversion: number
  agreeableness: number
  neuroticism: number
}

interface TraitDistributionData {
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
  average_personality?: PersonalityTraits
}

interface TraitDistributionChartsProps {
  data: TraitDistributionData
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#14B8A6']

export const TraitDistributionCharts: React.FC<TraitDistributionChartsProps> = ({ data }) => {
  // Prepare personality radar chart data
  const personalityRadarData = data.average_personality ? [
    {
      trait: 'Openness',
      value: Math.round(data.average_personality.openness * 100),
      fullMark: 100
    },
    {
      trait: 'Conscientiousness',
      value: Math.round(data.average_personality.conscientiousness * 100),
      fullMark: 100
    },
    {
      trait: 'Extraversion',
      value: Math.round(data.average_personality.extraversion * 100),
      fullMark: 100
    },
    {
      trait: 'Agreeableness',
      value: Math.round(data.average_personality.agreeableness * 100),
      fullMark: 100
    },
    {
      trait: 'Neuroticism',
      value: Math.round(data.average_personality.neuroticism * 100),
      fullMark: 100
    }
  ] : []

  // Prepare values distribution data
  const valuesData = data.values_distribution ? 
    Object.entries(data.values_distribution)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([key, value]) => ({
        name: key.charAt(0).toUpperCase() + key.slice(1),
        value: Math.round(value * 100),
        percentage: value
      })) : []

  // Prepare interests distribution data
  const interestsData = data.interests_distribution ? 
    Object.entries(data.interests_distribution)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([key, value]) => ({
        name: key.charAt(0).toUpperCase() + key.slice(1),
        value: Math.round(value * 100),
        percentage: value
      })) : []

  // Prepare behavioral patterns data
  const shoppingBehaviorData = data.behavioral_patterns_distribution?.shopping_behavior ? 
    Object.entries(data.behavioral_patterns_distribution.shopping_behavior).map(([key, value]) => ({
      name: key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
      value: Math.round(value * 100),
      percentage: value
    })) : []

  const technologyAdoptionData = data.behavioral_patterns_distribution?.technology_adoption ? 
    Object.entries(data.behavioral_patterns_distribution.technology_adoption).map(([key, value]) => ({
      name: key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
      value: Math.round(value * 100),
      percentage: value
    })) : []

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
          <p className="text-white font-semibold">{label}</p>
          <p className="text-blue-400">
            {`${payload[0].value}% (${payload[0].payload.percentage?.toFixed(3) || payload[0].value})`}
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
            {`${payload[0].value}% (${payload[0].payload.percentage?.toFixed(3) || payload[0].value})`}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6">
      {/* Personality Traits Radar Chart */}
      {personalityRadarData.length > 0 && (
        <div className="bg-gray-700 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-white mb-4">Average Personality Profile (Big Five)</h4>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={personalityRadarData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="trait" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
              <PolarRadiusAxis 
                angle={90} 
                domain={[0, 100]} 
                tick={{ fill: '#9CA3AF', fontSize: 10 }}
                tickCount={6}
              />
              <Radar
                name="Personality Traits"
                dataKey="value"
                stroke="#3B82F6"
                fill="#3B82F6"
                fillOpacity={0.3}
                strokeWidth={2}
              />
            </RadarChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
            {personalityRadarData.map((trait, index) => (
              <div key={trait.trait} className="text-center">
                <div className="text-gray-400">{trait.trait}</div>
                <div className="text-white font-semibold">{trait.value}%</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Values and Interests Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Values Distribution */}
        {valuesData.length > 0 && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-white mb-4">Core Values Distribution</h4>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={valuesData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}%`}
                  labelLine={false}
                >
                  {valuesData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomPieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Interests Distribution */}
        {interestsData.length > 0 && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-white mb-4">Top Interests</h4>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={interestsData}>
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
      </div>

      {/* Behavioral Patterns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Shopping Behavior */}
        {shoppingBehaviorData.length > 0 && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-white mb-4">Shopping Behavior Patterns</h4>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={shoppingBehaviorData}
                  cx="50%"
                  cy="50%"
                  outerRadius={60}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {shoppingBehaviorData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomPieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-2 space-y-1">
              {shoppingBehaviorData.map((item, index) => (
                <div key={item.name} className="flex items-center text-sm">
                  <div 
                    className="w-3 h-3 rounded-full mr-2" 
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  ></div>
                  <span className="text-gray-300">{item.name}: {item.value}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Technology Adoption */}
        {technologyAdoptionData.length > 0 && (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-white mb-4">Technology Adoption Patterns</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={technologyAdoptionData}>
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

      {/* Trait Analysis Interpretation */}
      <div className="bg-gray-700 rounded-lg p-4">
        <h4 className="text-lg font-semibold text-white mb-3">Trait Distribution Analysis</h4>
        <div className="space-y-2 text-sm text-gray-300">
          <p>
            <strong className="text-white">Personality Profile:</strong> The radar chart shows the average Big Five personality traits across all personas. 
            Balanced profiles indicate diverse personality representation.
          </p>
          <p>
            <strong className="text-white">Values & Interests:</strong> Distribution charts reveal the most common values and interests among generated personas. 
            Diverse distributions suggest well-rounded persona generation.
          </p>
          <p>
            <strong className="text-white">Behavioral Patterns:</strong> Shopping and technology adoption patterns show how personas behave in different contexts. 
            Varied patterns indicate realistic behavioral diversity.
          </p>
          {data.average_personality && (
            <div className="mt-3 p-3 bg-gray-600 rounded">
              <strong className="text-white">Key Insights:</strong>
              <ul className="mt-2 space-y-1">
                {data.average_personality.openness > 0.6 && (
                  <li className="text-blue-400">• High openness suggests creative and curious personas</li>
                )}
                {data.average_personality.conscientiousness > 0.6 && (
                  <li className="text-green-400">• High conscientiousness indicates organized and reliable personas</li>
                )}
                {data.average_personality.extraversion > 0.6 && (
                  <li className="text-yellow-400">• High extraversion suggests outgoing and social personas</li>
                )}
                {data.average_personality.agreeableness > 0.6 && (
                  <li className="text-purple-400">• High agreeableness indicates cooperative and trusting personas</li>
                )}
                {data.average_personality.neuroticism < 0.4 && (
                  <li className="text-green-400">• Low neuroticism suggests emotionally stable personas</li>
                )}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TraitDistributionCharts