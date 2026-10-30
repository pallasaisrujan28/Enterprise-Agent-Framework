import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import json
from loguru import logger
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
import random

@dataclass
class DiversityConfig:
    """Configuration for diversity generation"""
    latent_dim: int = 64
    hidden_dim: int = 128
    num_epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.0002
    diversity_weight: float = 0.3
    edge_case_probability: float = 0.1

class PersonaVAE(nn.Module):
    """Variational Autoencoder for persona attribute generation"""
    
    def __init__(self, input_dim: int, latent_dim: int = 64, hidden_dim: int = 128):
        super(PersonaVAE, self).__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # Latent space
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
            nn.Sigmoid()
        )
    
    def encode(self, x):
        h = self.encoder(x)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar
    
    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def decode(self, z):
        return self.decoder(z)
    
    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon_x = self.decode(z)
        return recon_x, mu, logvar

class PersonaGAN(nn.Module):
    """Generative Adversarial Network for diverse persona generation"""
    
    def __init__(self, noise_dim: int = 100, output_dim: int = 50, hidden_dim: int = 128):
        super(PersonaGAN, self).__init__()
        self.noise_dim = noise_dim
        
        # Generator
        self.generator = nn.Sequential(
            nn.Linear(noise_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
            nn.Tanh()
        )
        
        # Discriminator
        self.discriminator = nn.Sequential(
            nn.Linear(output_dim, hidden_dim),
            nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid()
        )
    
    def generate(self, batch_size: int):
        noise = torch.randn(batch_size, self.noise_dim)
        return self.generator(noise)
    
    def discriminate(self, x):
        return self.discriminator(x)

class DiversityEngine:
    """Engine for generating diverse persona attributes using GANs and VAEs"""
    
    def __init__(self, config: DiversityConfig = None):
        self.config = config or DiversityConfig()
        self.vae = None
        self.gan = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.is_trained = False
        
        # Psychographic and behavioral attribute templates
        self.psychographic_templates = self._load_psychographic_templates()
        self.behavioral_patterns = self._load_behavioral_patterns()
        self.edge_case_scenarios = self._load_edge_cases()
        
        logger.info("Initialized Diversity Engine with GAN/VAE architecture")
    
    def generate_diverse_attributes(self, base_demographics: List[Dict[str, Any]], 
                                  diversity_level: float = 0.5) -> List[Dict[str, Any]]:
        """Generate diverse psychographic and behavioral attributes"""
        enhanced_personas = []
        
        for demo in base_demographics:
            # Generate psychographic profile
            psychographic = self._generate_psychographic_profile(demo, diversity_level)
            
            # Generate behavioral patterns
            behavioral = self._generate_behavioral_patterns(demo, diversity_level)
            
            # Add edge cases if probability triggers
            if random.random() < self.config.edge_case_probability:
                edge_case = self._generate_edge_case_attributes(demo)
                psychographic.update(edge_case)
            
            # Combine all attributes
            enhanced_persona = {
                **demo,
                "psychographic": psychographic,
                "behavioral": behavioral,
                "diversity_score": self._calculate_diversity_score(psychographic, behavioral)
            }
            
            enhanced_personas.append(enhanced_persona)
        
        logger.info(f"Generated diverse attributes for {len(enhanced_personas)} personas")
        return enhanced_personas
    
    def generate_psychographic_profile(self, demographic: Dict[str, Any], diversity_level: float = 0.5) -> Dict[str, Any]:
        """Public method to generate psychographic profile"""
        return self._generate_psychographic_profile(demographic, diversity_level)
    
    def _generate_psychographic_profile(self, demographic: Dict[str, Any], diversity_level: float) -> Dict[str, Any]:
        """Generate psychographic attributes using demographic correlations and diversity injection"""
        age = demographic.get("age", 30)
        income = demographic.get("income_range", "")
        education = demographic.get("education", "")
        
        # Base personality traits (Big Five)
        personality = self._generate_big_five_traits(age, education, diversity_level)
        
        # Values and motivations
        values = self._generate_values_profile(age, income, diversity_level)
        
        # Lifestyle preferences
        lifestyle = self._generate_lifestyle_preferences(demographic, diversity_level)
        
        # Technology adoption
        tech_profile = self._generate_technology_profile(age, education, diversity_level)
        
        return {
            "personality": personality,
            "values": values,
            "lifestyle": lifestyle,
            "technology": tech_profile,
            "communication_style": self._generate_communication_style(personality, education)
        }
    
    def _generate_big_five_traits(self, age: int, education: str, diversity_level: float) -> Dict[str, float]:
        """Generate Big Five personality traits with age/education correlations"""
        # Base correlations
        base_traits = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5
        }
        
        # Age adjustments
        if age > 40:
            base_traits["conscientiousness"] += 0.1
            base_traits["neuroticism"] -= 0.1
        if age < 25:
            base_traits["openness"] += 0.1
            base_traits["neuroticism"] += 0.05
        
        # Education adjustments
        if "Bachelor" in education or "Master" in education or "Doctoral" in education:
            base_traits["openness"] += 0.15
            base_traits["conscientiousness"] += 0.1
        
        # Apply diversity injection
        for trait in base_traits:
            noise = np.random.normal(0, diversity_level * 0.3)
            base_traits[trait] = max(0.0, min(1.0, base_traits[trait] + noise))
        
        return base_traits
    
    def _generate_values_profile(self, age: int, income: str, diversity_level: float) -> Dict[str, float]:
        """Generate values and motivations profile"""
        values = {
            "achievement": 0.5,
            "security": 0.5,
            "hedonism": 0.5,
            "tradition": 0.5,
            "benevolence": 0.5,
            "universalism": 0.5,
            "self_direction": 0.5,
            "stimulation": 0.5
        }
        
        # Age-based adjustments
        if age > 45:
            values["security"] += 0.2
            values["tradition"] += 0.15
            values["stimulation"] -= 0.1
        elif age < 30:
            values["stimulation"] += 0.2
            values["hedonism"] += 0.15
            values["tradition"] -= 0.1
        
        # Income-based adjustments
        if "$100k" in income or "$150k" in income:
            values["achievement"] += 0.2
            values["self_direction"] += 0.1
        
        # Apply diversity
        for value in values:
            noise = np.random.normal(0, diversity_level * 0.25)
            values[value] = max(0.0, min(1.0, values[value] + noise))
        
        return values
    
    def _generate_lifestyle_preferences(self, demographic: Dict[str, Any], diversity_level: float) -> Dict[str, Any]:
        """Generate lifestyle and preference attributes"""
        age = demographic.get("age", 30)
        location = demographic.get("location", {}).get("city", "")
        
        # Base lifestyle preferences
        lifestyle = {
            "social_activity_level": np.random.normal(0.5, diversity_level * 0.3),
            "outdoor_preference": np.random.normal(0.5, diversity_level * 0.3),
            "cultural_engagement": np.random.normal(0.5, diversity_level * 0.3),
            "fitness_orientation": np.random.normal(0.5, diversity_level * 0.3),
            "environmental_consciousness": np.random.normal(0.5, diversity_level * 0.3)
        }
        
        # Urban vs rural adjustments
        urban_cities = ["New York", "Los Angeles", "Chicago", "San Francisco"]
        if any(city in location for city in urban_cities):
            lifestyle["cultural_engagement"] += 0.2
            lifestyle["environmental_consciousness"] += 0.1
        
        # Age adjustments
        if age < 30:
            lifestyle["social_activity_level"] += 0.15
        elif age > 50:
            lifestyle["cultural_engagement"] += 0.1
            lifestyle["outdoor_preference"] -= 0.05
        
        # Normalize values
        for key in lifestyle:
            lifestyle[key] = max(0.0, min(1.0, lifestyle[key]))
        
        # Add categorical preferences
        lifestyle.update({
            "preferred_activities": self._select_preferred_activities(lifestyle, age),
            "shopping_style": self._determine_shopping_style(demographic, lifestyle),
            "media_consumption": self._generate_media_preferences(age, lifestyle)
        })
        
        return lifestyle
    
    def _generate_technology_profile(self, age: int, education: str, diversity_level: float) -> Dict[str, Any]:
        """Generate technology adoption and usage patterns"""
        # Base tech adoption based on age
        if age < 25:
            base_adoption = 0.9
        elif age < 35:
            base_adoption = 0.8
        elif age < 50:
            base_adoption = 0.6
        else:
            base_adoption = 0.4
        
        # Education boost
        if "Bachelor" in education or "Master" in education or "Doctoral" in education:
            base_adoption += 0.1
        
        # Apply diversity
        adoption_score = max(0.0, min(1.0, base_adoption + np.random.normal(0, diversity_level * 0.2)))
        
        return {
            "adoption_score": adoption_score,
            "preferred_platforms": self._select_tech_platforms(age, adoption_score),
            "device_preferences": self._determine_device_preferences(age, adoption_score),
            "privacy_consciousness": np.random.normal(0.5, diversity_level * 0.3),
            "early_adopter_tendency": max(0.0, min(1.0, adoption_score + np.random.normal(0, 0.2)))
        }
    
    def _generate_behavioral_patterns(self, demographic: Dict[str, Any], diversity_level: float) -> Dict[str, Any]:
        """Generate behavioral patterns and habits"""
        return {
            "decision_making_style": self._generate_decision_style(demographic, diversity_level),
            "communication_patterns": self._generate_communication_patterns(demographic, diversity_level),
            "spending_behavior": self._generate_spending_behavior(demographic, diversity_level),
            "time_management": self._generate_time_management_style(demographic, diversity_level),
            "social_behavior": self._generate_social_behavior(demographic, diversity_level)
        }
    
    def _generate_edge_case_attributes(self, demographic: Dict[str, Any]) -> Dict[str, Any]:
        """Generate edge case or unusual attribute combinations"""
        edge_cases = [
            {"unusual_hobby": "Competitive Origami", "expertise_level": "Expert"},
            {"unique_skill": "Speed Reading", "proficiency": "Advanced"},
            {"rare_interest": "Mycology", "involvement_level": "Hobbyist"},
            {"uncommon_trait": "Synesthesia", "type": "Chromesthesia"},
            {"distinctive_habit": "Lucid Dreaming Practice", "frequency": "Regular"},
            {"specialized_knowledge": "Ancient Languages", "languages": ["Latin", "Sanskrit"]},
            {"unique_perspective": "Minimalist Philosophy", "adoption_level": "Strict"}
        ]
        
        return random.choice(edge_cases)
    
    def _calculate_diversity_score(self, psychographic: Dict[str, Any], behavioral: Dict[str, Any]) -> float:
        """Calculate overall diversity score for the persona"""
        # Extract numerical values
        psych_values = []
        if "personality" in psychographic:
            psych_values.extend(psychographic["personality"].values())
        if "values" in psychographic:
            psych_values.extend(psychographic["values"].values())
        
        # Calculate variance as diversity measure
        if psych_values:
            diversity = float(np.var(psych_values))
            return min(1.0, diversity * 2)  # Normalize to 0-1 range
        
        return 0.5  # Default diversity score
    
    def _load_psychographic_templates(self) -> Dict[str, List[str]]:
        """Load psychographic attribute templates"""
        return {
            "personality_descriptors": [
                "analytical", "creative", "methodical", "spontaneous", "detail-oriented",
                "big-picture", "collaborative", "independent", "optimistic", "realistic"
            ],
            "value_systems": [
                "achievement-oriented", "family-focused", "career-driven", "community-minded",
                "environmentally-conscious", "tradition-respecting", "innovation-seeking"
            ]
        }
    
    def _load_behavioral_patterns(self) -> Dict[str, List[str]]:
        """Load behavioral pattern templates"""
        return {
            "decision_styles": ["analytical", "intuitive", "collaborative", "directive"],
            "communication_styles": ["direct", "diplomatic", "expressive", "reserved"],
            "work_styles": ["structured", "flexible", "deadline-driven", "process-oriented"]
        }
    
    def _load_edge_cases(self) -> List[Dict[str, Any]]:
        """Load edge case scenarios for unusual personas"""
        return [
            {"type": "skill_mismatch", "description": "High education, low income by choice"},
            {"type": "age_reversal", "description": "Young person with traditional values"},
            {"type": "tech_paradox", "description": "Tech worker who avoids social media"},
            {"type": "lifestyle_contrast", "description": "Urban dweller who loves rural activities"}
        ]
    
    # Helper methods for specific attribute generation
    def _select_preferred_activities(self, lifestyle: Dict[str, float], age: int) -> List[str]:
        activities = ["reading", "hiking", "cooking", "gaming", "traveling", "gardening", "photography"]
        # Ensure we don't select more activities than available
        num_activities = min(random.randint(2, 4), len(activities))
        selected = random.sample(activities, k=num_activities)
        return list(dict.fromkeys(selected))  # Preserve order while removing duplicates
    
    def _determine_shopping_style(self, demographic: Dict[str, Any], lifestyle: Dict[str, float]) -> str:
        styles = ["research-heavy", "impulse", "brand-loyal", "price-conscious", "experience-focused"]
        return random.choice(styles)
    
    def _generate_media_preferences(self, age: int, lifestyle: Dict[str, float]) -> Dict[str, str]:
        return {
            "news_source": random.choice(["social_media", "traditional_media", "podcasts", "newsletters"]),
            "entertainment": random.choice(["streaming", "traditional_tv", "books", "podcasts", "gaming"])
        }
    
    def _select_tech_platforms(self, age: int, adoption_score: float) -> List[str]:
        platforms = ["Facebook", "Instagram", "Twitter", "LinkedIn", "TikTok", "YouTube"]
        num_platforms = int(adoption_score * 4) + 1
        return random.sample(platforms, k=min(num_platforms, len(platforms)))
    
    def _determine_device_preferences(self, age: int, adoption_score: float) -> Dict[str, str]:
        return {
            "primary_device": random.choice(["smartphone", "laptop", "desktop", "tablet"]),
            "os_preference": random.choice(["iOS", "Android", "Windows", "macOS", "Linux"])
        }
    
    def _generate_decision_style(self, demographic: Dict[str, Any], diversity_level: float) -> str:
        styles = ["analytical", "intuitive", "collaborative", "directive"]
        return random.choice(styles)
    
    def _generate_communication_patterns(self, demographic: Dict[str, Any], diversity_level: float) -> Dict[str, str]:
        return {
            "style": random.choice(["direct", "diplomatic", "expressive", "reserved"]),
            "preferred_channel": random.choice(["email", "phone", "text", "in_person", "video_call"])
        }
    
    def _generate_spending_behavior(self, demographic: Dict[str, Any], diversity_level: float) -> Dict[str, Any]:
        income = demographic.get("income_range", "")
        return {
            "style": random.choice(["conservative", "moderate", "liberal", "impulsive"]),
            "priority_categories": random.sample(["housing", "food", "entertainment", "travel", "technology", "education"], k=3)
        }
    
    def _generate_time_management_style(self, demographic: Dict[str, Any], diversity_level: float) -> str:
        styles = ["structured", "flexible", "deadline_driven", "process_oriented"]
        return random.choice(styles)
    
    def _generate_social_behavior(self, demographic: Dict[str, Any], diversity_level: float) -> Dict[str, Any]:
        return {
            "networking_style": random.choice(["active", "passive", "selective", "minimal"]),
            "group_dynamics": random.choice(["leader", "collaborator", "supporter", "observer"])
        }
    
    def _generate_communication_style(self, personality: Dict[str, float], education: str) -> str:
        extraversion = personality.get("extraversion", 0.5)
        if extraversion > 0.7:
            return "expressive"
        elif extraversion < 0.3:
            return "reserved"
        else:
            return "balanced"
    
    def train_models(self, training_data: List[Dict[str, Any]]):
        """Train VAE and GAN models on existing persona data"""
        if not training_data:
            logger.warning("No training data provided for diversity models")
            return
        
        # Prepare training data
        encoded_data = self._encode_training_data(training_data)
        
        # Initialize models
        input_dim = encoded_data.shape[1]
        self.vae = PersonaVAE(input_dim, self.config.latent_dim)
        self.gan = PersonaGAN(noise_dim=100, output_dim=input_dim)
        
        # Train VAE
        self._train_vae(encoded_data)
        
        # Train GAN
        self._train_gan(encoded_data)
        
        self.is_trained = True
        logger.info("Diversity models trained successfully")
    
    def _encode_training_data(self, data: List[Dict[str, Any]]) -> np.ndarray:
        """Encode persona data for model training"""
        # Simplified encoding - in practice, this would be more sophisticated
        encoded_features = []
        
        for persona in data:
            features = []
            # Extract numerical features
            features.append(persona.get("age", 30) / 100.0)  # Normalize age
            
            # Encode categorical features
            gender = persona.get("gender", "Unknown")
            features.extend([1 if gender == g else 0 for g in ["Male", "Female", "Non-binary"]])
            
            encoded_features.append(features)
        
        return np.array(encoded_features)
    
    def _train_vae(self, data: np.ndarray):
        """Train the VAE model"""
        # Simplified training loop
        optimizer = optim.Adam(self.vae.parameters(), lr=self.config.learning_rate)
        
        for epoch in range(min(10, self.config.num_epochs)):  # Reduced for demo
            data_tensor = torch.FloatTensor(data)
            recon_batch, mu, logvar = self.vae(data_tensor)
            
            # VAE loss
            recon_loss = nn.functional.mse_loss(recon_batch, data_tensor, reduction='sum')
            kld_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
            loss = recon_loss + kld_loss
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        
        logger.info("VAE training completed")
    
    def _train_gan(self, data: np.ndarray):
        """Train the GAN model"""
        # Simplified GAN training
        g_optimizer = optim.Adam(self.gan.generator.parameters(), lr=self.config.learning_rate)
        d_optimizer = optim.Adam(self.gan.discriminator.parameters(), lr=self.config.learning_rate)
        
        for epoch in range(min(10, self.config.num_epochs)):  # Reduced for demo
            # Train discriminator
            real_data = torch.FloatTensor(data)
            fake_data = self.gan.generate(len(data))
            
            d_real = self.gan.discriminate(real_data)
            d_fake = self.gan.discriminate(fake_data.detach())
            
            d_loss = -torch.mean(torch.log(d_real) + torch.log(1 - d_fake))
            
            d_optimizer.zero_grad()
            d_loss.backward()
            d_optimizer.step()
            
            # Train generator
            fake_data = self.gan.generate(len(data))
            d_fake = self.gan.discriminate(fake_data)
            g_loss = -torch.mean(torch.log(d_fake))
            
            g_optimizer.zero_grad()
            g_loss.backward()
            g_optimizer.step()
        
        logger.info("GAN training completed")