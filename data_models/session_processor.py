import json
from langchain.llms import Ollama  # Or another LLM provider


class SessionProcessor:
    """Summarizes and extracts state changes from session transcripts."""

    def __init__(self):
        self.llm = Ollama(model="llama3")  # Use a powerful model for this task

    def process_transcript(self, transcript: str) -> (str, List[Dict]):
        """
        Generates a summary and extracts structured state change events.

        This is the most complex AI task. It requires strong prompt engineering.
        """
        summary = self._generate_summary(transcript)
        state_changes = self._extract_state_changes(transcript)
        return summary, state_changes

    def _generate_summary(self, transcript: str) -> str:
        prompt = f"""
        Read the following transcript from a Cyberpunk Red TTRPG session.
        Provide a concise, narrative summary of the key events, decisions, and outcomes.
        Format it like a mission report.

        Transcript:
        ---
        {transcript}
        ---
        Summary:
        """
        return self.llm(prompt)

    def _extract_state_changes(self, transcript: str) -> List[Dict]:
        prompt = f"""
        You are an AI assistant that analyzes game transcripts to update a world database.
        Analyze the Cyberpunk Red session transcript below.
        Identify events that change the state of NPCs, Corporations, or Locations.
        Output a JSON list of update objects.

        Valid object keys are:
        - "entity_id": The unique ID of the entity being changed (e.g., "npc-morgan-blackhand").
        - "update_type": "modify" or "note".
        - "field": The attribute of the entity to change (e.g., "location", "status", "relationships").
        - "new_value": The new value for that attribute. For notes, this is the text to append.

        Example:
        Transcript: The players convinced the NPC 'Rogue' to leave Watson and hide out at The Afterlife. They also shot and killed 'MaelstromGoon1'.
        Output:
        [
            {{
                "entity_id": "npc-rogue",
                "update_type": "modify",
                "field": "location",
                "new_value": "The Afterlife"
            }},
            {{
                "entity_id": "npc-maelstromgoon1",
                "update_type": "modify",
                "field": "status",
                "new_value": "Deceased"
            }},
            {{
                "entity_id": "npc-rogue",
                "update_type": "note",
                "field": "notes",
                "new_value": "Convinced by the players to relocate to The Afterlife for safety on [Current Date]."
            }}
        ]

        Transcript:
        ---
        {transcript}
        ---
        JSON Output:
        """
        response = self.llm(prompt)
        try:
            # Clean up the response, as LLMs sometimes add extra text
            json_response = response[response.find('['):response.rfind(']') + 1]
            return json.loads(json_response)
        except (json.JSONDecodeError, IndexError):
            print("Error: LLM did not return valid JSON for state changes.")
            return []