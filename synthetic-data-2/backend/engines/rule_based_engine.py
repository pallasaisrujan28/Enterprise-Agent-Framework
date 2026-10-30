import random
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
from loguru import logger
from pydantic import BaseModel, Field
from datetime import datetime

class DemographicProfile(BaseModel):
    """Demographic profile data structure"""
    age: int = Field(..., ge=18, le=100)
    gender: str = Field(...)
    location: Dict[str, str] = Field(default_factory=dict)
    income: int = Field(..., ge=0)
    education: str = Field(...)
    family_status: str = Field(...)
    household_size: int = Field(default=1, ge=1, le=10)
    
    class Config:
        extra = "allow"

class AgeGroup(Enum):
    TEEN = "13-17"
    YOUNG_ADULT = "18-24"
    ADULT = "25-34"
    MIDDLE_AGED = "35-44"
    MATURE = "45-54"
    SENIOR = "55-64"
    ELDERLY = "65+"

class IncomeLevel(Enum):
    LOW = "Under $30k"
    LOWER_MIDDLE = "$30k-$50k"
    MIDDLE = "$50k-$75k"
    UPPER_MIDDLE = "$75k-$100k"
    HIGH = "$100k-$150k"
    VERY_HIGH = "$150k+"

@dataclass
class DemographicConstraints:
    """Constraints for demographic generation"""
    age_range: Optional[Tuple[int, int]] = None
    gender_distribution: Optional[Dict[str, float]] = None
    location_preferences: Optional[List[str]] = None
    income_constraints: Optional[Tuple[str, str]] = None
    education_requirements: Optional[List[str]] = None
    family_status_options: Optional[List[str]] = None

class RuleBasedEngine:
    """Rule-based demographic and constraint validation engine"""
    
    def __init__(self):
        self.demographic_rules = self._load_demographic_rules()
        self.correlation_matrix = self._build_correlation_matrix()
        self.validation_rules = self._define_validation_rules()
        
        logger.info("Initialized Rule-Based Engine with demographic constraints")
    
    def generate_base_demographics(self, constraints: DemographicConstraints, count: int = 1) -> List[Dict[str, Any]]:
        """Generate base demographic profiles following rules and constraints"""
        demographics = []
        
        for _ in range(count):
            demo = self._generate_single_demographic(constraints)
            if self._validate_demographic(demo):
                demographics.append(demo)
            else:
                # Retry with adjusted parameters
                demo = self._adjust_and_regenerate(demo, constraints)
                demographics.append(demo)
        
        logger.info(f"Generated {len(demographics)} base demographic profiles")
        return demographics
    
    def _generate_single_demographic(self, constraints: DemographicConstraints) -> Dict[str, Any]:
        """Generate a single demographic profile"""
        # Age generation with constraints
        age = self._generate_age(constraints.age_range)
        
        # Gender based on distribution
        gender = self._generate_gender(constraints.gender_distribution)
        
        # Location selection
        location = self._generate_location(constraints.location_preferences)
        
        # Generate name based on gender and location
        name = self._generate_name(gender, location)
        
        # Income based on age and location correlations
        income = self._generate_income(age, location, constraints.income_constraints)
        
        # Education correlated with income and age
        education = self._generate_education(age, income, constraints.education_requirements)
        
        # Family status based on age and income
        family_status = self._generate_family_status(age, income, constraints.family_status_options)
        
        return {
            "name": name,
            "age": age,
            "gender": gender,
            "location": location,
            "income_range": income,
            "education": education,
            "family_status": family_status
        }
    
    def _generate_age(self, age_range: Optional[Tuple[int, int]]) -> int:
        """Generate age with realistic distribution"""
        logger.debug(f"=== AGE GENERATION DEBUG ===")
        logger.debug(f"age_range input: {age_range} (type: {type(age_range)})")
        
        if age_range:
            logger.debug(f"Processing age_range: {age_range}")
            try:
                min_age, max_age = age_range
                logger.debug(f"Successfully unpacked: min_age={min_age}, max_age={max_age}")
                # Use normal distribution centered in the range
                center = (min_age + max_age) / 2
                std_dev = (max_age - min_age) / 6  # 99.7% within range
                age = int(np.random.normal(center, std_dev))
                result = max(min_age, min(max_age, age))
                logger.debug(f"Generated age: {result}")
                return result
            except Exception as e:
                logger.error(f"Error unpacking age_range {age_range}: {e}")
                logger.error(f"age_range type: {type(age_range)}, length: {len(age_range) if hasattr(age_range, '__len__') else 'N/A'}")
                raise
        else:
            logger.debug(f"Using default age distribution")
            # Default age distribution (18-65 with peak at 35)
            age = int(np.random.normal(35, 12))
            result = max(18, min(65, age))
            logger.debug(f"Generated age from default distribution: {result}")
            return result
    
    def _generate_gender(self, distribution: Optional[Dict[str, float]]) -> str:
        """Generate gender based on distribution"""
        if distribution:
            # Convert lowercase gender keys to proper case
            gender_mapping = {
                "male": "Male",
                "female": "Female", 
                "non-binary": "Non-binary",
                "nonbinary": "Non-binary"
            }
            
            genders = []
            weights = []
            for gender_key, weight in distribution.items():
                # Convert to proper case, fallback to original if not found
                proper_gender = gender_mapping.get(gender_key.lower(), gender_key)
                genders.append(proper_gender)
                weights.append(weight)
            
            # Normalize weights to sum to 1.0
            total_weight = sum(weights)
            if total_weight > 0:
                normalized_weights = [w / total_weight for w in weights]
            else:
                # If all weights are 0, use equal distribution
                normalized_weights = [1.0 / len(weights)] * len(weights)
            
            return np.random.choice(genders, p=normalized_weights)
        else:
            # Default distribution
            return np.random.choice(["Male", "Female", "Non-binary"], p=[0.49, 0.49, 0.02])
    
    def _generate_location(self, preferences: Optional[List[str]]) -> Dict[str, str]:
        """Generate location data"""
        # DEBUG: Print location preferences input
        # Debug logging removed for production
        
        # Define geographic data matching frontend
        geographic_data = {
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
        }
        
        if preferences:
            # Check if preferences is a location object from frontend
            if len(preferences) == 1 and isinstance(preferences[0], str):
                try:
                    # Try to parse as JSON if it's a stringified object
                    import json
                    location_obj = json.loads(preferences[0])
                    if isinstance(location_obj, dict) and 'country' in location_obj:
                        country = location_obj.get('country', '')
                        state = location_obj.get('state', '')
                        city = location_obj.get('city', '')
                        
                        # If complete location is provided, use it
                        if country and state and city:
                            return {
                                "city": city,
                                "state": state,
                                "country": country,
                                "full_location": f"{city}, {state}, {country}"
                            }
                        # If only country and state are provided, generate random city in that state
                        elif country and state and country in geographic_data and state in geographic_data[country]:
                            cities = geographic_data[country][state]
                            selected_city = random.choice(cities)
                            return {
                                "city": selected_city,
                                "state": state,
                                "country": country,
                                "full_location": f"{selected_city}, {state}, {country}"
                            }
                        # If only country is provided, generate random location in that country
                        elif country and country in geographic_data:
                            states = list(geographic_data[country].keys())
                            selected_state = random.choice(states)
                            cities = geographic_data[country][selected_state]
                            selected_city = random.choice(cities)
                            return {
                                "city": selected_city,
                                "state": selected_state,
                                "country": country,
                                "full_location": f"{selected_city}, {selected_state}, {country}"
                            }
                except (json.JSONDecodeError, TypeError):
                    # If JSON parsing fails, check if it's a stringified empty JSON
                    if preferences[0].strip() in ['{"country":"","state":"","city":""}', '{}', '']:
                        # Generate random international location for empty/invalid JSON
                        countries = list(geographic_data.keys())
                        country = random.choice(countries)
                        states = list(geographic_data[country].keys())
                        selected_state = random.choice(states)
                        cities = geographic_data[country][selected_state]
                        selected_city = random.choice(cities)
                        
                        return {
                            "city": selected_city,
                            "state": selected_state,
                            "country": country,
                            "full_location": f"{selected_city}, {selected_state}, {country}"
                        }
            
            # Handle traditional string preferences
            location_str = random.choice(preferences)
            
            # Skip if this looks like malformed JSON
            if location_str.startswith('{') and location_str.endswith('}'):
                # Generate random international location for malformed JSON
                countries = list(geographic_data.keys())
                country = random.choice(countries)
                states = list(geographic_data[country].keys())
                selected_state = random.choice(states)
                cities = geographic_data[country][selected_state]
                selected_city = random.choice(cities)
                
                return {
                    "city": selected_city,
                    "state": selected_state,
                    "country": country,
                    "full_location": f"{selected_city}, {selected_state}, {country}"
                }
            
            # Check if location_str is a country name
            if location_str in geographic_data:
                country = location_str
                states = list(geographic_data[country].keys())
                selected_state = random.choice(states)
                cities = geographic_data[country][selected_state]
                selected_city = random.choice(cities)
                
                return {
                    "city": selected_city,
                    "state": selected_state,
                    "country": country,
                    "full_location": f"{selected_city}, {selected_state}, {country}"
                }
            
            # Check if location_str is a state name
            for country_name, states in geographic_data.items():
                if location_str in states:
                    country = country_name
                    selected_state = location_str
                    cities = geographic_data[country][selected_state]
                    selected_city = random.choice(cities)
                    
                    return {
                        "city": selected_city,
                        "state": selected_state,
                        "country": country,
                        "full_location": f"{selected_city}, {selected_state}, {country}"
                    }
            
            # Check if location_str is a city name
            for country_name, states in geographic_data.items():
                for state_name, cities in states.items():
                    if location_str in cities:
                        return {
                            "city": location_str,
                            "state": state_name,
                            "country": country_name,
                            "full_location": f"{location_str}, {state_name}, {country_name}"
                        }
            
            # Handle "City, State" format
            parts = location_str.split(", ")
            if len(parts) >= 2:
                # Check if this matches any known locations
                for country_name, states in geographic_data.items():
                    for state_name, cities in states.items():
                        if parts[0] in cities and parts[1] == state_name:
                            return {
                                "city": parts[0],
                                "state": state_name,
                                "country": country_name,
                                "full_location": f"{parts[0]}, {state_name}, {country_name}"
                            }
            
            # Fallback: treat as unknown location and generate random international location
            countries = list(geographic_data.keys())
            country = random.choice(countries)
            states = list(geographic_data[country].keys())
            selected_state = random.choice(states)
            cities = geographic_data[country][selected_state]
            selected_city = random.choice(cities)
            
            return {
                "city": selected_city,
                "state": selected_state,
                "country": country,
                "full_location": f"{selected_city}, {selected_state}, {country}"
            }
        else:
            # Default to random international location if no preferences
            countries = list(geographic_data.keys())
            country = random.choice(countries)
            states = list(geographic_data[country].keys())
            selected_state = random.choice(states)
            cities = geographic_data[country][selected_state]
            selected_city = random.choice(cities)
            
            return {
                "city": selected_city,
                "state": selected_state,
                "country": country,
                "full_location": f"{selected_city}, {selected_state}, {country}"
            }
    
    def _generate_name(self, gender: str, location: Dict[str, str]) -> str:
        """Generate realistic names based on gender and location"""
        # Common first names by gender
        male_names = [
            "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Christopher",
            "Charles", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua",
            "Kenneth", "Kevin", "Brian", "George", "Timothy", "Ronald", "Jason", "Edward", "Jeffrey", "Ryan",
            "Jacob", "Gary", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott", "Brandon"
        ]
        
        female_names = [
            "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen",
            "Nancy", "Lisa", "Betty", "Helen", "Sandra", "Donna", "Carol", "Ruth", "Sharon", "Michelle",
            "Laura", "Sarah", "Kimberly", "Deborah", "Dorothy", "Lisa", "Nancy", "Karen", "Betty", "Helen",
            "Sandra", "Donna", "Carol", "Ruth", "Sharon", "Michelle", "Laura", "Emily", "Ashley", "Emma"
        ]
        
        # Common last names
        last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
            "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
            "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
            "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"
        ]
        
        # Select first name based on gender
        if gender.lower() in ['male', 'm', 'man']:
            first_name = random.choice(male_names)
        elif gender.lower() in ['female', 'f', 'woman']:
            first_name = random.choice(female_names)
        else:
            # For non-binary or other genders, choose from both lists
            first_name = random.choice(male_names + female_names)
        
        # Select last name
        last_name = random.choice(last_names)
        
        # Adjust names based on location if needed
        country = location.get('country', '').lower()
        if 'mexico' in country or 'spain' in country:
            # Add some Spanish names to the mix
            spanish_first_names = ["Carlos", "Maria", "Jose", "Ana", "Luis", "Carmen", "Francisco", "Isabel"]
            spanish_last_names = ["Garcia", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Perez", "Sanchez"]
            if random.random() < 0.3:  # 30% chance for Spanish names
                if gender.lower() in ['female', 'f', 'woman']:
                    first_name = random.choice(["Maria", "Ana", "Carmen", "Isabel", "Sofia", "Lucia"])
                else:
                    first_name = random.choice(["Carlos", "Jose", "Luis", "Francisco", "Miguel", "Antonio"])
                last_name = random.choice(spanish_last_names)
        
        return f"{first_name} {last_name}"
    
    def _generate_income(self, age: int, location: Dict[str, str], constraints: Optional[Tuple[str, str]]) -> str:
        """Generate income based on age and location correlations"""
        logger.debug(f"=== INCOME GENERATION DEBUG ===")
        logger.debug(f"constraints input: {constraints} (type: {type(constraints)})")
        
        # Base income calculation
        if age < 25:
            income_options = [IncomeLevel.LOW, IncomeLevel.LOWER_MIDDLE]
            weights = [0.7, 0.3]
        elif age < 35:
            income_options = [IncomeLevel.LOW, IncomeLevel.LOWER_MIDDLE, IncomeLevel.MIDDLE, IncomeLevel.UPPER_MIDDLE]
            weights = [0.2, 0.3, 0.3, 0.2]
        elif age < 45:
            income_options = [IncomeLevel.LOWER_MIDDLE, IncomeLevel.MIDDLE, IncomeLevel.UPPER_MIDDLE, IncomeLevel.HIGH]
            weights = [0.15, 0.25, 0.35, 0.25]
        elif age < 55:
            income_options = [IncomeLevel.MIDDLE, IncomeLevel.UPPER_MIDDLE, IncomeLevel.HIGH, IncomeLevel.VERY_HIGH]
            weights = [0.2, 0.3, 0.3, 0.2]
        else:
            income_options = [IncomeLevel.LOWER_MIDDLE, IncomeLevel.MIDDLE, IncomeLevel.UPPER_MIDDLE, IncomeLevel.HIGH]
            weights = [0.25, 0.35, 0.25, 0.15]
        
        # Adjust for high-cost areas
        high_cost_cities = ["New York", "San Francisco", "Los Angeles", "San Jose", "Seattle"]
        if any(city in location.get("city", "") for city in high_cost_cities):
            # Shift income distribution higher
            if len(income_options) > 2:
                # Redistribute weights to maintain sum of 1
                new_weights = weights[1:] + [weights[0]]  # Move first weight to end
                weights = [w / sum(new_weights) for w in new_weights]  # Normalize
                income_options = income_options[1:] + [IncomeLevel.VERY_HIGH]
        
        selected_income = np.random.choice(income_options, p=weights)
        
        # Apply constraints if provided
        if constraints:
            logger.debug(f"Processing income constraints: {constraints}")
            try:
                min_income, max_income = constraints
                logger.debug(f"Successfully unpacked: min_income={min_income}, max_income={max_income}")
                # Validate against constraints (simplified)
                result = selected_income.value
                logger.debug(f"Generated income with constraints: {result}")
                return result
            except Exception as e:
                logger.error(f"Error unpacking income constraints {constraints}: {e}")
                logger.error(f"constraints type: {type(constraints)}, length: {len(constraints) if hasattr(constraints, '__len__') else 'N/A'}")
                raise
        
        result = selected_income.value
        logger.debug(f"Generated income without constraints: {result}")
        return result
    
    def _generate_education(self, age: int, income: str, requirements: Optional[List[str]]) -> str:
        """Generate education level correlated with age and income"""
        education_levels = [
            "High School",
            "Some College",
            "Associate Degree",
            "Bachelor's Degree",
            "Master's Degree",
            "Doctoral Degree"
        ]
        
        if requirements:
            return random.choice(requirements)
        
        # Correlate with income
        if "$150k+" in income or "$100k-$150k" in income:
            weights = [0.05, 0.1, 0.1, 0.35, 0.3, 0.1]
        elif "$75k-$100k" in income:
            weights = [0.1, 0.15, 0.15, 0.4, 0.15, 0.05]
        elif "$50k-$75k" in income:
            weights = [0.15, 0.2, 0.25, 0.3, 0.08, 0.02]
        else:
            weights = [0.3, 0.25, 0.2, 0.2, 0.04, 0.01]
        
        return np.random.choice(education_levels, p=weights)
    

    
    def _generate_family_status(self, age: int, income: str, options: Optional[List[str]]) -> str:
        """Generate family status based on age and income"""
        if options:
            return random.choice(options)
        
        if age < 25:
            statuses = ["Single", "In Relationship", "Married"]
            weights = [0.6, 0.3, 0.1]
        elif age < 35:
            statuses = ["Single", "In Relationship", "Married", "Married with Children"]
            weights = [0.3, 0.2, 0.3, 0.2]
        elif age < 45:
            statuses = ["Single", "Married", "Married with Children", "Divorced"]
            weights = [0.15, 0.25, 0.5, 0.1]
        else:
            statuses = ["Married", "Married with Children", "Divorced", "Widowed"]
            weights = [0.3, 0.4, 0.25, 0.05]
        
        return np.random.choice(statuses, p=weights)
    
    def _validate_demographic(self, demographic: Dict[str, Any]) -> bool:
        """Validate demographic profile against rules"""
        age = demographic.get("age", 0)
        income = demographic.get("income_range", "")
        education = demographic.get("education", "")
        
        # Rule: PhD holders should be at least 25
        if "Doctoral" in education and age < 25:
            return False
        
        # Rule: High income should correlate with higher education
        if "$150k+" in income and education == "High School":
            return False
        
        # Rule: Very young people shouldn't have very high incomes
        if age < 22 and ("$100k" in income or "$150k" in income):
            return False
        
        return True
    
    def _adjust_and_regenerate(self, demographic: Dict[str, Any], constraints: DemographicConstraints) -> Dict[str, Any]:
        """Adjust invalid demographic to make it valid"""
        age = demographic.get("age", 0)
        
        # Adjust education if age is too young for advanced degrees
        if age < 25 and "Doctoral" in demographic.get("education", ""):
            demographic["education"] = "Bachelor's Degree"
        
        # Adjust income if inconsistent with education
        if demographic.get("education") == "High School" and "$150k" in demographic.get("income_range", ""):
            demographic["income_range"] = "$30k-$50k"
        
        return demographic
    
    def _load_demographic_rules(self) -> Dict[str, Any]:
        """Load demographic correlation rules"""
        return {
            "age_income_correlation": 0.65,
            "education_income_correlation": 0.78,
            "location_income_adjustment": {
                "high_cost": 1.3,
                "medium_cost": 1.0,
                "low_cost": 0.8
            }
        }
    
    def _build_correlation_matrix(self) -> np.ndarray:
        """Build correlation matrix for demographic attributes"""
        # Simplified correlation matrix (age, income, education)
        return np.array([
            [1.0, 0.65, 0.45],  # age correlations
            [0.65, 1.0, 0.78],  # income correlations
            [0.45, 0.78, 1.0]   # education correlations
        ])
    
    def _define_validation_rules(self) -> List[Dict[str, Any]]:
        """Define validation rules for demographic consistency"""
        return [
            {
                "name": "age_education_consistency",
                "condition": lambda d: not ("Doctoral" in d.get("education", "") and d.get("age", 0) < 25),
                "message": "Doctoral degree holders must be at least 25 years old"
            },
            {
                "name": "income_education_consistency",
                "condition": lambda d: not ("$150k+" in d.get("income_range", "") and d.get("education", "") == "High School"),
                "message": "High income should correlate with higher education"
            },
            {
                "name": "age_income_consistency",
                "condition": lambda d: not (d.get("age", 0) < 22 and ("$100k" in d.get("income_range", "") or "$150k" in d.get("income_range", ""))),
                "message": "Very young people typically don't have very high incomes"
            }
        ]
    
    def validate_batch_demographics(self, demographics: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate a batch of demographics and return valid ones with error messages"""
        valid_demographics = []
        error_messages = []
        
        for i, demo in enumerate(demographics):
            if self._validate_demographic(demo):
                valid_demographics.append(demo)
            else:
                # Find which rule failed
                for rule in self.validation_rules:
                    if not rule["condition"](demo):
                        error_messages.append(f"Demographic {i}: {rule['message']}")
                        break
        
        logger.info(f"Validated {len(valid_demographics)}/{len(demographics)} demographics")
        return valid_demographics, error_messages
    
    def generate_single_demographic(self, constraints: Optional[DemographicConstraints] = None) -> Dict[str, Any]:
        """Generate a single demographic profile (public method)"""
        if constraints is None:
            constraints = DemographicConstraints()
        return self._generate_single_demographic(constraints)
    
    def generate_batch_demographics(self, sample_size: int, constraints: Optional[DemographicConstraints] = None) -> List[Dict[str, Any]]:
        """Generate a batch of demographic profiles"""
        if constraints is None:
            constraints = DemographicConstraints()
        return self.generate_base_demographics(constraints, sample_size)