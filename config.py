"""Central paths & constants for the GM Helper."""
from pathlib import Path

PROJECT_ROOT   = Path(__file__).resolve().parent
DATA_DIR       = PROJECT_ROOT / "data"
KB_DIR         = PROJECT_ROOT / "source_files"
VECTOR_DIR     = PROJECT_ROOT / "vector_store"
WORLD_STATE    = DATA_DIR / "world_state.json"
FACTIONS       = DATA_DIR / "factions.json"
NPC            = DATA_DIR / "npcs.json"
SESSION_TXT    = DATA_DIR / "session_transcripts"
SESSION_SUM    = DATA_DIR / "session_summaries"
EMBED_MODEL    = "all-MiniLM-L6-v2"