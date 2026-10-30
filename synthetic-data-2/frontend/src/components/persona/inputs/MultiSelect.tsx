'use client';

import React, { useState } from 'react';

interface MultiSelectProps {
  label: string;
  options: string[];
  value: string[];
  onChange: (value: string[]) => void;
  maxSelections?: number;
  searchable?: boolean;
  className?: string;
  placeholder?: string;
}

export const MultiSelect: React.FC<MultiSelectProps> = ({
  label,
  options,
  value,
  onChange,
  maxSelections,
  searchable = false,
  className = '',
  placeholder = 'Search options...'
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);

  const filteredOptions = searchable
    ? options.filter(option => 
        option.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : options;

  const handleToggle = (option: string) => {
    if (value.includes(option)) {
      onChange(value.filter(item => item !== option));
    } else {
      if (maxSelections && value.length >= maxSelections) {
        return; // Don't add if max selections reached
      }
      onChange([...value, option]);
    }
  };

  const handleSelectAll = () => {
    if (maxSelections) {
      onChange(filteredOptions.slice(0, maxSelections));
    } else {
      onChange(filteredOptions);
    }
  };

  const handleClearAll = () => {
    onChange([]);
  };

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-white">
          {label}
          {maxSelections && (
            <span className="text-white/60 ml-2">
              ({value.length}/{maxSelections})
            </span>
          )}
        </label>
        
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSelectAll}
            className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
            disabled={!!(maxSelections && value.length >= maxSelections)}
          >
            Select All
          </button>
          <button
            type="button"
            onClick={handleClearAll}
            className="text-xs text-red-400 hover:text-red-300 transition-colors"
          >
            Clear All
          </button>
        </div>
      </div>

      {/* Selected items display */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {value.map((item) => (
            <span
              key={item}
              className="inline-flex items-center gap-1 px-3 py-1 bg-indigo-500/20 border border-indigo-500/30 rounded-full text-sm text-indigo-300"
            >
              {item}
              <button
                type="button"
                onClick={() => handleToggle(item)}
                className="ml-1 text-indigo-400 hover:text-red-400 transition-colors"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search input */}
      {searchable && (
        <input
          type="text"
          placeholder={placeholder}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200"
        />
      )}

      {/* Expand/Collapse toggle */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white/70 hover:bg-white/20 transition-all duration-200 flex items-center justify-between"
      >
        <span>
          {isExpanded ? 'Hide Options' : `Show Options (${filteredOptions.length})`}
        </span>
        <span className={`transform transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>

      {/* Options list */}
      {isExpanded && (
        <div className="max-h-60 overflow-y-auto border border-white/20 rounded-lg bg-white/5">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-1 p-2">
            {filteredOptions.map((option) => {
              const isSelected = value.includes(option);
              const isDisabled = maxSelections && !isSelected && value.length >= maxSelections;
              
              return (
                <label
                  key={option}
                  className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-all duration-200 ${
                    isSelected
                      ? 'bg-indigo-500/20 border border-indigo-500/30'
                      : isDisabled
                      ? 'bg-white/5 text-white/40 cursor-not-allowed'
                      : 'hover:bg-white/10'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => !isDisabled && handleToggle(option)}
                    disabled={!!isDisabled}
                    className="w-4 h-4 text-indigo-500 bg-transparent border-white/30 rounded focus:ring-indigo-500 focus:ring-2"
                  />
                  <span className={`text-sm ${
                    isSelected ? 'text-indigo-300 font-medium' : 'text-white/70'
                  }`}>
                    {option}
                  </span>
                </label>
              );
            })}
          </div>
          
          {filteredOptions.length === 0 && (
            <div className="p-4 text-center text-white/50">
              No options found
            </div>
          )}
        </div>
      )}
    </div>
  );
};