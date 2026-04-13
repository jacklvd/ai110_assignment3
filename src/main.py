"""
Command line runner for the Music Recommender Simulation.
"""

import os

try:
    from src.recommender import load_songs, recommend_songs, DEFAULT_WEIGHTS  # python -m src.main
except ModuleNotFoundError:
    from recommender import load_songs, recommend_songs, DEFAULT_WEIGHTS       # python3 main.py

# Resolve data path relative to this file so it works from any working directory
_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")

# ---------------------------------------------------------------------------
# User profiles to evaluate
# ---------------------------------------------------------------------------

PROFILES = [
    (
        "High-Energy Pop",
        {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False},
    ),
    (
        "Chill Lofi Study",
        {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True},
    ),
    (
        "Deep Intense Rock",
        {"genre": "rock", "mood": "intense", "energy": 0.92, "likes_acoustic": False},
    ),
    # --- adversarial / edge-case profiles ---
    (
        "Conflicting: Classical + Energetic (genre/energy fight each other)",
        {"genre": "classical", "mood": "energetic", "energy": 0.9, "likes_acoustic": True},
    ),
    (
        "Unknown Genre: kpop (no catalog match)",
        {"genre": "kpop", "mood": "happy", "energy": 0.75, "likes_acoustic": False},
    ),
    (
        "Edge: Extreme Low Energy + Sad (floor test)",
        {"genre": "folk", "mood": "melancholic", "energy": 0.05, "likes_acoustic": True},
    ),
]

# ---------------------------------------------------------------------------
# Experiment: double energy weight, halve genre weight
# ---------------------------------------------------------------------------

EXPERIMENT_WEIGHTS = {
    "genre":    1.0,   # halved from 2.0
    "mood":     1.0,
    "energy":   4.0,   # doubled from 2.0
    "acoustic": 1.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _max_score(weights: dict) -> float:
    """Return the theoretical maximum score for a given weight set."""
    return weights["genre"] + weights["mood"] + weights["energy"] + weights["acoustic"]


def _print_results(name: str, results: list, weights: dict) -> None:
    max_pts = _max_score(weights)
    bar = "─" * 56
    print(f"\n{bar}")
    print(f"  Profile: {name}")
    print(bar)
    for rank, (song, score, explanation) in enumerate(results, start=1):
        print(f"\n  #{rank}  {song['title']}  —  {song['artist']}")
        print(f"       Genre: {song['genre']}  |  Mood: {song['mood']}"
              f"  |  Energy: {song['energy']}")
        print(f"       Score: {score:.2f} / {max_pts:.2f}")
        for reason in explanation.split(" | "):
            print(f"         + {reason}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    songs = load_songs(_DATA_PATH)

    # --- Step 1 & 2: run all profiles with default weights ---
    print("\n" + "=" * 56)
    print("  PART 1 — Standard Weights  (genre=2, mood=1, energy×2)")
    print("=" * 56)

    for name, prefs in PROFILES:
        results = recommend_songs(prefs, songs, k=5)
        _print_results(name, results, DEFAULT_WEIGHTS)

    # --- Step 3: weight-shift experiment (High-Energy Pop profile) ---
    print("\n" + "=" * 56)
    print("  PART 2 — Weight Experiment  (genre=1, mood=1, energy×4)")
    print("  Profile: High-Energy Pop  (same user, different weights)")
    print("=" * 56)

    exp_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}
    exp_results = recommend_songs(exp_prefs, songs, k=5, weights=EXPERIMENT_WEIGHTS)
    _print_results("High-Energy Pop [EXPERIMENT]", exp_results, EXPERIMENT_WEIGHTS)

    print("  ↑ Compare this to PART 1 #1 to see how ranking shifts")
    print("    when energy matters twice as much as genre.\n")


if __name__ == "__main__":
    main()
