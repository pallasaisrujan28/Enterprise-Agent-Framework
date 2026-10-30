'use client';

import React, { useState, useEffect } from 'react';
import { useFormContext } from './FormContext';

interface Step {
  id: string;
  title: string;
  component: React.ComponentType;
  completed?: boolean;
}

interface MultiStepFormProps {
  steps: Step[];
  onStepChange?: (stepIndex: number) => void;
  onComplete?: (formData?: any) => void;
}

export default function MultiStepForm({ steps, onStepChange, onComplete }: MultiStepFormProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { getStepCompletionStatus, isFormValid, updateFormData, formData } = useFormContext();

  // Log component mount and step changes
  useEffect(() => {
  }, []);

  useEffect(() => {
      current: getStepCompletionStatus(steps[currentStep]?.id),
      allSteps: steps.map(step => ({
        id: step.id,
        title: step.title,
        completed: getStepCompletionStatus(step.id)
      }))
    });
  }, [currentStep, steps, getStepCompletionStatus]);



  const handleNext = () => {
    
    if (currentStep < steps.length - 1) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      onStepChange?.(nextStep);
      
      // Log step completion status
        currentStep: nextStep + 1,
        totalSteps: steps.length,
        percentage: Math.round(((nextStep + 1) / steps.length) * 100)
      });
    } else {
      // Final step completed
      if (isFormValid()) {
        onComplete?.(formData); // Pass the actual form data
      } else {
        console.warn('⚠️ Form validation failed on final step');
      }
    }
  };

  const handlePrevious = () => {
    
    if (currentStep > 0) {
      const prevStep = currentStep - 1;
      setCurrentStep(prevStep);
      onStepChange?.(prevStep);
      
    } else {
    }
  };

  const handleStepClick = (stepIndex: number) => {
    
    setCurrentStep(stepIndex);
    onStepChange?.(stepIndex);
    setIsMenuOpen(false); // Close menu after selection
    
  };

  const isStepCompleted = (stepIndex: number) => {
    return getStepCompletionStatus(steps[stepIndex].id);
  };

  const CurrentStepComponent = steps[currentStep]?.component;

  return (
    <div className="w-full max-w-6xl mx-auto flex gap-6">
      {/* Slidable Side Menu */}
      <div className={`transition-all duration-300 ease-in-out ${
        isMenuOpen ? 'w-80' : 'w-16'
      } flex-shrink-0`}>
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4 h-full">
          {/* Menu Toggle Button */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="w-full flex items-center justify-center p-2 mb-4 bg-white/10 hover:bg-white/20 rounded-lg transition-all duration-200"
          >
            <svg className={`w-6 h-6 text-white transition-transform duration-300 ${
              isMenuOpen ? 'rotate-180' : ''
            }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* Step Navigation */}
          <div className="space-y-3">
            {steps.map((step, index) => (
              <button
                key={step.id}
                onClick={() => handleStepClick(index)}
                className={`w-full flex items-center ${isMenuOpen ? 'p-3' : 'p-2 justify-center'} rounded-lg transition-all duration-200 ${
                   index === currentStep
                     ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg'
                     : isStepCompleted(index)
                     ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                     : 'bg-white/5 text-gray-400 hover:bg-white/10 border border-white/10'
                 }`}
              >
                {/* Step Number/Icon */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0 ${
                   index === currentStep
                     ? 'bg-white/20'
                     : isStepCompleted(index)
                     ? 'bg-green-500'
                     : 'bg-white/10'
                 }`}>
                   {isStepCompleted(index) ? (
                     <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                       <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                     </svg>
                   ) : (
                     index + 1
                   )}
                 </div>
                
                {/* Step Title */}
                {isMenuOpen && (
                  <span className="ml-3 text-sm font-medium truncate">
                    {step.title}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Progress Indicator */}
          {isMenuOpen && (
            <div className="mt-6 p-3 bg-white/5 rounded-lg border border-white/10">
              <div className="flex items-center justify-between mb-2">
                 <span className="text-sm text-gray-300">Progress</span>
                 <span className="text-sm text-white font-medium">
                   {Math.round((steps.filter((_, index) => isStepCompleted(index)).length / steps.length) * 100)}%
                 </span>
               </div>
               <div className="w-full bg-white/10 rounded-full h-2">
                 <div 
                   className="bg-gradient-to-r from-indigo-500 to-purple-600 h-2 rounded-full transition-all duration-300"
                   style={{ 
                     width: `${(steps.filter((_, index) => isStepCompleted(index)).length / steps.length) * 100}%` 
                   }}
                 />
               </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 min-w-0">
        {/* Top Progress Bar (Mobile/Compact View) */}
        <div className="mb-6 bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-semibold text-white">
              {steps[currentStep]?.title}
            </h2>
            <span className="text-sm text-gray-300">
              Step {currentStep + 1} of {steps.length}
            </span>
          </div>
          
          {/* Compact Progress Bar */}
          <div className="w-full bg-white/10 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-indigo-500 to-purple-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Form Content */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6 min-h-[500px] transition-all duration-300">
          {CurrentStepComponent && <CurrentStepComponent />}
        </div>

        {/* Navigation Buttons */}
        <div className="flex justify-between mt-6">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 0}
            className="px-6 py-3 bg-white/10 text-white rounded-lg border border-white/20 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Previous
          </button>
          
          <button
            onClick={handleNext}
            disabled={currentStep === steps.length - 1}
            className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg hover:from-indigo-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg flex items-center gap-2"
          >
            Next
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}