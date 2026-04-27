"""
Structured JSONL logger for recommendation events and errors.
Each line in the log file is a self-contained JSON object.
"""

import json
import datetime
from pathlib import Path


class RecommendationLogger:
    def __init__(self, log_path: str = "logs/recommendations.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, entry: dict) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def _base(self, event_type: str) -> dict:
        return {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "event": event_type,
        }

    def log_recommendation(self, query: str, result: dict) -> None:
        """Log a completed recommendation run."""
        history = result.get("iterations_history", [])
        entry = {
            **self._base("recommendation"),
            "query": query,
            "user_profile": result.get("user_profile"),
            "num_songs": len(result.get("songs", [])),
            "confidence_score": result.get("final_score"),
            "critique": result.get("final_critique"),
            "num_iterations": len(history),
            "iteration_scores": [h["score"] for h in history],
            "final_weights": result.get("final_weights"),
        }
        self._write(entry)

    def log_error(self, query: str, error: str) -> None:
        """Log a failed or rejected query."""
        entry = {**self._base("error"), "query": query, "error": error}
        self._write(entry)

    def get_recent_logs(self, n: int = 10) -> list[dict]:
        """Return the last n log entries (newest last)."""
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        recent = lines[-n:] if len(lines) > n else lines
        result = []
        for line in recent:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result

    def get_stats(self) -> dict:
        """Return aggregate statistics across all logged recommendations."""
        logs = self.get_recent_logs(n=10_000)
        recommendations = [l for l in logs if l["event"] == "recommendation"]
        errors = [l for l in logs if l["event"] == "error"]
        scores = [
            r["confidence_score"]
            for r in recommendations
            if r.get("confidence_score") is not None
        ]
        return {
            "total_queries": len(recommendations) + len(errors),
            "total_recommendations": len(recommendations),
            "total_errors": len(errors),
            "avg_confidence": round(sum(scores) / len(scores), 2) if scores else None,
            "avg_iterations": (
                round(
                    sum(r.get("num_iterations", 1) for r in recommendations)
                    / len(recommendations),
                    2,
                )
                if recommendations
                else None
            ),
        }
