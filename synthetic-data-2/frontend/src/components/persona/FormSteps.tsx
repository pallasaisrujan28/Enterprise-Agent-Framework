'use client';

import React from 'react';
import { useFormContext, PersonaFormData, ageRanges, educationLevels, familyStatus, incomeBrackets, personalityTraits, interests, values, lifestyleOptions, industries, productCategories, mediaConsumptionOptions, decisionMakingStyles, decisionMakingInfluences, goalOptions, timelineOptions, geographicData } from './FormContext';
import {
  audienceEducationLevels,
  audienceIncomeBrackets,
  audiencePersonalityTraits,
  audienceValues,
  audienceLifestyleOptions,
  audienceInterests,
  audienceGoalOptions
} from './AudiencePersonaConfig';
import { 
  AudienceShoppingBehaviorStep, 
  AudienceBrandPreferencesStep, 
  AudienceInfluenceStep 
} from './AudienceFormSteps';
import { RangeSlider, GenderDistribution, LikertScale, MultiSelect } from './inputs';

// Basic Information Step
export const BasicInformationStep: React.FC = () => {
  const { formData, validation, updateFormData, updateNestedFormData } = useFormContext();

  const handleGenderDistributionChange = (gender: 'male' | 'female', value: number) => {
    const clampedValue = Math.min(100, Math.max(0, value));
    const otherGender = gender === 'male' ? 'female' : 'male';
    const otherValue = 100 - clampedValue;
    
    updateFormData('basicInfo', 'genderDistribution', {
      [gender]: clampedValue,
      [otherGender]: otherValue
    });
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Persona Name *
          </label>
          <input
            type="text"
            value={formData.basicInfo.name}
            onChange={(e) => updateFormData('basicInfo', 'name', e.target.value)}
            className={`w-full px-4 py-3 bg-white/10 border rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 transition-all duration-200 ${
              validation.basicInfo.name.length > 0
                ? 'border-red-500 focus:ring-red-500'
                : 'border-white/20 focus:ring-indigo-500'
            }`}
            placeholder="Enter persona name"
          />
          {validation.basicInfo.name.length > 0 && (
            <p className="mt-1 text-sm text-red-400">{validation.basicInfo.name[0]}</p>
          )}
        </div>

        {/* Age Range */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Age Range *
          </label>
          <select
            value={formData.basicInfo.ageRange}
            onChange={(e) => updateFormData('basicInfo', 'ageRange', e.target.value)}
            className={`w-full px-4 py-3 bg-white/10 border rounded-lg text-white focus:outline-none focus:ring-2 transition-all duration-200 ${
              validation.basicInfo.ageRange.length > 0
                ? 'border-red-500 focus:ring-red-500'
                : 'border-white/20 focus:ring-indigo-500'
            }`}
          >
            <option value="">Select age range</option>
            {ageRanges.map((range) => (
              <option key={range.value} value={range.value} className="bg-gray-800">
                {range.label}
              </option>
            ))}
          </select>
          {validation.basicInfo.ageRange.length > 0 && (
            <p className="mt-1 text-sm text-red-400">{validation.basicInfo.ageRange[0]}</p>
          )}
        </div>
      </div>

      {/* Gender Distribution */}
      <GenderDistribution
        value={formData.basicInfo.genderDistribution}
        onChange={(value) => {
          updateFormData('basicInfo', 'genderDistribution', value);
        }}
      />

      {/* Location */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Location *
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Country */}
          <select
            value={formData.basicInfo.location.country}
            onChange={(e) => {
              updateNestedFormData('basicInfo', 'location', 'country', e.target.value);
              updateNestedFormData('basicInfo', 'location', 'state', '');
              updateNestedFormData('basicInfo', 'location', 'city', '');
            }}
            className={`px-4 py-3 bg-white/10 border rounded-lg text-white focus:outline-none focus:ring-2 transition-all duration-200 ${
              validation.basicInfo.location.length > 0
                ? 'border-red-500 focus:ring-red-500'
                : 'border-white/20 focus:ring-indigo-500'
            }`}
          >
            <option value="">Select country</option>
            {Object.keys(geographicData).map((country) => (
              <option key={country} value={country} className="bg-gray-800">
                {country}
              </option>
            ))}
          </select>

          {/* State */}
          <select
             value={formData.basicInfo.location.state}
             onChange={(e) => {
               updateNestedFormData('basicInfo', 'location', 'state', e.target.value);
               updateNestedFormData('basicInfo', 'location', 'city', '');
             }}
             disabled={!formData.basicInfo.location.country}
             className="px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200 disabled:opacity-50"
           >
             <option value="">Select state</option>
             {formData.basicInfo.location.country && geographicData[formData.basicInfo.location.country as keyof typeof geographicData] &&
               Object.keys(geographicData[formData.basicInfo.location.country as keyof typeof geographicData]).map((state) => (
                 <option key={state} value={state} className="bg-gray-800">
                   {state}
                 </option>
               ))
             }
           </select>

          {/* City */}
          <select
             value={formData.basicInfo.location.city}
             onChange={(e) => updateNestedFormData('basicInfo', 'location', 'city', e.target.value)}
             disabled={!formData.basicInfo.location.state}
             className="px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200 disabled:opacity-50"
           >
             <option value="">Select city</option>
             {(() => {
               const country = formData.basicInfo.location.country;
               const state = formData.basicInfo.location.state;
               if (country && state && geographicData[country as keyof typeof geographicData]) {
                 const countryData = geographicData[country as keyof typeof geographicData] as Record<string, string[]>;
                 const cities = countryData[state];
                 if (cities) {
                   return cities.map((city: string) => (
                     <option key={city} value={city} className="bg-gray-800">
                       {city}
                     </option>
                   ));
                 }
               }
               return null;
             })()
             }
           </select>
        </div>
        {validation.basicInfo.location.length > 0 && (
          <p className="mt-1 text-sm text-red-400">{validation.basicInfo.location[0]}</p>
        )}
      </div>
    </div>
  );
};

// Export professional and audience specific steps
export { 
  AudienceShoppingBehaviorStep,
  AudienceBrandPreferencesStep,
  AudienceInfluenceStep
};

// Demographics Step
export const DemographicsStep: React.FC = () => {
  const { formData, validation, updateFormData, updateNestedFormData } = useFormContext();

  // Use audience configurations
  const currentEducationLevels = audienceEducationLevels;
  const currentIncomeBrackets = audienceIncomeBrackets;

  return (
    <div className="space-y-6">
      {/* Note: Age Range and Gender Distribution are in Basic Info step, not Demographics */}
        {/* This step focuses on occupation, education, income, and family status */}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Education */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Education Level *
          </label>
          <select
            value={formData.demographics.education}
            onChange={(e) => updateFormData('demographics', 'education', e.target.value)}
            className={`w-full px-4 py-3 bg-white/10 border rounded-lg text-white focus:outline-none focus:ring-2 transition-all duration-200 ${
              validation.demographics.education.length > 0
                ? 'border-red-500 focus:ring-red-500'
                : 'border-white/20 focus:ring-indigo-500'
            }`}
          >
            <option value="">Select education level</option>
            {currentEducationLevels.map((level) => (
              <option key={level.value} value={level.value} className="bg-gray-800">
                {level.label}
              </option>
            ))}
          </select>
          {validation.demographics.education.length > 0 && (
            <p className="mt-1 text-sm text-red-400">{validation.demographics.education[0]}</p>
          )}
        </div>

        {/* Income */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Income Bracket *
          </label>
          <select
            value={formData.demographics.income}
            onChange={(e) => updateFormData('demographics', 'income', e.target.value)}
            className={`w-full px-4 py-3 bg-white/10 border rounded-lg text-white focus:outline-none focus:ring-2 transition-all duration-200 ${
              validation.demographics.income.length > 0
                ? 'border-red-500 focus:ring-red-500'
                : 'border-white/20 focus:ring-indigo-500'
            }`}
          >
            <option value="">Select income bracket</option>
            {currentIncomeBrackets.map((bracket) => (
              <option key={bracket.value} value={bracket.value} className="bg-gray-800">
                {bracket.label}
              </option>
            ))}
          </select>
          {validation.demographics.income.length > 0 && (
            <p className="mt-1 text-sm text-red-400">{validation.demographics.income[0]}</p>
          )}
        </div>

        {/* Family Status */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Family Status
          </label>
          <select
            value={formData.demographics.familyStatus}
            onChange={(e) => updateFormData('demographics', 'familyStatus', e.target.value)}
            className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200"
          >
            <option value="">Select family status</option>
            {familyStatus.map((status) => (
              <option key={status.value} value={status.value} className="bg-gray-800">
                {status.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};

// Personality Step
export const PersonalityStep: React.FC = () => {
  const { formData, validation, updateFormData } = useFormContext();

  // Use audience configurations
  const currentPersonalityTraits = audiencePersonalityTraits;
  const currentValues = audienceValues;
  const currentLifestyleOptions = audienceLifestyleOptions;

  const handleMultiSelect = (field: 'traits' | 'values' | 'lifestyle', value: string) => {
    const currentValues = formData.personality[field];
    const newValues = currentValues.includes(value)
      ? currentValues.filter(v => v !== value)
      : [...currentValues, value];
    updateFormData('personality', field, newValues);
  };

  return (
    <div className="space-y-8">
      {/* Personality Traits */}
      <MultiSelect
          label="Personality Traits"
          options={currentPersonalityTraits}
          value={formData.personality.traits}
          onChange={(value) => updateFormData('personality', 'traits', value)}
          maxSelections={6}
          searchable={true}
          placeholder="Search personality traits..."
        />

      {/* Values */}
      <MultiSelect
          label="Core Values"
          options={currentValues}
          value={formData.personality.values}
          onChange={(value) => updateFormData('personality', 'values', value)}
          maxSelections={5}
          searchable={true}
          placeholder="Search values..."
        />

      {/* Lifestyle */}
      <MultiSelect
        label="Lifestyle Characteristics"
        options={currentLifestyleOptions}
        value={formData.personality.lifestyle}
        onChange={(value) => updateFormData('personality', 'lifestyle', value)}
        maxSelections={8}
        searchable={true}
        placeholder="Search lifestyle options..."
      />
    </div>
  );
};

// Behavioral Step
export const BehavioralStep: React.FC = () => {
  const { formData, updateFormData } = useFormContext();

  return (
    <div className="space-y-8">
      <div className="text-center mb-8">
        <h3 className="text-lg font-medium text-white mb-2">Behavioral Attributes</h3>
        <p className="text-gray-400">Rate each attribute on a scale of 1-5</p>
      </div>

      <div className="space-y-8">
        {/* Price Sensitivity */}
        <LikertScale
          label="Price Sensitivity"
          value={formData.behavioral.priceSensitivity}
          onChange={(value) => updateFormData('behavioral', 'priceSensitivity', value)}
          labels={['Very Low', 'Low', 'Moderate', 'High', 'Very High']}
        />

        {/* Brand Loyalty */}
        <LikertScale
          label="Brand Loyalty"
          value={formData.behavioral.brandLoyalty}
          onChange={(value) => updateFormData('behavioral', 'brandLoyalty', value)}
          labels={['Very Low', 'Low', 'Moderate', 'High', 'Very High']}
        />

        {/* Online Shopping Preference */}
        <LikertScale
          label="Online Shopping Preference"
          value={formData.behavioral.onlineShoppingPreference}
          onChange={(value) => updateFormData('behavioral', 'onlineShoppingPreference', value)}
          labels={['Strongly Offline', 'Prefer Offline', 'No Preference', 'Prefer Online', 'Strongly Online']}
        />

        {/* Innovation vs Tradition */}
        <LikertScale
          label="Innovation vs Tradition"
          value={formData.behavioral.innovationVsTradition}
          onChange={(value) => updateFormData('behavioral', 'innovationVsTradition', value)}
          labels={['Very Traditional', 'Traditional', 'Balanced', 'Innovative', 'Very Innovative']}
        />

        {/* Individual vs Community */}
        <LikertScale
          label="Individual vs Community Focus"
          value={formData.behavioral.individualVsCommunity}
          onChange={(value) => updateFormData('behavioral', 'individualVsCommunity', value)}
          labels={['Very Individual', 'Individual', 'Balanced', 'Community', 'Very Community']}
        />

        {/* Security vs Adventure */}
        <LikertScale
          label="Security vs Adventure"
          value={formData.behavioral.securityVsAdventure}
          onChange={(value) => updateFormData('behavioral', 'securityVsAdventure', value)}
          labels={['Very Security', 'Security', 'Balanced', 'Adventure', 'Very Adventure']}
        />
      </div>
    </div>
  );
};

// Media Consumption Step
export const MediaConsumptionStep: React.FC = () => {
  const { formData, updateFormData, mediaConsumptionOptions } = useFormContext();

  // Use audience media consumption options
  const currentMediaConsumptionOptions = mediaConsumptionOptions;

  return (
    <div className="space-y-8">
      <div className="text-center mb-8">
        <h3 className="text-xl font-semibold text-white mb-2">
          Media Consumption
        </h3>
        <p className="text-white/70">
          Select media platforms and influences
        </p>
      </div>

      {/* Media Platforms */}
      <MultiSelect
        label="Media Platforms"
        options={currentMediaConsumptionOptions.platforms}
        value={formData.mediaConsumption.platforms}
        onChange={(values) => updateFormData('mediaConsumption', 'platforms', values)}
        placeholder="Select media platforms..."
        maxSelections={10}
      />

      {/* Decision Influences */}
      <MultiSelect
        label="Decision Influences"
        options={currentMediaConsumptionOptions.influences}
        value={formData.mediaConsumption.influences}
        onChange={(values) => updateFormData('mediaConsumption', 'influences', values)}
        placeholder="Select decision influences..."
        maxSelections={8}
      />

      {/* Content Preferences */}
      <div className="space-y-4">
        <label className="block text-sm font-medium text-white">
          Content Preferences
        </label>
        <textarea
          value={formData.mediaConsumption.contentPreferences}
          onChange={(e) => updateFormData('mediaConsumption', 'contentPreferences', e.target.value)}
          placeholder="Describe preferred content types, genres, topics..."
          className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
          rows={4}
        />
      </div>
    </div>
  );
};

// Decision Making Step
export const DecisionMakingStep: React.FC = () => {
  const { formData, validation, updateFormData } = useFormContext();

  // Use standard decision making influences
  const currentDecisionInfluences = decisionMakingInfluences;

  return (
    <div className="space-y-8">
      <div className="text-center mb-8">
        <h3 className="text-xl font-semibold text-white mb-2">Decision Making Style</h3>
        <p className="text-white/70">How does this persona typically make purchasing decisions?</p>
      </div>

      {/* Decision Making Style */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-4">
          Primary Decision Making Style *
        </label>
        <div className="space-y-3">
          {decisionMakingStyles.map((style) => (
            <button
              key={style.value}
              type="button"
              onClick={() => updateFormData('decisionMaking', 'style', style.value)}
              className={`w-full p-4 rounded-lg border text-left transition-all duration-200 ${
                formData.decisionMaking.style === style.value
                  ? 'bg-indigo-500 border-indigo-400 text-white'
                  : 'bg-white/5 border-white/20 text-gray-300 hover:bg-white/10'
              }`}
            >
                <div className="font-medium">{style.label}</div>
              </button>
          ))}
        </div>
        {validation.decisionMaking.style.length > 0 && (
          <p className="mt-2 text-sm text-red-400">{validation.decisionMaking.style[0]}</p>
        )}
      </div>

      {/* Decision Influences */}
      <MultiSelect
        label="Decision Influences"
        options={currentDecisionInfluences}
        value={formData.decisionMaking.influences}
        onChange={(values) => updateFormData('decisionMaking', 'influences', values)}
        placeholder="Select factors that influence decisions..."
        maxSelections={8}
        searchable={true}
      />
    </div>
  );
};

// Interests Step
export const InterestsStep: React.FC = () => {
  const { formData, validation, updateFormData } = useFormContext();

  // Use audience configurations
  const currentInterests = audienceInterests;

  const handleInterestToggle = (interest: string) => {
    const currentInterests = formData.interests.primary;
    const newInterests = currentInterests.includes(interest)
      ? currentInterests.filter(i => i !== interest)
      : [...currentInterests, interest];
    updateFormData('interests', 'primary', newInterests);
  };

  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h3 className="text-lg font-medium text-white mb-2">
          Primary Interests
        </h3>
        <p className="text-gray-400">
          Select the main areas of interest for this persona
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {currentInterests.map((interest) => (
          <button
            key={interest}
            type="button"
            onClick={() => handleInterestToggle(interest)}
            className={`p-4 rounded-lg border text-center font-medium transition-all duration-200 ${
              formData.interests.primary.includes(interest)
                ? 'bg-purple-500 border-purple-400 text-white'
                : 'bg-white/5 border-white/20 text-gray-300 hover:bg-white/10'
            }`}
          >
            {interest}
          </button>
        ))}
      </div>

      {validation.interests.primary.length > 0 && (
        <p className="mt-4 text-sm text-red-400 text-center">{validation.interests.primary[0]}</p>
      )}
    </div>
  );
};

// Context Step
export const ContextStep: React.FC = () => {
  const { formData, validation, updateFormData } = useFormContext();

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Industry */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Target Industry *
          </label>
          <select
            value={formData.context.industry}
            onChange={(e) => updateFormData('context', 'industry', e.target.value)}
            className={`w-full px-4 py-3 bg-white/10 border rounded-lg text-white focus:outline-none focus:ring-2 transition-all duration-200 ${
              validation.context.industry.length > 0
                ? 'border-red-500 focus:ring-red-500'
                : 'border-white/20 focus:ring-indigo-500'
            }`}
          >
            <option value="">Select industry</option>
            {industries.map((industry) => (
              <option key={industry} value={industry} className="bg-gray-800">
                {industry}
              </option>
            ))}
          </select>
          {validation.context.industry.length > 0 && (
            <p className="mt-1 text-sm text-red-400">{validation.context.industry[0]}</p>
          )}
        </div>

        {/* Product Category */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Product Category *
          </label>
          <select
            value={formData.context.productCategory}
            onChange={(e) => updateFormData('context', 'productCategory', e.target.value)}
            className={`w-full px-4 py-3 bg-white/10 border rounded-lg text-white focus:outline-none focus:ring-2 transition-all duration-200 ${
              validation.context.productCategory.length > 0
                ? 'border-red-500 focus:ring-red-500'
                : 'border-white/20 focus:ring-indigo-500'
            }`}
          >
            <option value="">Select product category</option>
            {productCategories.map((category) => (
              <option key={category} value={category} className="bg-gray-800">
                {category}
              </option>
            ))}
          </select>
          {validation.context.productCategory.length > 0 && (
            <p className="mt-1 text-sm text-red-400">{validation.context.productCategory[0]}</p>
          )}
        </div>
      </div>

      {/* Use Case */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Use Case Description
        </label>
        <textarea
          value={formData.context.useCase}
          onChange={(e) => updateFormData('context', 'useCase', e.target.value)}
          rows={4}
          className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200"
          placeholder="Describe how this persona will be used (e.g., market research, product development, user testing...)"
        />
      </div>
    </div>
  );
};

// Goals Step
export const GoalsStep: React.FC = () => {
  const { formData, validation, updateFormData } = useFormContext();

  // Use audience configurations
  const currentGoalOptions = audienceGoalOptions;

  const handleSecondaryGoalToggle = (goal: string) => {
    const currentGoals = formData.goals.secondary;
    const newGoals = currentGoals.includes(goal)
      ? currentGoals.filter(g => g !== goal)
      : [...currentGoals, goal];
    updateFormData('goals', 'secondary', newGoals);
  };

  return (
    <div className="space-y-8">
      {/* Primary Goal */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-4">
          Primary Goal *
        </label>
        <div className="space-y-3">
          {currentGoalOptions.map((goal) => (
            <button
              key={goal}
              type="button"
              onClick={() => updateFormData('goals', 'primary', goal)}
              className={`w-full p-3 rounded-lg border text-left transition-all duration-200 ${
                formData.goals.primary === goal
                  ? 'bg-indigo-500 border-indigo-400 text-white'
                  : 'bg-white/5 border-white/20 text-gray-300 hover:bg-white/10'
              }`}
            >
              {goal}
            </button>
          ))}
        </div>
        {validation.goals.primary.length > 0 && (
          <p className="mt-2 text-sm text-red-400">{validation.goals.primary[0]}</p>
        )}
      </div>

      {/* Secondary Goals */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-4">
          Secondary Goals (Select multiple)
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {currentGoalOptions.filter(goal => goal !== formData.goals.primary).map((goal) => (
            <button
              key={goal}
              type="button"
              onClick={() => handleSecondaryGoalToggle(goal)}
              className={`p-3 rounded-lg border text-sm font-medium transition-all duration-200 ${
                formData.goals.secondary.includes(goal)
                  ? 'bg-green-500 border-green-400 text-white'
                  : 'bg-white/5 border-white/20 text-gray-300 hover:bg-white/10'
              }`}
            >
              {goal}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Timeline
        </label>
        <select
          value={formData.goals.timeline}
          onChange={(e) => updateFormData('goals', 'timeline', e.target.value)}
          className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200"
        >
          <option value="">Select timeline</option>
          {timelineOptions.map((option) => (
            <option key={option.value} value={option.value} className="bg-gray-800">
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

// Review Step
export const ReviewStep: React.FC = () => {
  const { formData } = useFormContext();

  return (
    <div className="space-y-8">
      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold text-white mb-2">Persona Summary</h3>
        <p className="text-gray-400">Review your persona details before generating</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Basic Information */}
        <div className="bg-white/5 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-white mb-4">Basic Information</h4>
          <div className="space-y-2 text-sm">
            <div><span className="text-gray-400">Name:</span> <span className="text-white">{formData.basicInfo.name || 'Not specified'}</span></div>
            <div><span className="text-gray-400">Age Range:</span> <span className="text-white">{formData.basicInfo.ageRange || 'Not specified'}</span></div>
            <div><span className="text-gray-400">Location:</span> <span className="text-white">{formData.basicInfo.location.city ? `${formData.basicInfo.location.city}, ${formData.basicInfo.location.state}, ${formData.basicInfo.location.country}` : 'Not specified'}</span></div>
            <div><span className="text-gray-400">Gender Distribution:</span> <span className="text-white">{`${formData.basicInfo.genderDistribution.male}% Male, ${formData.basicInfo.genderDistribution.female}% Female`}</span></div>
          </div>
        </div>

        {/* Demographics */}
        <div className="bg-white/5 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-white mb-4">Demographics</h4>
          <div className="space-y-2 text-sm">
            <div><span className="text-gray-400">Occupation:</span> <span className="text-white">{formData.demographics.occupation || 'Not specified'}</span></div>
            <div><span className="text-gray-400">Education:</span> <span className="text-white">{formData.demographics.education || 'Not specified'}</span></div>
            <div><span className="text-gray-400">Income:</span> <span className="text-white">{formData.demographics.income || 'Not specified'}</span></div>
            <div><span className="text-gray-400">Family Status:</span> <span className="text-white">{formData.demographics.familyStatus || 'Not specified'}</span></div>
          </div>
        </div>

        {/* Personality */}
        <div className="bg-white/5 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-white mb-4">Personality</h4>
          <div className="space-y-2 text-sm">
            <div><span className="text-gray-400">Traits:</span> <span className="text-white">{formData.personality.traits?.length > 0 ? formData.personality.traits.join(', ') : 'None selected'}</span></div>
            <div><span className="text-gray-400">Values:</span> <span className="text-white">{formData.personality.values?.length > 0 ? formData.personality.values.join(', ') : 'None selected'}</span></div>
            <div><span className="text-gray-400">Lifestyle:</span> <span className="text-white">{formData.personality.lifestyle?.length > 0 ? formData.personality.lifestyle.join(', ') : 'None selected'}</span></div>
          </div>
        </div>

        {/* Behavioral & Interests */}
        <div className="bg-white/5 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-white mb-4">Behavioral & Interests</h4>
          <div className="space-y-2 text-sm">
            <div><span className="text-gray-400">Price Sensitivity:</span> <span className="text-white">{formData.behavioral.priceSensitivity}/5</span></div>
            <div><span className="text-gray-400">Brand Loyalty:</span> <span className="text-white">{formData.behavioral.brandLoyalty}/5</span></div>
            <div><span className="text-gray-400">Online Shopping Preference:</span> <span className="text-white">{formData.behavioral.onlineShoppingPreference}/5</span></div>
            <div><span className="text-gray-400">Primary Interests:</span> <span className="text-white">{formData.interests.primary?.length > 0 ? formData.interests.primary.join(', ') : 'Not specified'}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
};