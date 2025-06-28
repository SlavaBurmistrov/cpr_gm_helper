import json
from data_models import NPC, Corporation, Location
from typing import Dict, Union

class WorldStateManager:
    """Manages the loading, modification, and saving of the campaign world state."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.npcs: Dict[str, NPC] = {}
        self.corporations: Dict[str, Corporation] = {}
        self.locations: Dict[str, Location] = {}
        self.load_world()

    def load_world(self):
        """Loads the world state from the JSON file."""
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                self.npcs = {k: NPC(**v) for k, v in data.get('npcs', {}).items()}
                self.corporations = {k: Corporation(**v) for k, v in data.get('corporations', {}).items()}
                self.locations = {k: Location(**v) for k, v in data.get('locations', {}).items()}
        except FileNotFoundError:
            print("World state file not found. Starting with a fresh world.")
            self.save_world()

    def save_world(self):
        """Saves the current world state to the JSON file."""
        world_data = {
            'npcs': {k: v.__dict__ for k, v in self.npcs.items()},
            'corporations': {k: v.__dict__ for k, v in self.corporations.items()},
            'locations': {k: v.__dict__ for k, v in self.locations.items()},
        }
        with open(self.filepath, 'w') as f:
            json.dump(world_data, f, indent=4)

    def get_entity(self, entity_id: str) -> Union[NPC, Corporation, Location, None]:
        """Retrieves an entity by its unique ID."""
        for store in [self.npcs, self.corporations, self.locations]:
            if entity_id in store:
                return store[entity_id]
        return None

    def update_entity(self, entity_id: str, updates: Dict[str, Any]):
        """Updates an entity's attributes."""
        entity = self.get_entity(entity_id)
        if entity:
            for key, value in updates.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            print(f"Updated entity: {entity_id}")
        else:
            print(f"Error: Entity not found: {entity_id}")