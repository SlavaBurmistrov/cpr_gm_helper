from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class BaseEntity:
    id: str
    name: str
    description: str
    notes: List[str] = field(default_factory=list)

@dataclass
class NPC(BaseEntity):
    role: str = "Civilian" # e.g., Fixer, Solo, Netrunner
    location: str = "Unknown"
    relationships: Dict[str, str] = field(default_factory=dict) # e.g., {"player_id": "Friendly"}
    status: str = "Alive"

@dataclass
class Corporation(BaseEntity):
    tier: str = "Minor"
    assets: List[str] = field(default_factory=list)
    enemies: List[str] = field(default_factory=list) # List of other corp IDs

@dataclass
class Location(BaseEntity):
    district: str
    security_level: str = "Medium"
    points_of_interest: List[str] = field(default_factory=list)