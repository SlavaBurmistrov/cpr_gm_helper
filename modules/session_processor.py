# modules/session_processor.py
from __future__ import annotations
import datetime as dt, json, re, math
from pathlib import Path
from typing import List, Dict, Any
import openai, tiktoken
from pprint import pprint

from modules.world_state import WorldState
from modules.data_models import Location, Faction, NPC, slug
import config

ENC = tiktoken.get_encoding("cl100k_base")        # tokeniser for GPT-4o-mini

# ---------- tuneables ----------
CHUNK_TOKENS   = 3_000   # ~12k chars; keeps plenty of headroom
MODEL_NAME     = "gpt-4.1-nano"
SYSTEM_HEADER  = (
    "You are an AI scribe for a Cyberpunk RED TTRPG session.\n"
    "For the given chunk, (1) write a concise summary, then (2) return JSON "
    "arrays called 'locations', 'npcs', 'factions' containing only NEW or "
    "UPDATED entries. Follow the supplied schemas exactly."
)
# JSON schemas for function-calling (shortened here for brevity)
FUNCTION_SCHEMA: Dict[str, Any] = {
    "name": "chunk_result",
    "description": "Summary + world-state deltas for one transcript chunk.",
    "parameters": {
        "type": "object",
        "properties": {
            "summary":    {"type": "string"},
            "locations":  {"type": "array", "items": {"$ref": "#/definitions/location"}},
            "npcs":       {"type": "array", "items": {"$ref": "#/definitions/npc"}},
            "factions":   {"type": "array", "items": {"$ref": "#/definitions/faction"}}
        },
        "definitions": {
            "location": {
                "type":"object",
                "required":["name","description"],
                "properties": {
                    "name":{"type":"string"},"description":{"type":"string"},
                    "region":{"type":"string"},"parent":{"type":"string"}
                }
            },
            "npc": {
                "type":"object",
                "required":["name","description"],
                "properties": {
                    "name":{"type":"string"},"description":{"type":"string"},
                    "role":{"type":"string"},"faction":{"type":"string"},
                    "home":{"type":"string"}
                }
            },
            "faction": {
                "type":"object",
                "required":["name","description"],
                "properties": {
                    "name":{"type":"string"},"description":{"type":"string"},
                    "type":{"type":"string"}
                }
            }
        }
    }
}
# --------------------------------

class SessionProcessor:
    def __init__(self, api_key: str | None = None):
        self.oai = openai.OpenAI(api_key=api_key or config.OPENAI_API_KEY)
        self.ws  = WorldState()

    # ~~~~~~~~~~~~~~~~~ public entry ~~~~~~~~~~~~~~~~~ #
    def process(self, transcript_path: str | Path) -> None:
        text = Path(transcript_path).read_text("utf-8", errors="replace")
        chunks = self._split_by_tokens(text, CHUNK_TOKENS)
        chunk_results = [self._analyze_chunk(c) for c in chunks]

        # 1️⃣  rolling summary list
        summaries = [cr["summary"] for cr in chunk_results]
        print(summaries)
        # 2️⃣  merge deltas
        for cr in chunk_results:
            self._apply_deltas(cr)

        # 3️⃣  global session summary
        master_summary = self._summarise_session(summaries)

        self._write_summary_file(master_summary, transcript_path)
        print("✓ Session processed — world state updated.")

    # ~~~~~~~~~~~~~~~~~ helpers ~~~~~~~~~~~~~~~~~ #
    def _split_by_tokens(self, text: str, max_tok: int) -> List[str]:
        words, buf, chunks = text.split(), [], []
        for w in words:
            buf.append(w)
            if len(ENC.encode(" ".join(buf))) > max_tok:
                chunks.append(" ".join(buf))
                buf = []
        if buf:
            chunks.append(" ".join(buf))

        return chunks

    def _analyze_chunk(self, chunk: str) -> dict:
        messages = [{"role":"system","content":SYSTEM_HEADER},
                    {"role":"user","content":chunk}]
        resp = self.oai.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=[{"type":"function","function":FUNCTION_SCHEMA}],
            tool_choice="auto",
            temperature=0.2,
        )
        tool_calls = resp.choices[0].message.tool_calls
        test1 = json.loads(tool_calls[0].function.arguments)
        test2 = json.loads(tool_calls[1].function.arguments)
        return {**test1, **test2}

    def _apply_deltas(self, data: dict) -> None:
        # Locations
        # pprint(data)
        for item in data.get("locations", []):
            print(item)
            loc_id = slug(item["name"])
            # self.ws.upsert_location(
            #     Location(
            #         id=loc_id,
            #         name=item["name"],
            #         description=item["description"],
            #         region=item.get("region",""),
            #         parent_location=slug(item.get("parent","")) if item.get("parent") else ""
            #     )
            # )
            print(
                Location(
                    id=loc_id,
                    name=item["name"],
                    description=item["description"],
                    region=item.get("region",""),
                    parent_location=slug(item.get("parent","")) if item.get("parent") else ""
                )
            )
        # NPCs
        for item in data.get("npcs", []):
            npc_id = slug(item["name"])
            # self.ws.upsert_npc(
            #     NPC(
            #         id=npc_id,
            #         name=item["name"],
            #         description=item["description"],
            #         role=item.get("role",""),
            #         affiliation=slug(item.get("faction","")) if item.get("faction") else "",
            #         home_location=slug(item.get("home","")) if item.get("home") else "",
            #         location=slug(item.get("home","")) if item.get("home") else "",
            #     )
            # )
            print(
                NPC(
                    id=npc_id,
                    name=item["name"],
                    description=item["description"],
                    role=item.get("role",""),
                    affiliation=slug(item.get("faction","")) if item.get("faction") else "",
                    home_location=slug(item.get("home","")) if item.get("home") else "",
                    location=slug(item.get("home","")) if item.get("home") else "",
                )
            )
        # Factions
        for item in data.get("factions", []):
            fac_id = slug(item["name"])
            # self.ws.upsert_faction(
            #     Faction(
            #         id=fac_id,
            #         name=item["name"],
            #         description=item["description"],
            #         type=item.get("type","gang")
            #     )
            # )
            print(
                Faction(
                    id=fac_id,
                    name=item["name"],
                    description=item["description"],
                    type=item.get("type","gang")
                )
            )

    def _summarise_session(self, chunk_summaries: List[str]) -> str:
        prompt = (
            "Combine the following ordered chunk summaries into one coherent "
            "≤200-word session recap, preserving chronology.\n\n"
            + "\n\n".join(f"{i+1}. {s}" for i,s in enumerate(chunk_summaries))
        )
        resp = self.oai.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role":"system","content":"You are a concise narrator."},
                      {"role":"user","content":prompt}],
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()

    def _write_summary_file(self, summary: str, src: str | Path) -> None:
        date = dt.date.today().isoformat()
        stem = slug(Path(src).stem)
        outdir = Path(config.SESSION_SUM)
        outdir.mkdir(parents=True, exist_ok=True)
        fpath = outdir / f"{date}_{stem}.md"
        fpath.write_text(summary, encoding="utf-8")
        print("Summary saved →", fpath)
