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
from modules.data_models import Location, Faction, NPC


def _safe_read(path: Path) -> dict:
    """Return {} if file absent / empty / bad JSON."""
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        print("Ignoring malformed JSON in %s", path)
        return {}


class WorldState:
    """
    JSON-backed storage for Locations, Factions, NPCs.
    Any CRUD call auto-saves to disk so the state is always current.
    """

    def __init__(self) -> None:
        self._locations: Path = config.WORLD_STATE
        self._factions: Path = config.FACTIONS
        self._npcs: Path = config.NPC
        self._locations.parent.mkdir(parents=True, exist_ok=True)
        self._factions.parent.mkdir(parents=True, exist_ok=True)
        self._npcs.parent.mkdir(parents=True, exist_ok=True)

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
        if not self._locations.exists():
            self._save()                       # create empty scaffold
            return

        locations = _safe_read(self._locations)
        factions = _safe_read(self._factions)
        npcs = _safe_read(self._npcs)

        self.locations = {o["id"]: Location(**o) for o in locations.get("locations", [])}
        self.factions  = {o["id"]: Faction(**o)  for o in factions.get("factions", [])}
        self.npcs      = {o["id"]: NPC(**o)      for o in npcs.get("npcs", [])}

    def _save(self) -> None:
        """Persist each collection into its dedicated file."""
        self._locations.write_text(
            json.dumps({"locations": [asdict(l) for l in self.locations.values()]},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._factions.write_text(
            json.dumps({"factions": [asdict(f) for f in self.factions.values()]},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._npcs.write_text(
            json.dumps({"npcs": [asdict(n) for n in self.npcs.values()]},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )