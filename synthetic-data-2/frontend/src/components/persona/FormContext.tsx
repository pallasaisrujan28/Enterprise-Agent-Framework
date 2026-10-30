'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react';

// Geographic Data
export const geographicData = {
  'United States': {
    'California': ['Los Angeles', 'San Francisco', 'San Diego', 'Sacramento'],
    'New York': ['New York City', 'Buffalo', 'Rochester', 'Syracuse'],
    'Texas': ['Houston', 'Dallas', 'Austin', 'San Antonio'],
    'Florida': ['Miami', 'Orlando', 'Tampa', 'Jacksonville'],
    'Illinois': ['Chicago', 'Springfield', 'Rockford', 'Peoria']
  },
  'United Kingdom': {
    'England': ['London', 'Manchester', 'Birmingham', 'Liverpool'],
    'Scotland': ['Edinburgh', 'Glasgow', 'Aberdeen', 'Dundee'],
    'Wales': ['Cardiff', 'Swansea', 'Newport', 'Wrexham'],
    'Northern Ireland': ['Belfast', 'Derry', 'Lisburn', 'Newry']
  },
  'Canada': {
    'Ontario': ['Toronto', 'Ottawa', 'Hamilton', 'London'],
    'Quebec': ['Montreal', 'Quebec City', 'Laval', 'Gatineau'],
    'British Columbia': ['Vancouver', 'Victoria', 'Surrey', 'Burnaby'],
    'Alberta': ['Calgary', 'Edmonton', 'Red Deer', 'Lethbridge']
  },
  'Australia': {
    'New South Wales': ['Sydney', 'Newcastle', 'Wollongong', 'Wagga Wagga'],
    'Victoria': ['Melbourne', 'Geelong', 'Ballarat', 'Bendigo'],
    'Queensland': ['Brisbane', 'Gold Coast', 'Townsville', 'Cairns'],
    'Western Australia': ['Perth', 'Fremantle', 'Bunbury', 'Geraldton']
  },
  'Germany': {
    'Bavaria': ['Munich', 'Nuremberg', 'Augsburg', 'Regensburg'],
    'North Rhine-Westphalia': ['Cologne', 'Düsseldorf', 'Dortmund', 'Essen'],
    'Berlin': ['Berlin'],
    'Hamburg': ['Hamburg']
  }
};

// Predefined Options
export const ageRanges = [
  { value: '18-24', label: '18-24 years (Gen Z)' },
  { value: '25-34', label: '25-34 years (Millennials)' },
  { value: '35-44', label: '35-44 years (Millennials/Gen X)' },
  { value: '45-54', label: '45-54 years (Gen X)' },
  { value: '55-64', label: '55-64 years (Baby Boomers)' },
  { value: '65+', label: '65+ years (Baby Boomers)' }
];



export const educationLevels = [
  { value: 'high-school', label: 'High School' },
  { value: 'bachelors', label: "Bachelor's Degree" },
  { value: 'masters', label: "Master's Degree" },
  { value: 'phd', label: 'PhD' }
];

export const familyStatus = [
  { value: 'single', label: 'Single' },
  { value: 'married', label: 'Married' },
  { value: 'divorced', label: 'Divorced' }
];

export const incomeBrackets = [
  { label: '<$30k', value: 'under-30k', min: 0, max: 30000 },
  { label: '$30-50k', value: '30k-50k', min: 30000, max: 50000 },
  { label: '$50-75k', value: '50k-75k', min: 50000, max: 75000 },
  { label: '$75-100k', value: '75k-100k', min: 75000, max: 100000 },
  { label: '$100k+', value: '100k-plus', min: 100000, max: 500000 }
];

export const personalityTraits = [
  'Analytical', 'Creative', 'Outgoing', 'Introverted', 'Ambitious', 'Empathetic',
  'Detail-oriented', 'Spontaneous', 'Logical', 'Intuitive', 'Collaborative', 'Independent',
  'Tech-savvy', 'Risk-taker', 'Conservative', 'Optimistic', 'Pragmatic', 'Innovative',
  'Patient', 'Decisive', 'Curious', 'Methodical', 'Adaptable', 'Goal-oriented',
  'Social', 'Reserved', 'Confident', 'Cautious', 'Perfectionist', 'Flexible'
];

export const interests = [
  'Technology', 'Travel', 'Sports', 'Reading', 'Music', 'Art', 'Cooking',
  'Photography', 'Gaming', 'Fitness', 'Nature', 'Fashion', 'Movies', 'Learning'
];

export const values = [
  'Family', 'Career Growth', 'Financial Security', 'Work-Life Balance',
  'Innovation', 'Sustainability', 'Community', 'Adventure', 'Stability', 'Creativity'
];

export const lifestyleOptions = [
  'Early adopter', 'Eco-conscious', 'Health-focused', 'Tech-savvy',
  'Budget-conscious', 'Luxury-oriented', 'Minimalist', 'Social media active',
  'Fitness enthusiast', 'Foodie', 'Travel lover', 'Homebody',
  'Night owl', 'Early riser', 'Urban dweller', 'Suburban lifestyle',
  'Remote worker', 'Entrepreneur', 'Family-oriented', 'Career-driven',
  'Creative', 'Analytical', 'Risk-taker', 'Conservative'
];

export const industries = [
  'Technology', 'Healthcare', 'Finance', 'Retail', 'Education', 'Manufacturing',
  'Real Estate', 'Automotive', 'Food & Beverage', 'Entertainment', 'Travel & Tourism',
  'Fashion', 'Sports & Fitness', 'Beauty & Cosmetics', 'Home & Garden', 'Other'
];

export const productCategories = [
  'Software/Apps', 'Hardware/Electronics', 'Clothing/Apparel', 'Food Products',
  'Health/Wellness', 'Financial Services', 'Educational Services', 'Entertainment',
  'Home Goods', 'Automotive', 'Beauty Products', 'Sports Equipment',
  'Travel Services', 'Professional Services', 'Other'
];

export const mediaConsumptionOptions = {
  platforms: ['Social Media', 'Television', 'Podcasts', 'News', 'Streaming', 'Radio'],
  influences: ['Friends & Family', 'Social Media Influencers', 'Online Reviews', 'Traditional Advertising', 'Expert Opinions', 'Celebrity Endorsements', 'User-Generated Content', 'Brand Reputation']
};

export const decisionMakingStyles = [
  { value: 'impulsive', label: 'Impulsive' },
  { value: 'researched', label: 'Researched' },
  { value: 'peer-influenced', label: 'Peer Influenced' }
];

export const decisionMakingInfluences = [
  'Friends & Family', 'Online Reviews', 'Social Media', 'Expert Opinions',
  'Brand Reputation', 'Price Comparison', 'Personal Experience', 'Advertising',
  'Quality', 'Convenience', 'Environmental Impact', 'Innovation'
];

export const goalOptions = [
  'Increase brand awareness', 'Drive sales growth', 'Improve customer satisfaction',
  'Launch new product', 'Enter new market', 'Enhance user experience',
  'Build customer loyalty', 'Reduce churn rate', 'Optimize pricing strategy',
  'Improve product features', 'Expand market share', 'Increase engagement'
];

export const timelineOptions = [
  { value: 'immediate', label: 'Immediate (0-3 months)' },
  { value: 'short-term', label: 'Short-term (3-6 months)' },
  { value: 'medium-term', label: 'Medium-term (6-12 months)' },
  { value: 'long-term', label: 'Long-term (1+ years)' }
];

// Form Data Interface
export interface PersonaFormData {
  basicInfo: {
    name: string;
    ageRange: string;
    genderDistribution: {
      male: number;
      female: number;
    };
    location: {
      country: string;
      state: string;
      city: string;
    };
  };
  demographics: {
    education: string;
    income: string;
    familyStatus: string;
  };
  personality: {
    traits: string[];
    values: string[];
    lifestyle: string[];
  };
  behavioral: {
    priceSensitivity: number; // 1-5 scale
    brandLoyalty: number; // 1-5 scale
    onlineShoppingPreference: number; // 1-5 scale
    innovationVsTradition: number; // 1-5 scale
    individualVsCommunity: number; // 1-5 scale
    securityVsAdventure: number; // 1-5 scale
  };
  mediaConsumption: {
    platforms: string[];
    influences: string[];
    contentPreferences: string;
  };
  decisionMaking: {
    style: string;
    influences: string[];
  };
  interests: {
    primary: string[];
    categories: { [key: string]: string[] };
  };
  context: {
    industry: string;
    productCategory: string;
    useCase: string;
  };
  goals: {
    primary: string;
    secondary: string[];
    timeline: string;
  };
  audience: {
    shoppingBehaviors: string[];
    purchaseMotivations: string[];
    shoppingFrequency: string;
    brandPreferences: string[];
    budgetConsiderations: string[];
    preferredChannels: string;
    informationSources: string[];
    socialInfluence: string[];
    decisionProcess: string;
    painPoints: string;
  };
}

// Form Validation Interface
export interface PersonaFormValidation {
  basicInfo: {
    name: string[];
    ageRange: string[];
    genderDistribution: string[];
    location: string[];
  };
  demographics: {
    education: string[];
    income: string[];
    familyStatus: string[];
  };
  personality: {
    traits: string[];
    values: string[];
    lifestyle: string[];
  };
  behavioral: {
    priceSensitivity: string[];
    brandLoyalty: string[];
    onlineShoppingPreference: string[];
    innovationVsTradition: string[];
    individualVsCommunity: string[];
    securityVsAdventure: string[];
  };
  mediaConsumption: {
    platforms: string[];
    influences: string[];
    contentPreferences: string[];
  };
  decisionMaking: {
    style: string[];
    influences: string[];
  };
  interests: {
    primary: string[];
    categories: string[];
  };
  context: {
    industry: string[];
    productCategory: string[];
    useCase: string[];
  };
  goals: {
    primary: string[];
    secondary: string[];
    timeline: string[];
  };
  audience: {
    shoppingBehaviors: string[];
    purchaseMotivations: string[];
    shoppingFrequency: string[];
    brandPreferences: string[];
    budgetConsiderations: string[];
    preferredChannels: string[];
    informationSources: string[];
    socialInfluence: string[];
    decisionProcess: string[];
    painPoints: string[];
  };
}

// Form Context Type
export interface FormContextType {
  formData: PersonaFormData;
  validation: PersonaFormValidation;
  updateFormData: (section: keyof PersonaFormData, field: string, value: any) => void;
  updateNestedFormData: (section: keyof PersonaFormData, subsection: string, field: string, value: any) => void;
  validateField: (section: keyof PersonaFormData, field: string, value: any) => string[];
  getStepCompletionStatus: (stepId: string) => boolean;
  isFormValid: () => boolean;
  clearFormData: () => void;
  mediaConsumptionOptions: typeof mediaConsumptionOptions;
  personalityTraits: typeof personalityTraits;
  interests: typeof interests;
  values: typeof values;
  lifestyleOptions: typeof lifestyleOptions;
  decisionMakingInfluences: typeof decisionMakingInfluences;
  goalOptions: typeof goalOptions;
  timelineOptions: typeof timelineOptions;
}

// Initial Form Data
export const initialFormData: PersonaFormData = {
  basicInfo: {
    name: '',
    ageRange: '',
    genderDistribution: {
      male: 50,
      female: 50
    },
    location: {
      country: '',
      state: '',
      city: ''
    }
  },
  demographics: {
    education: '',
    income: '',
    familyStatus: ''
  },
  personality: {
    traits: [],
    values: [],
    lifestyle: []
  },
  behavioral: {
    priceSensitivity: 3,
    brandLoyalty: 3,
    onlineShoppingPreference: 3,
    innovationVsTradition: 3,
    individualVsCommunity: 3,
    securityVsAdventure: 3
  },
  mediaConsumption: {
    platforms: [],
    influences: [],
    contentPreferences: ''
  },
  decisionMaking: {
    style: '',
    influences: []
  },
  interests: {
    primary: [],
    categories: {}
  },
  context: {
    industry: '',
    productCategory: '',
    useCase: ''
  },
  goals: {
    primary: '',
    secondary: [],
    timeline: ''
  },
  audience: {
    shoppingBehaviors: [],
    purchaseMotivations: [],
    shoppingFrequency: '',
    brandPreferences: [],
    budgetConsiderations: [],
    preferredChannels: '',
    informationSources: [],
    socialInfluence: [],
    decisionProcess: '',
    painPoints: ''
  }
};

// Initial Validation State
const initialValidation: PersonaFormValidation = {
  basicInfo: {
    name: [],
    ageRange: [],
    genderDistribution: [],
    location: []
  },
  demographics: {
    education: [],
    income: [],
    familyStatus: []
  },
  personality: {
    traits: [],
    values: [],
    lifestyle: []
  },
  behavioral: {
    priceSensitivity: [],
    brandLoyalty: [],
    onlineShoppingPreference: [],
    innovationVsTradition: [],
    individualVsCommunity: [],
    securityVsAdventure: []
  },
  mediaConsumption: {
    platforms: [],
    influences: [],
    contentPreferences: []
  },
  decisionMaking: {
    style: [],
    influences: []
  },
  interests: {
    primary: [],
    categories: []
  },
  context: {
    industry: [],
    productCategory: [],
    useCase: []
  },
  goals: {
    primary: [],
    secondary: [],
    timeline: []
  },
  audience: {
    shoppingBehaviors: [],
    purchaseMotivations: [],
    shoppingFrequency: [],
    brandPreferences: [],
    budgetConsiderations: [],
    preferredChannels: [],
    informationSources: [],
    socialInfluence: [],
    decisionProcess: [],
    painPoints: []
  }
};

// Step Validation Rules
const stepValidationRules: { [key: string]: string[] } = {
  'basic': ['basicInfo.name', 'basicInfo.ageRange', 'basicInfo.location.country'],
  'demographics': ['demographics.education', 'demographics.income'],
  'personality': ['personality.traits', 'personality.values'],
  'behavioral': [], // Behavioral fields have default values, so no validation needed
  'media': ['mediaConsumption.platforms'],
  'decision': ['decisionMaking.style'],
  'interests': ['interests.primary'],
  'context': ['context.industry', 'context.productCategory'],
  'goals': ['goals.primary', 'goals.timeline'],
  'review': []
};

// Create Context
const FormContext = createContext<FormContextType | undefined>(undefined);

// Form Provider Component
export const FormProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Initialize form data with empty values (no persistence)
  const [formData, setFormData] = useState<PersonaFormData>(initialFormData);
  const [validation, setValidation] = useState<PersonaFormValidation>(initialValidation);

  // Log form data state on mount
  useEffect(() => {
  }, []);

  // Log form data changes (no persistence)
  useEffect(() => {
  }, [formData]);

  const updateFormData = useCallback((section: keyof PersonaFormData, field: string, value: any) => {
    
    setFormData(prev => {
      const newData = {
        ...prev,
        [section]: {
          ...prev[section],
          [field]: value
        }
      };
      return newData;
    });

    // Validate the field
    const errors = validateField(section, field, value);
    setValidation(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: errors
      }
    }));
  }, []);

  const updateNestedFormData = useCallback((section: keyof PersonaFormData, subsection: string, field: string, value: any) => {
    
    setFormData(prev => {
      const newData = {
        ...prev,
        [section]: {
          ...prev[section],
          [subsection]: {
            ...(prev[section] as any)[subsection],
            [field]: value
          }
        }
      };
      return newData;
    });

    // Validate the nested field
    const fieldPath = `${section}.${subsection}.${field}`;
    const errors = validateField(section, fieldPath, value);
    setValidation(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [subsection]: {
          ...(prev[section] as any)[subsection],
          [field]: errors
        }
      }
    }));
  }, []);

  const validateField = (section: keyof PersonaFormData, field: string, value: any): string[] => {
    const errors: string[] = [];

    // Basic validation rules
    if (field.includes('name') && (!value || value.trim().length < 2)) {
      errors.push('Name must be at least 2 characters long');
    }

    if (field.includes('ageRange') && !value) {
      errors.push('Please select an age range');
    }

    if (field.includes('country') && !value) {
      errors.push('Please select a country');
    }

    if (field.includes('occupation') && !value) {
      errors.push('Please select an occupation');
    }

    if (field.includes('education') && !value) {
      errors.push('Please select an education level');
    }

    if (field.includes('income') && !value) {
      errors.push('Please select an income bracket');
    }

    if (field.includes('traits') && Array.isArray(value) && value.length === 0) {
      errors.push('Please select at least one personality trait');
    }

    if (field.includes('values') && Array.isArray(value) && value.length === 0) {
      errors.push('Please select at least one value');
    }

    if (field === 'platforms' && Array.isArray(value) && value.length === 0) {
      errors.push('Please select at least one media platform');
    }

    if (field === 'influences' && Array.isArray(value) && value.length === 0) {
      errors.push('Please select at least one influence');
    }

    if (field.includes('style') && !value) {
      errors.push('Please select a decision making style');
    }

    if (field.includes('primary') && Array.isArray(value) && value.length === 0) {
      errors.push('Please select at least one primary interest');
    }

    if (field.includes('industry') && !value) {
      errors.push('Please select an industry');
    }

    if (field.includes('productCategory') && !value) {
      errors.push('Please select a product category');
    }

    if (field === 'primary' && section === 'goals' && !value) {
      errors.push('Please select a primary goal');
    }

    if (field === 'timeline' && !value) {
      errors.push('Please select a timeline');
    }

    return errors;
  };

  const getNestedValue = (obj: any, path: string): any => {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  };

  const getStepCompletionStatus = (stepId: string): boolean => {
    const requiredFields = stepValidationRules[stepId] || [];
    
    return requiredFields.every(fieldPath => {
      const value = getNestedValue(formData, fieldPath);
      
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      
      return value !== '' && value !== null && value !== undefined;
    });
  };

  const isFormValid = (): boolean => {
    const allSteps = Object.keys(stepValidationRules);
    return allSteps.every(stepId => getStepCompletionStatus(stepId));
  };

  const clearFormData = useCallback(() => {
    setFormData(initialFormData);
    setValidation(initialValidation);
  }, []);

  const contextValue: FormContextType = {
    formData,
    validation,
    updateFormData,
    updateNestedFormData,
    validateField,
    getStepCompletionStatus,
    isFormValid,
    clearFormData,
    mediaConsumptionOptions,
    personalityTraits,
    interests,
    values,
    lifestyleOptions,
    decisionMakingInfluences,
    goalOptions,
    timelineOptions
  };

  return (
    <FormContext.Provider value={contextValue}>
      {children}
    </FormContext.Provider>
  );
};

// Custom Hook
export const useFormContext = (): FormContextType => {
  const context = useContext(FormContext);
  if (!context) {
    throw new Error('useFormContext must be used within a FormProvider');
  }
  return context;
};

export default FormContext;