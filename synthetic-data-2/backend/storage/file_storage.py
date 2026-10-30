"""
File-based storage manager for personas
"""
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class StorageConfig:
    """Configuration for storage manager"""
    base_path: str = "data/personas"
    auto_create_dirs: bool = True
    use_compression: bool = False


@dataclass
class PersonaRecord:
    """Record for storing a persona"""
    persona_id: str
    demographics: Dict[str, Any]
    psychographics: Dict[str, Any]
    behavioral_patterns: Dict[str, Any]
    narrative: Optional[str] = None
    generation_method: Optional[str] = None
    confidence_score: Optional[float] = None
    cluster_id: Optional[int] = None
    created_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FileStorageManager:
    """Manages file-based storage of personas"""
    
    def __init__(self, base_path: str = "data/personas"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_persona(self, persona: PersonaRecord, folder_name: str = "default") -> str:
        """Save a persona to file storage"""
        folder = self.base_path / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        
        file_path = folder / f"{persona.persona_id}.json"
        
        with open(file_path, 'w') as f:
            json.dump(asdict(persona), f, indent=2)
        
        return str(file_path)
    
    def save_batch(self, personas: List[PersonaRecord], folder_name: str = "default") -> List[str]:
        """Save multiple personas"""
        return [self.save_persona(p, folder_name) for p in personas]
    
    def load_persona(self, persona_id: str, folder_name: str = "default") -> Optional[PersonaRecord]:
        """Load a persona from storage"""
        file_path = self.base_path / folder_name / f"{persona_id}.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return PersonaRecord(**data)
    
    def list_personas(self, folder_name: str = "default") -> List[str]:
        """List all persona IDs in a folder"""
        folder = self.base_path / folder_name
        
        if not folder.exists():
            return []
        
        return [f.stem for f in folder.glob("*.json")]
    
    def delete_persona(self, persona_id: str, folder_name: str = "default") -> bool:
        """Delete a persona from storage"""
        file_path = self.base_path / folder_name / f"{persona_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            return True
        
        return False
