"""
Data adapter for confidence scoring and persona data
"""
from typing import Dict, Any, List, Optional
import json


class ConfidenceDataAdapter:
    """Adapter for managing confidence score data storage and retrieval"""
    
    def __init__(self, storage_manager=None):
        """
        Initialize the data adapter
        
        Args:
            storage_manager: Optional FileStorageManager instance
        """
        self.storage_manager = storage_manager
    
    def store_confidence_profile(self, persona_id: str, confidence_data: Dict[str, Any]) -> bool:
        """
        Store confidence profile for a persona
        
        Args:
            persona_id: Unique identifier for the persona
            confidence_data: Confidence scoring data
            
        Returns:
            bool: Success status
        """
        try:
            if self.storage_manager:
                # Store in file system if storage manager is available
                filename = f"confidence_{persona_id}.json"
                self.storage_manager.save_json(filename, confidence_data)
            return True
        except Exception as e:
            print(f"Error storing confidence profile: {e}")
            return False
    
    def get_confidence_profile(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve confidence profile for a persona
        
        Args:
            persona_id: Unique identifier for the persona
            
        Returns:
            Confidence data or None if not found
        """
        try:
            if self.storage_manager:
                filename = f"confidence_{persona_id}.json"
                return self.storage_manager.load_json(filename)
            return None
        except Exception as e:
            print(f"Error retrieving confidence profile: {e}")
            return None
    
    def store_batch_confidence(self, confidence_batch: List[Dict[str, Any]]) -> bool:
        """
        Store confidence data for multiple personas
        
        Args:
            confidence_batch: List of confidence data dictionaries
            
        Returns:
            bool: Success status
        """
        try:
            for item in confidence_batch:
                persona_id = item.get('persona_id')
                if persona_id:
                    self.store_confidence_profile(persona_id, item)
            return True
        except Exception as e:
            print(f"Error storing batch confidence: {e}")
            return False
