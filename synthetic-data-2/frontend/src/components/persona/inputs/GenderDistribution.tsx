'use client';

import React, { useState } from 'react';

interface GenderDistributionProps {
  value: {
    male: number;
    female: number;
  };
  onChange: (value: {
    male: number;
    female: number;
  }) => void;
  className?: string;
}

export const GenderDistribution: React.FC<GenderDistributionProps> = ({
  value,
  onChange,
  className = ''
}) => {
  const [activeSegment, setActiveSegment] = useState<string | null>(null);

  const total = value.male + value.female;
  const normalizedValue = total === 0 ? { male: 50, female: 50 } : value;
  const normalizedTotal = normalizedValue.male + normalizedValue.female;

  const segments = [
    { key: 'male', label: 'Male', color: '#3B82F6', value: normalizedValue.male },
    { key: 'female', label: 'Female', color: '#EC4899', value: normalizedValue.female }
  ];

  const handleSliderChange = (key: string, newValue: number) => {
    const clampedValue = Math.min(100, Math.max(0, newValue));
    const otherValue = 100 - clampedValue;
    
    if (key === 'male') {
      onChange({
        male: clampedValue,
        female: otherValue
      });
    } else {
      onChange({
        male: otherValue,
        female: clampedValue
      });
    }
  };

  const handleDropdownChange = (key: string, newValue: number) => {
    const otherValue = 100 - newValue;
    
    if (key === 'male') {
      onChange({
        male: newValue,
        female: otherValue
      });
    } else {
      onChange({
        male: otherValue,
        female: newValue
      });
    }
  };

  const percentageOptions = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];

  const getAngle = (val: number) => (val / normalizedTotal) * 360;
  
  let cumulativeAngle = 0;
  const segmentPaths = segments.map((segment) => {
    const angle = getAngle(segment.value);
    const startAngle = cumulativeAngle;
    const endAngle = cumulativeAngle + angle;
    cumulativeAngle += angle;

    const startAngleRad = (startAngle * Math.PI) / 180;
    const endAngleRad = (endAngle * Math.PI) / 180;

    const largeArcFlag = angle > 180 ? 1 : 0;
    const x1 = 50 + 40 * Math.cos(startAngleRad);
    const y1 = 50 + 40 * Math.sin(startAngleRad);
    const x2 = 50 + 40 * Math.cos(endAngleRad);
    const y2 = 50 + 40 * Math.sin(endAngleRad);

    const pathData = [
      `M 50 50`,
      `L ${x1} ${y1}`,
      `A 40 40 0 ${largeArcFlag} 1 ${x2} ${y2}`,
      'Z'
    ].join(' ');

    return {
      ...segment,
      pathData,
      percentage: ((segment.value / normalizedTotal) * 100).toFixed(1)
    };
  });

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="mb-4">
        <label className="block text-sm font-medium text-white mb-2">
          Target Audience Gender Distribution
        </label>
        <p className="text-sm text-gray-400">
          Set the percentage of male vs female personas to generate. For example, 60% male and 40% female means 6 out of 10 personas will be male.
        </p>
      </div>
      
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Pie Chart */}
        <div className="flex-shrink-0">
          <svg width="200" height="200" viewBox="0 0 100 100" className="transform -rotate-90">
            {segmentPaths.map((segment) => (
              <path
                key={segment.key}
                d={segment.pathData}
                fill={segment.color}
                stroke="#1F2937"
                strokeWidth="0.5"
                className={`cursor-pointer transition-all duration-200 ${
                  activeSegment === segment.key ? 'opacity-80 transform scale-105' : 'hover:opacity-80'
                }`}
                onMouseEnter={() => setActiveSegment(segment.key)}
                onMouseLeave={() => setActiveSegment(null)}
              />
            ))}
          </svg>
        </div>
        
        {/* Controls */}
        <div className="flex-1 space-y-4">
          {segments.map((segment) => {
            const segmentData = segmentPaths.find(s => s.key === segment.key);
            return (
              <div key={segment.key} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: segment.color }}
                    />
                    <span className="text-sm font-medium text-white">
                      {segment.label}
                    </span>
                  </div>
                  <span className="text-sm text-white/70">
                    {segmentData?.percentage}%
                  </span>
                </div>
                
                <div className="flex gap-3 items-center">
                  <div className="flex-1">
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={segment.value}
                      onChange={(e) => handleSliderChange(segment.key, parseInt(e.target.value))}
                      className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer slider"
                      style={{
                        background: `linear-gradient(to right, ${segment.color} 0%, ${segment.color} ${(segment.value / 100) * 100}%, rgba(255,255,255,0.2) ${(segment.value / 100) * 100}%, rgba(255,255,255,0.2) 100%)`
                      }}
                    />
                  </div>
                  
                  <select
                    value={segment.value}
                    onChange={(e) => handleDropdownChange(segment.key, parseInt(e.target.value))}
                    className="px-3 py-1 bg-white/10 border border-white/20 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[70px]"
                  >
                    {percentageOptions.map((option) => (
                      <option key={option} value={option} className="bg-gray-800">
                        {option}%
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="flex justify-between text-xs text-white/50">
                  <span>0</span>
                  <span>{segment.value}</span>
                  <span>100</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      
      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: white;
          border: 2px solid #4F46E5;
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        .slider::-moz-range-thumb {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: white;
          border: 2px solid #4F46E5;
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
      `}</style>
    </div>
  );
};