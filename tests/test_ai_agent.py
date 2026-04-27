"""
Tests for MusicRecommenderAgent.
All Gemini API calls are mocked so these run without a real API key.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.recommender import Song, UserProfile, DEFAULT_WEIGHTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(payload: dict | str) -> MagicMock:
    """Build a fake Gemini response whose .text is JSON-serialised payload."""
    resp = MagicMock()
    resp.text = json.dumps(payload) if isinstance(payload, dict) else payload
    return resp


def _make_agent(songs=None):
    """Create a MusicRecommenderAgent with all Gemini API calls patched out."""
    with patch("google.genai.Client"):
        from src.ai_agent import MusicRecommenderAgent
        agent = MusicRecommenderAgent(api_key="test-key", songs=songs or [])
    # Replace the client with a full mock so we control generate_content
    agent.client = MagicMock()
    return agent


SAMPLE_SONGS = [
    {
        "id": 1, "title": "Sunrise City", "artist": "Neon Echo",
        "genre": "pop", "mood": "happy", "energy": 0.82,
        "tempo_bpm": 118, "valence": 0.84, "danceability": 0.79, "acousticness": 0.18,
    },
    {
        "id": 2, "title": "Midnight Coding", "artist": "LoRoom",
        "genre": "lofi", "mood": "chill", "energy": 0.42,
        "tempo_bpm": 78, "valence": 0.56, "danceability": 0.62, "acousticness": 0.71,
    },
    {
        "id": 3, "title": "Storm Runner", "artist": "Voltline",
        "genre": "rock", "mood": "intense", "energy": 0.91,
        "tempo_bpm": 152, "valence": 0.48, "danceability": 0.66, "acousticness": 0.10,
    },
]


# ---------------------------------------------------------------------------
# validate_query
# ---------------------------------------------------------------------------

class TestValidateQuery:
    def test_returns_true_for_valid_music_query(self):
        agent = _make_agent()
        agent.client.models.generate_content.return_value = _mock_response(
            {"valid": True, "reason": "Clearly a music preference request"}
        )
        valid, reason = agent.validate_query("I want something upbeat")
        assert valid is True
        assert isinstance(reason, str)

    def test_returns_false_for_off_topic_query(self):
        agent = _make_agent()
        agent.client.models.generate_content.return_value = _mock_response(
            {"valid": False, "reason": "Not related to music"}
        )
        valid, reason = agent.validate_query("What's the weather today?")
        assert valid is False
        assert isinstance(reason, str)

    def test_defaults_to_valid_when_json_parse_fails(self):
        agent = _make_agent()
        agent.client.models.generate_content.return_value = _mock_response("not json at all")
        valid, _ = agent.validate_query("something")
        assert valid is True


# ---------------------------------------------------------------------------
# parse_user_query
# ---------------------------------------------------------------------------

class TestParseUserQuery:
    def test_returns_dict_with_required_keys(self):
        agent = _make_agent()
        agent.client.models.generate_content.return_value = _mock_response({
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.8,
            "likes_acoustic": False,
        })
        result = agent.parse_user_query("upbeat pop for the gym")
        assert result is not None
        assert result["favorite_genre"] == "pop"
        assert result["favorite_mood"] == "happy"
        assert isinstance(result["target_energy"], float)
        assert isinstance(result["likes_acoustic"], bool)

    def test_returns_none_on_api_failure(self):
        agent = _make_agent()
        agent.client.models.generate_content.side_effect = Exception("API error")
        result = agent.parse_user_query("some query")
        assert result is None


# ---------------------------------------------------------------------------
# generate_explanation
# ---------------------------------------------------------------------------

class TestGenerateExplanation:
    def test_returns_non_empty_string(self):
        agent = _make_agent()
        resp = MagicMock()
        resp.text = "These songs match your vibe perfectly!"
        agent.client.models.generate_content.return_value = resp

        user = UserProfile("pop", "happy", 0.8, False)
        songs = [Song(**SAMPLE_SONGS[0])]
        explanation = agent.generate_explanation(user, songs)
        assert isinstance(explanation, str)
        assert explanation.strip() != ""

    def test_returns_fallback_on_api_error(self):
        agent = _make_agent()
        agent.client.models.generate_content.side_effect = Exception("API error")
        user = UserProfile("pop", "happy", 0.8, False)
        songs = [Song(**SAMPLE_SONGS[0])]
        explanation = agent.generate_explanation(user, songs)
        assert isinstance(explanation, str)
        assert len(explanation) > 0


# ---------------------------------------------------------------------------
# self_critique
# ---------------------------------------------------------------------------

class TestSelfCritique:
    def test_returns_dict_with_required_keys(self):
        agent = _make_agent()
        agent.client.models.generate_content.return_value = _mock_response({
            "score": 8.5,
            "critique": "Great matches for genre and energy.",
            "weight_adjustments": {"genre": 2.0, "mood": 1.0, "energy": 2.0, "acoustic": 1.0},
            "should_retry": False,
        })
        user = UserProfile("pop", "happy", 0.8, False)
        songs = [Song(**s) for s in SAMPLE_SONGS]
        result = agent.self_critique(user, songs, DEFAULT_WEIGHTS.copy())

        assert "score" in result
        assert "critique" in result
        assert "weight_adjustments" in result
        assert "should_retry" in result

    def test_weight_adjustments_always_has_all_keys(self):
        agent = _make_agent()
        # Return partial weight_adjustments missing 'acoustic'
        agent.client.models.generate_content.return_value = _mock_response({
            "score": 5.0,
            "critique": "Energy mismatch.",
            "weight_adjustments": {"genre": 2.0, "mood": 1.0, "energy": 4.0},
            "should_retry": True,
        })
        user = UserProfile("pop", "happy", 0.8, False)
        songs = [Song(**s) for s in SAMPLE_SONGS]
        result = agent.self_critique(user, songs, DEFAULT_WEIGHTS.copy())

        assert "acoustic" in result["weight_adjustments"]

    def test_returns_safe_fallback_on_api_failure(self):
        agent = _make_agent()
        agent.client.models.generate_content.side_effect = Exception("API error")
        user = UserProfile("pop", "happy", 0.8, False)
        songs = [Song(**s) for s in SAMPLE_SONGS]
        result = agent.self_critique(user, songs, DEFAULT_WEIGHTS.copy())

        assert result["should_retry"] is False
        assert isinstance(result["score"], float)


# ---------------------------------------------------------------------------
# run_agentic_loop
# ---------------------------------------------------------------------------

class TestRunAgenticLoop:
    def _setup_agent_happy_path(self):
        """Return agent pre-wired for a successful single-iteration run."""
        agent = _make_agent(songs=SAMPLE_SONGS)
        call_count = {"n": 0}

        def side_effect(model, contents, **kwargs):
            call_count["n"] += 1
            prompt = contents

            if "guardrail" in prompt.lower() or '"valid"' in prompt or "off-topic" in prompt.lower():
                return _mock_response({"valid": True, "reason": "Music query"})
            if "favorite_genre" in prompt or "available genres" in prompt.lower():
                return _mock_response({
                    "favorite_genre": "pop",
                    "favorite_mood": "happy",
                    "target_energy": 0.8,
                    "likes_acoustic": False,
                })
            if "weight_adjustments" in prompt:
                return _mock_response({
                    "score": 8.0,
                    "critique": "Good matches.",
                    "weight_adjustments": DEFAULT_WEIGHTS.copy(),
                    "should_retry": False,
                })
            # Plain text: explanation
            r = MagicMock()
            r.text = "These pop songs perfectly match your upbeat, energetic mood."
            return r

        agent.client.models.generate_content.side_effect = side_effect
        return agent

    def test_successful_loop_returns_expected_keys(self):
        agent = self._setup_agent_happy_path()
        result = agent.run_agentic_loop("I want upbeat pop music")
        assert "songs" in result
        assert "explanation" in result
        assert "final_score" in result
        assert "iterations_history" in result
        assert len(result["songs"]) > 0

    def test_returns_error_on_invalid_query(self):
        agent = _make_agent(songs=SAMPLE_SONGS)
        agent.client.models.generate_content.return_value = _mock_response(
            {"valid": False, "reason": "Not music related"}
        )
        result = agent.run_agentic_loop("How do I bake a cake?")
        assert "error" in result

    def test_returns_error_when_parse_fails(self):
        agent = _make_agent(songs=SAMPLE_SONGS)
        call_count = {"n": 0}

        def side_effect(model, contents, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _mock_response({"valid": True, "reason": "ok"})
            raise Exception("parse failed")

        agent.client.models.generate_content.side_effect = side_effect
        result = agent.run_agentic_loop("some music query")
        assert "error" in result

    def test_stops_early_when_weights_unchanged(self):
        """If self-critique proposes the same weights, the loop stops after one iteration."""
        agent = _make_agent(songs=SAMPLE_SONGS)
        call_count = {"n": 0}

        def side_effect(model, contents, **kwargs):
            call_count["n"] += 1
            prompt = contents
            if call_count["n"] == 1:
                return _mock_response({"valid": True, "reason": "ok"})
            if "favorite_genre" in prompt or "available genres" in prompt.lower():
                return _mock_response({
                    "favorite_genre": "pop", "favorite_mood": "happy",
                    "target_energy": 0.8, "likes_acoustic": False,
                })
            if "weight_adjustments" in prompt:
                return _mock_response({
                    "score": 5.0, "critique": "Meh.",
                    "weight_adjustments": DEFAULT_WEIGHTS.copy(),  # unchanged → stop early
                    "should_retry": True,
                })
            r = MagicMock()
            r.text = "Here are some songs for you."
            return r

        agent.client.models.generate_content.side_effect = side_effect
        result = agent.run_agentic_loop("I want music", max_iterations=3)
        assert len(result.get("iterations_history", [])) == 1
