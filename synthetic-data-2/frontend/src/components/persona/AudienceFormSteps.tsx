import React from 'react';
import { useFormContext } from './FormContext';
import {
  audienceShoppingBehaviors,
  audiencePurchaseMotivations,
  audienceBrandPreferences,
  audienceBudgetConsiderations,
  audienceShoppingFrequency,
  audienceInformationSources,
  audienceSocialInfluence
} from './AudiencePersonaConfig';

export const AudienceShoppingBehaviorStep: React.FC = () => {
  const { formData, validation, updateFormData } = useFormContext();

  return (
    <div className="space-y-8">
      <div className="text-center mb-8">
        <h3 className="text-xl font-semibold text-white mb-2">Shopping Behavior</h3>
        <p className="text-white/70">Define shopping patterns and behaviors</p>
      </div>

      {/* Shopping Behaviors */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Shopping Behaviors *
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {audienceShoppingBehaviors.map((behavior) => (
            <label key={behavior} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.audience?.shoppingBehaviors?.includes(behavior) || false}
                onChange={(e) => {
                  const current = formData.audience?.shoppingBehaviors || [];
                  const updated = e.target.checked
                    ? [...current, behavior]
                    : current.filter(b => b !== behavior);
                  updateFormData('audience', 'shoppingBehaviors', updated);
                }}
                className="rounded border-white/20 bg-white/10 text-indigo-500 focus:ring-indigo-500"
              />
              <span className="text-sm text-gray-300">{behavior}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Purchase Motivations */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Purchase Motivations *
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {audiencePurchaseMotivations.map((motivation) => (
            <label key={motivation} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.audience?.purchaseMotivations?.includes(motivation) || false}
                onChange={(e) => {
                  const current = formData.audience?.purchaseMotivations || [];
                  const updated = e.target.checked
                    ? [...current, motivation]
                    : current.filter(m => m !== motivation);
                  updateFormData('audience', 'purchaseMotivations', updated);
                }}
                className="rounded border-white/20 bg-white/10 text-indigo-500 focus:ring-indigo-500"
              />
              <span className="text-sm text-gray-300">{motivation}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Shopping Frequency */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Shopping Frequency *
        </label>
        <select
          value={formData.audience?.shoppingFrequency || ''}
          onChange={(e) => updateFormData('audience', 'shoppingFrequency', e.target.value)}
          className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200"
        >
          <option value="">Select shopping frequency</option>
          {audienceShoppingFrequency.map((freq) => (
            <option key={freq.value} value={freq.value} className="bg-gray-800">
              {freq.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export const AudienceBrandPreferencesStep: React.FC = () => {
  const { formData, validation, updateFormData } = useFormContext();

  return (
    <div className="space-y-8">
      <div className="text-center mb-8">
        <h3 className="text-xl font-semibold text-white mb-2">Brand Preferences</h3>
        <p className="text-white/70">Define brand loyalty and preferences</p>
      </div>

      {/* Brand Preferences */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Brand Preferences *
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {audienceBrandPreferences.map((preference) => (
            <label key={preference} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.audience?.brandPreferences?.includes(preference) || false}
                onChange={(e) => {
                  const current = formData.audience?.brandPreferences || [];
                  const updated = e.target.checked
                    ? [...current, preference]
                    : current.filter(p => p !== preference);
                  updateFormData('audience', 'brandPreferences', updated);
                }}
                className="rounded border-white/20 bg-white/10 text-indigo-500 focus:ring-indigo-500"
              />
              <span className="text-sm text-gray-300">{preference}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Budget Considerations */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Budget Considerations *
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {audienceBudgetConsiderations.map((consideration) => (
            <label key={consideration} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.audience?.budgetConsiderations?.includes(consideration) || false}
                onChange={(e) => {
                  const current = formData.audience?.budgetConsiderations || [];
                  const updated = e.target.checked
                    ? [...current, consideration]
                    : current.filter(c => c !== consideration);
                  updateFormData('audience', 'budgetConsiderations', updated);
                }}
                className="rounded border-white/20 bg-white/10 text-indigo-500 focus:ring-indigo-500"
              />
              <span className="text-sm text-gray-300">{consideration}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Preferred Shopping Channels */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Preferred Shopping Channels
        </label>
        <textarea
          value={formData.audience?.preferredChannels || ''}
          onChange={(e) => updateFormData('audience', 'preferredChannels', e.target.value)}
          placeholder="Describe preferred shopping channels (online, in-store, mobile app, etc.)..."
          className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200"
          rows={3}
        />
      </div>
    </div>
  );
};

export const AudienceInfluenceStep: React.FC = () => {
  const { formData, validation, updateFormData } = useFormContext();

  return (
    <div className="space-y-8">
      <div className="text-center mb-8">
        <h3 className="text-xl font-semibold text-white mb-2">Social Influence</h3>
        <p className="text-white/70">Define social influences and information sources</p>
      </div>

      {/* Information Sources */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Information Sources *
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {audienceInformationSources.map((source) => (
            <label key={source} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.audience?.informationSources?.includes(source) || false}
                onChange={(e) => {
                  const current = formData.audience?.informationSources || [];
                  const updated = e.target.checked
                    ? [...current, source]
                    : current.filter(s => s !== source);
                  updateFormData('audience', 'informationSources', updated);
                }}
                className="rounded border-white/20 bg-white/10 text-indigo-500 focus:ring-indigo-500"
              />
              <span className="text-sm text-gray-300">{source}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Social Influence */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Social Influence Factors *
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {audienceSocialInfluence.map((influence) => (
            <label key={influence} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.audience?.socialInfluence?.includes(influence) || false}
                onChange={(e) => {
                  const current = formData.audience?.socialInfluence || [];
                  const updated = e.target.checked
                    ? [...current, influence]
                    : current.filter(i => i !== influence);
                  updateFormData('audience', 'socialInfluence', updated);
                }}
                className="rounded border-white/20 bg-white/10 text-indigo-500 focus:ring-indigo-500"
              />
              <span className="text-sm text-gray-300">{influence}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Purchase Decision Process */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Purchase Decision Process
        </label>
        <textarea
          value={formData.audience?.decisionProcess || ''}
          onChange={(e) => updateFormData('audience', 'decisionProcess', e.target.value)}
          placeholder="Describe how this persona typically makes purchase decisions..."
          className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200"
          rows={4}
        />
      </div>

      {/* Pain Points */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Shopping Pain Points
        </label>
        <textarea
          value={formData.audience?.painPoints || ''}
          onChange={(e) => updateFormData('audience', 'painPoints', e.target.value)}
          placeholder="What frustrations or challenges does this persona face when shopping..."
          className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200"
          rows={4}
        />
      </div>
    </div>
  );
};