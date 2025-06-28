# cpr_helper/world_state.py  ★ NEW detailed entity model ★
"""JSON‑backed, strongly‑typed world state for a Cyberpunk RED campaign."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any

def slug(text: str) -> str:
    """Lower-case, replace non-alphanumerics → ID-safe slug."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

# ── Entity dataclasses ─────────────────────────────────────────────
@dataclass
class Location:
    """A place in Night City or beyond. Can nest via `parent_location`."""
    id: str
    name: str
    description: str = ""
    type: str = "Location"           # Location | SubLocation
    parent_location: str = ""         # id of parent if SubLocation
    city_manager: str = ""           # NPC id or free‑text
    security_provider: str = ""      # corp / faction responsible
    region: str = ""                 # district / biome
    factions: List[str] = field(default_factory=list)  # faction ids present
    events: List[str] = field(default_factory=list)    # event ids / strings

@dataclass
class NPC:
    id: str
    name: str
    description: str = ""
    role: str = "NPC"
    affiliation: str = ""  # corp/faction id
    location: str = ""     # current location id
    home_location: str = ""  # location.id where they are usually found
    current_location: str = ""       # location.id if they’ve moved
    notes: str = ""
    relationships: Dict[str, str] = field(default_factory=dict)  # npc.id → description

@dataclass
class Faction:
    id: str
    name: str
    type: str = "gang"       # gang / booster / nomad pack / etc.
    description: str = ""

@dataclass
class Corporation:
    id: str
    name: str
    tier: str = "AA"          # AAA / AA / etc.
    description: str = ""

@dataclass
class Player:
    id: str
    handle: str
    character_name: str
    role: str               # Solo, Netrunner, etc.
    notes: str = ""