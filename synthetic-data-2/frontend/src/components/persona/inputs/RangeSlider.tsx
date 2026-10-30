'use client';

import React from 'react';

interface RangeSliderProps {
  label: string;
  value: [number, number];
  onChange: (value: [number, number]) => void;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  className?: string;
}

export const RangeSlider: React.FC<RangeSliderProps> = ({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  unit = '',
  className = ''
}) => {
  const handleMinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newMin = parseInt(e.target.value);
    if (newMin <= value[1]) {
      onChange([newMin, value[1]]);
    }
  };

  const handleMaxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newMax = parseInt(e.target.value);
    if (newMax >= value[0]) {
      onChange([value[0], newMax]);
    }
  };

  const getPercentage = (val: number) => ((val - min) / (max - min)) * 100;

  return (
    <div className={`space-y-4 ${className}`}>
      <label className="block text-sm font-medium text-white mb-2">
        {label}
      </label>
      
      <div className="relative">
        {/* Track */}
        <div className="h-2 bg-white/20 rounded-lg relative">
          {/* Active range */}
          <div 
            className="absolute h-2 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg"
            style={{
              left: `${getPercentage(value[0])}%`,
              width: `${getPercentage(value[1]) - getPercentage(value[0])}%`
            }}
          />
        </div>
        
        {/* Min slider */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value[0]}
          onChange={handleMinChange}
          className="absolute top-0 w-full h-2 opacity-0 cursor-pointer"
        />
        
        {/* Max slider */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value[1]}
          onChange={handleMaxChange}
          className="absolute top-0 w-full h-2 opacity-0 cursor-pointer"
        />
        
        {/* Min thumb */}
        <div 
          className="absolute w-4 h-4 bg-white border-2 border-indigo-500 rounded-full shadow-lg transform -translate-y-1 -translate-x-2 cursor-pointer"
          style={{ left: `${getPercentage(value[0])}%` }}
        />
        
        {/* Max thumb */}
        <div 
          className="absolute w-4 h-4 bg-white border-2 border-purple-500 rounded-full shadow-lg transform -translate-y-1 -translate-x-2 cursor-pointer"
          style={{ left: `${getPercentage(value[1])}%` }}
        />
      </div>
      
      {/* Value display */}
      <div className="flex justify-between text-sm text-white/70">
        <span>{value[0]}{unit}</span>
        <span>{value[1]}{unit}</span>
      </div>
    </div>
  );
};