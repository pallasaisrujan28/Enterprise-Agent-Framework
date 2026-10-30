'use client';

import React from 'react';

interface LikertScaleProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  labels?: string[];
  className?: string;
}

export const LikertScale: React.FC<LikertScaleProps> = ({
  label,
  value,
  onChange,
  min = 1,
  max = 5,
  labels = ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
  className = ''
}) => {
  const options = Array.from({ length: max - min + 1 }, (_, i) => min + i);

  return (
    <div className={`space-y-4 ${className}`}>
      <label className="block text-sm font-medium text-white mb-3">
        {label}
      </label>
      
      <div className="space-y-3">
        {/* Scale options */}
        <div className="flex justify-between items-center gap-2">
          {options.map((option, index) => (
            <div key={option} className="flex flex-col items-center gap-2">
              <button
                type="button"
                onClick={() => onChange(option)}
                className={`w-12 h-12 rounded-full border-2 transition-all duration-200 flex items-center justify-center font-medium ${
                  value === option
                    ? 'bg-indigo-500 border-indigo-400 text-white shadow-lg transform scale-110'
                    : 'bg-white/10 border-white/30 text-white/70 hover:bg-white/20 hover:border-white/50 hover:text-white'
                }`}
              >
                {option}
              </button>
              
              {/* Label below each option */}
              {labels[index] && (
                <span className="text-xs text-white/60 text-center max-w-20 leading-tight">
                  {labels[index]}
                </span>
              )}
            </div>
          ))}
        </div>
        
        {/* Visual scale bar */}
        <div className="relative">
          <div className="h-2 bg-white/20 rounded-lg">
            <div 
              className="h-2 bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-lg transition-all duration-300"
              style={{
                width: `${((value - min) / (max - min)) * 100}%`
              }}
            />
          </div>
          
          {/* Current value indicator */}
          <div 
            className="absolute w-4 h-4 bg-white border-2 border-indigo-500 rounded-full shadow-lg transform -translate-y-1 -translate-x-2 transition-all duration-300"
            style={{
              left: `${((value - min) / (max - min)) * 100}%`
            }}
          />
        </div>
        
        {/* Range labels */}
        <div className="flex justify-between text-xs text-white/50">
          <span>{labels[0]}</span>
          <span>{labels[labels.length - 1]}</span>
        </div>
        
        {/* Current selection display */}
        {value && (
          <div className="text-center">
            <span className="inline-block px-3 py-1 bg-indigo-500/20 border border-indigo-500/30 rounded-full text-sm text-indigo-300">
              Selected: {value} - {labels[value - min] || 'Custom'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};