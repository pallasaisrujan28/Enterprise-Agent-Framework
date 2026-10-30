'use client';

import React from 'react';

// Audience-specific options (consumer-focused)

export const audienceEducationLevels = [
  { value: 'high-school', label: 'High School' },
  { value: 'some-college', label: 'Some College' },
  { value: 'associates', label: 'Associate Degree' },
  { value: 'bachelors', label: "Bachelor's Degree" },
  { value: 'masters', label: "Master's Degree" },
  { value: 'trade-school', label: 'Trade School/Vocational Training' }
];

export const audienceIncomeBrackets = [
  { label: 'Under $25k', value: 'under-25k', min: 0, max: 25000 },
  { label: '$25-40k', value: '25k-40k', min: 25000, max: 40000 },
  { label: '$40-60k', value: '40k-60k', min: 40000, max: 60000 },
  { label: '$60-80k', value: '60k-80k', min: 60000, max: 80000 },
  { label: '$80-100k', value: '80k-100k', min: 80000, max: 100000 },
  { label: '$100k+', value: '100k-plus', min: 100000, max: 200000 }
];

export const audiencePersonalityTraits = [
  // Consumer Behavior Traits
  'Price-conscious', 'Quality-focused', 'Brand-loyal', 'Trendy', 'Practical',
  'Impulsive', 'Research-oriented', 'Social', 'Independent', 'Family-oriented',
  
  // Lifestyle Traits
  'Active', 'Homebody', 'Adventurous', 'Cautious', 'Optimistic', 'Realistic',
  'Creative', 'Traditional', 'Tech-savvy', 'Eco-conscious', 'Health-conscious',
  
  // Social Traits
  'Outgoing', 'Introverted', 'Influential', 'Follower', 'Community-minded',
  'Individualistic', 'Collaborative', 'Competitive', 'Supportive', 'Skeptical',
  
  // Shopping Traits
  'Bargain hunter', 'Luxury seeker', 'Convenience-focused', 'Experience-seeker',
  'Value-oriented', 'Status-conscious', 'Minimalist', 'Collector'
];

export const audienceValues = [
  'Family', 'Friends', 'Health & Wellness', 'Financial Security', 'Fun & Entertainment',
  'Personal Growth', 'Work-Life Balance', 'Community', 'Environment', 'Convenience',
  'Quality', 'Value for Money', 'Authenticity', 'Freedom', 'Stability',
  'Adventure', 'Creativity', 'Tradition', 'Innovation', 'Social Connection'
];

export const audienceLifestyleOptions = [
  // Shopping & Consumer Behavior
  'Bargain hunter', 'Brand loyalist', 'Impulse buyer', 'Research-heavy shopper',
  'Online shopping preferred', 'In-store shopping preferred', 'Social commerce user',
  'Subscription service user', 'Second-hand shopper', 'Local business supporter',
  
  // Technology & Media
  'Social media active', 'Streaming service user', 'Gaming enthusiast',
  'Podcast listener', 'YouTube watcher', 'TikTok user', 'Instagram user',
  'Facebook user', 'Tech early adopter', 'Tech laggard',
  
  // Health & Wellness
  'Fitness enthusiast', 'Health-conscious', 'Organic food buyer', 'Supplement user',
  'Gym member', 'Home workout', 'Outdoor activities', 'Wellness focused',
  
  // Lifestyle Choices
  'Eco-friendly', 'Sustainable living', 'Minimalist', 'DIY enthusiast',
  'Foodie', 'Travel lover', 'Homebody', 'Pet owner', 'Parent', 'Student'
];

export const audienceInterests = [
  // Entertainment
  'Movies & TV', 'Music', 'Gaming', 'Books', 'Podcasts', 'YouTube', 'Social Media',
  'Streaming Services', 'Live Events', 'Concerts', 'Theater', 'Comedy',
  
  // Hobbies & Activities
  'Sports', 'Fitness', 'Cooking', 'Baking', 'Gardening', 'DIY Projects',
  'Arts & Crafts', 'Photography', 'Travel', 'Outdoor Activities', 'Hiking',
  'Camping', 'Fishing', 'Hunting', 'Cycling', 'Running',
  
  // Lifestyle & Personal
  'Fashion', 'Beauty', 'Home Decor', 'Interior Design', 'Parenting',
  'Pet Care', 'Health & Wellness', 'Nutrition', 'Mental Health', 'Self-Care',
  
  // Learning & Growth
  'Personal Development', 'Learning New Skills', 'Languages', 'History',
  'Science', 'Technology', 'Current Events', 'Politics', 'Environment'
];

export const audienceMediaConsumption = {
  platforms: [
    'Social Media (Facebook, Instagram, TikTok)', 'YouTube', 'Streaming Services (Netflix, Hulu)',
    'Television', 'Radio', 'Podcasts', 'Online News', 'Magazines', 'Blogs',
    'Email Newsletters', 'Mobile Apps', 'Gaming Platforms'
  ],
  influences: [
    'Friends & Family', 'Social Media Influencers', 'Online Reviews', 'Celebrity Endorsements',
    'User-Generated Content', 'Traditional Advertising', 'Word of Mouth', 'Brand Reputation',
    'Price Comparisons', 'Product Demonstrations', 'Free Trials', 'Recommendations',
    'Social Proof', 'Testimonials', 'Expert Reviews', 'Peer Opinions'
  ]
};

export const audienceDecisionMakingInfluences = [
  'Price', 'Quality', 'Brand Reputation', 'Friends & Family Recommendations',
  'Online Reviews', 'Social Media', 'Convenience', 'Customer Service',
  'Return Policy', 'Warranty', 'Personal Experience', 'Advertising',
  'Promotions & Discounts', 'Product Features', 'Design & Aesthetics',
  'Environmental Impact', 'Social Responsibility', 'Availability'
];

export const audienceGoalOptions = [
  'Find products that solve everyday problems', 'Get good value for money',
  'Discover new and interesting products', 'Make informed purchase decisions',
  'Find products that fit my lifestyle', 'Support brands that align with my values',
  'Find products recommended by others', 'Try products before major purchases',
  'Find products that improve quality of life', 'Discover trending products',
  'Find products that save time and effort', 'Make purchases I won\'t regret'
];

export const audienceShoppingBehaviors = [
  'Impulse buyer', 'Careful researcher', 'Bargain hunter', 'Brand loyalist',
  'Early adopter', 'Wait for reviews', 'Price comparison shopper', 'Convenience shopper',
  'Social shopper', 'Independent shopper', 'Seasonal shopper', 'Need-based shopper'
];

export const audiencePurchaseMotivations = [
  'Solve a problem', 'Improve lifestyle', 'Save money', 'Save time',
  'Feel good about purchase', 'Keep up with trends', 'Treat myself',
  'Gift for others', 'Replace broken item', 'Upgrade current item',
  'Try something new', 'Follow recommendation'
];

export const audienceProductCategories = [
  'Electronics & Gadgets', 'Clothing & Fashion', 'Home & Garden',
  'Health & Beauty', 'Food & Beverages', 'Sports & Outdoors',
  'Books & Media', 'Toys & Games', 'Automotive', 'Pet Supplies',
  'Baby & Kids', 'Office & School Supplies', 'Travel & Luggage',
  'Jewelry & Accessories', 'Arts & Crafts'
];

export const audienceBrandPreferences = [
  'Well-known brands', 'Local/Small businesses', 'Eco-friendly brands',
  'Budget-friendly brands', 'Premium/Luxury brands', 'Innovative brands',
  'Traditional/Established brands', 'Trendy/Fashion brands', 'Value brands',
  'Specialty/Niche brands', 'Direct-to-consumer brands', 'Private label brands'
];

// Audience persona configuration interface
export interface AudiencePersonaConfig {
  shoppingBehaviors: string[];
  purchaseMotivations: string[];
  preferredProductCategories: string[];
  brandPreferences: string[];
  budgetConsiderations: string;
  shoppingFrequency: string;
  informationSources: string[];
  socialInfluence: string;
}

export const audienceBudgetConsiderations = [
  { value: 'very-budget-conscious', label: 'Very budget-conscious' },
  { value: 'budget-conscious', label: 'Budget-conscious' },
  { value: 'moderate-spender', label: 'Moderate spender' },
  { value: 'willing-to-spend', label: 'Willing to spend for quality' },
  { value: 'luxury-spender', label: 'Luxury spender' }
];

export const audienceShoppingFrequency = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'occasionally', label: 'Occasionally' },
  { value: 'rarely', label: 'Rarely' }
];

export const audienceInformationSources = [
  'Search engines', 'Social media', 'Friends and family', 'Online reviews',
  'Brand websites', 'Comparison sites', 'YouTube videos', 'Blogs',
  'Email newsletters', 'In-store visits', 'Sales representatives', 'Advertisements'
];

export const audienceSocialInfluence = [
  { value: 'highly-influenced', label: 'Highly influenced by others' },
  { value: 'moderately-influenced', label: 'Moderately influenced by others' },
  { value: 'somewhat-influenced', label: 'Somewhat influenced by others' },
  { value: 'independent', label: 'Make independent decisions' },
  { value: 'influence-others', label: 'Tend to influence others' }
];