# modules/world_state.py
# ----------------------------------------------------------
# Loads, mutates, and persists the living campaign world
# ----------------------------------------------------------
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

import config
from modules.data_models import Location, Faction, NPC, slug


class WorldState:
    """
    JSON-backed storage for Locations, Factions, NPCs.
    Any CRUD call auto-saves to disk so the state is always current.
    """

    def __init__(self, store_path: Path | None = None) -> None:
        self._path: Path = store_path or config.WORLD_STATE
        self._path.parent.mkdir(parents=True, exist_ok=True)

        self.locations: Dict[str, Location] = {}
        self.factions: Dict[str, Faction] = {}
        self.npcs: Dict[str, NPC] = {}

        self._load()

    # ───────────────────── Locations ───────────────────── #
    def upsert_location(self, loc: Location) -> None:
        self.locations[loc.id] = loc
        self._save()

    def delete_location(self, loc_id: str) -> None:
        if loc_id in self.locations:
            del self.locations[loc_id]
            self._save()

    def children_of(self, parent_id: str) -> List[Location]:
        return [l for l in self.locations.values() if l.parent_location == parent_id]

    # ───────────────────── Factions ───────────────────── #
    def upsert_faction(self, fac: Faction) -> None:
        self.factions[fac.id] = fac
        self._save()

    def delete_faction(self, fac_id: str) -> None:
        if fac_id in self.factions:
            del self.factions[fac_id]
            self._save()

    # ───────────────────── NPCs ───────────────────── #
    def upsert_npc(self, npc: NPC) -> None:
        self.npcs[npc.id] = npc
        self._save()

    def delete_npc(self, npc_id: str) -> None:
        if npc_id in self.npcs:
            del self.npcs[npc_id]
            self._save()

    # ─────────────────── I/O helpers ─────────────────── #
    def _load(self) -> None:
        if not self._path.exists():
            self._save()                       # create empty scaffold
            return

        data = json.loads(self._path.read_text(encoding="utf-8", errors="replace"))
        self.locations = {o["id"]: Location(**o) for o in data.get("locations", [])}
        self.factions  = {o["id"]: Faction(**o)  for o in data.get("factions", [])}
        self.npcs      = {o["id"]: NPC(**o)      for o in data.get("npcs", [])}

    def _save(self) -> None:
        payload = {
            "locations": [asdict(l) for l in self.locations.values()],
            "factions":  [asdict(f) for f in self.factions.values()],
            "npcs":      [asdict(n) for n in self.npcs.values()],
        }
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )