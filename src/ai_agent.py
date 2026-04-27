"""
Gemini-powered AI agent that extends the music recommender with:
  - Input guardrails (reject off-topic queries)
  - Natural-language → UserProfile parsing
  - AI-generated narrative explanations
  - Self-critique with confidence scoring
  - Agentic loop: iteratively adjusts weights when quality is low
"""

import json
import re
from typing import Optional

from google import genai
from google.genai import types

try:
    from src.recommender import UserProfile, Song, DEFAULT_WEIGHTS, recommend_songs
except ModuleNotFoundError:
    from recommender import UserProfile, Song, DEFAULT_WEIGHTS, recommend_songs

AVAILABLE_GENRES = [
    "pop", "lofi", "rock", "ambient", "jazz", "synthwave",
    "indie pop", "hip-hop", "country", "metal", "edm", "folk",
    "r&b", "classical", "blues",
]
AVAILABLE_MOODS = [
    "happy", "chill", "intense", "relaxed", "focused", "moody",
    "energetic", "nostalgic", "melancholic", "romantic", "serene", "sad",
]

_MODEL = "gemini-2.0-flash"


class MusicRecommenderAgent:
    def __init__(self, api_key: str, songs: list[dict] | None = None):
        self.client = genai.Client(api_key=api_key)
        self.songs = songs or []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_json(self, prompt: str) -> dict:
        """Call Gemini with JSON response mode. Returns {} on any failure."""
        try:
            response = self.client.models.generate_content(
                model=_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            return json.loads(response.text)
        except Exception:
            try:
                text = response.text.strip()
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
                return json.loads(text.strip())
            except Exception:
                return {}

    def _call_text(self, prompt: str) -> str:
        """Call Gemini and return plain text. Returns fallback string on failure."""
        try:
            response = self.client.models.generate_content(
                model=_MODEL,
                contents=prompt,
            )
            return response.text.strip()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Guardrail
    # ------------------------------------------------------------------

    def validate_query(self, text: str) -> tuple[bool, str]:
        """Return (is_valid, reason). Rejects queries unrelated to music."""
        prompt = f"""You are a guardrail for a music recommendation system.
Determine if the following user query is requesting music recommendations or describing music preferences.
Respond with JSON only: {{"valid": true/false, "reason": "one-sentence explanation"}}

User query: "{text}"
"""
        result = self._call_json(prompt)
        if not result:
            return True, "Could not validate; proceeding"
        return bool(result.get("valid", True)), result.get("reason", "")

    # ------------------------------------------------------------------
    # Natural-language query parsing
    # ------------------------------------------------------------------

    def parse_user_query(self, text: str) -> Optional[dict]:
        """Convert a natural-language music request into a structured profile dict."""
        prompt = f"""You are parsing a music preference request into structured data.

Available genres: {', '.join(AVAILABLE_GENRES)}
Available moods: {', '.join(AVAILABLE_MOODS)}

Convert the user's request to JSON with these exact keys:
- "favorite_genre": one of the available genres (choose the closest match)
- "favorite_mood": one of the available moods (choose the closest match)
- "target_energy": float 0.0–1.0 (0 = very calm, 1 = very energetic)
- "likes_acoustic": true or false

User request: "{text}"

Respond with valid JSON only.
"""
        result = self._call_json(prompt)
        return result if result else None

    # ------------------------------------------------------------------
    # Narrative explanation
    # ------------------------------------------------------------------

    def generate_explanation(self, user_profile: UserProfile, songs: list[Song]) -> str:
        """Generate a friendly narrative explaining why these songs fit the user."""
        song_list = "\n".join(
            f"- {s.title} by {s.artist} (genre: {s.genre}, mood: {s.mood}, energy: {s.energy})"
            for s in songs
        )
        prompt = f"""You are a music recommendation assistant.

User preferences:
- Favorite genre: {user_profile.favorite_genre}
- Favorite mood: {user_profile.favorite_mood}
- Target energy level: {user_profile.target_energy:.2f} (0 = calm, 1 = energetic)
- Likes acoustic: {user_profile.likes_acoustic}

Recommended songs:
{song_list}

Write a friendly 2–3 sentence explanation of why these songs match this user.
Be specific about the features (genre, mood, energy). Be conversational, not robotic.
"""
        result = self._call_text(prompt)
        return result or "These songs were selected based on your genre, mood, and energy preferences."

    # ------------------------------------------------------------------
    # Self-critique / confidence scoring
    # ------------------------------------------------------------------

    def self_critique(
        self, user_profile: UserProfile, songs: list[Song], weights: dict
    ) -> dict:
        """
        Score recommendation quality and suggest weight adjustments if needed.
        Returns {"score": float, "critique": str, "weight_adjustments": dict, "should_retry": bool}
        """
        song_list = "\n".join(
            f"- {s.title} (genre: {s.genre}, mood: {s.mood}, energy: {s.energy})"
            for s in songs
        )
        prompt = f"""You are evaluating music recommendation quality.

User wants: genre={user_profile.favorite_genre}, mood={user_profile.favorite_mood},
energy={user_profile.target_energy:.2f}, likes_acoustic={user_profile.likes_acoustic}

Current scoring weights: genre={weights['genre']}, mood={weights['mood']},
energy_multiplier={weights['energy']}, acoustic_bonus={weights['acoustic']}

Top recommended songs:
{song_list}

Evaluate how well these recommendations match the user's stated preferences.
Respond with JSON:
{{
  "score": <float 0–10, where 10 = perfect match>,
  "critique": "<one sentence honest assessment>",
  "weight_adjustments": {{
    "genre": <float, suggest a new value if needed>,
    "mood": <float, suggest a new value if needed>,
    "energy": <float, suggest a new value if needed>,
    "acoustic": <float, suggest a new value if needed>
  }},
  "should_retry": <true if score < 7 and adjusting weights could improve results>
}}
"""
        result = self._call_json(prompt)
        if not result:
            return {
                "score": 7.0,
                "critique": "Could not evaluate recommendations.",
                "weight_adjustments": weights.copy(),
                "should_retry": False,
            }
        # Ensure weight_adjustments always has all required keys
        adj = result.get("weight_adjustments", {})
        for key in weights:
            if key not in adj:
                adj[key] = weights[key]
        result["weight_adjustments"] = adj
        result.setdefault("should_retry", False)
        return result

    # ------------------------------------------------------------------
    # Agentic loop (full pipeline)
    # ------------------------------------------------------------------

    def run_agentic_loop(self, query: str, max_iterations: int = 3) -> dict:
        """
        Full AI pipeline:
          1. Guardrail: validate the query is music-related
          2. Parse: convert natural language to user preferences
          3. Recommend: score songs with current weights
          4. Self-critique: score quality; if low, adjust weights and retry
          5. Explain: generate a narrative for the final result
        """
        # Step 1 — Guardrail
        valid, reason = self.validate_query(query)
        if not valid:
            return {"error": f"Query rejected: {reason}"}

        # Step 2 — Parse
        profile_dict = self.parse_user_query(query)
        if not profile_dict:
            return {"error": "Could not understand your music preferences. Please try rephrasing."}

        user_prefs = {
            "genre": profile_dict.get("favorite_genre", "pop"),
            "mood": profile_dict.get("favorite_mood", "happy"),
            "energy": float(profile_dict.get("target_energy", 0.5)),
            "likes_acoustic": bool(profile_dict.get("likes_acoustic", False)),
        }
        user_profile = UserProfile(
            favorite_genre=user_prefs["genre"],
            favorite_mood=user_prefs["mood"],
            target_energy=user_prefs["energy"],
            likes_acoustic=user_prefs["likes_acoustic"],
        )

        weights = DEFAULT_WEIGHTS.copy()
        iteration_history: list[dict] = []
        recommended_songs: list[Song] = []
        critique: dict = {}

        # Steps 3–4 — Recommend → Critique → (optionally) Adjust → Repeat
        for i in range(max_iterations):
            results = recommend_songs(user_prefs, self.songs, k=5, weights=weights)
            recommended_songs = [Song(**song) for song, _, _ in results]

            critique = self.self_critique(user_profile, recommended_songs, weights)
            iteration_history.append(
                {
                    "iteration": i + 1,
                    "weights": weights.copy(),
                    "score": critique.get("score", 0),
                    "critique": critique.get("critique", ""),
                }
            )

            if not critique.get("should_retry", False):
                break

            new_weights = critique.get("weight_adjustments", weights)
            if new_weights == weights:
                break  # No change proposed; stop early
            weights = new_weights

        # Step 5 — Explain
        explanation = self.generate_explanation(user_profile, recommended_songs)

        return {
            "user_profile": user_prefs,
            "user_profile_obj": user_profile,
            "songs": recommended_songs,
            "explanation": explanation,
            "final_score": critique.get("score", 0),
            "final_critique": critique.get("critique", ""),
            "iterations_history": iteration_history,
            "final_weights": weights,
        }
