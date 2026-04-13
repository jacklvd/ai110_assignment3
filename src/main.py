"""
Command line runner for the Music Recommender Simulation.
"""

import os

try:
    from src.recommender import load_songs, recommend_songs  # python -m src.main
except ModuleNotFoundError:
    from recommender import load_songs, recommend_songs       # python3 main.py

# Resolve data path relative to this file so it works from any working directory
_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")


def main() -> None:
    songs = load_songs(_DATA_PATH)

    user_prefs = {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "likes_acoustic": False,
    }

    print("\nUser profile:")
    for key, value in user_prefs.items():
        print(f"  {key}: {value}")

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print(f"\n{'─' * 52}")
    print(f"  Top {len(recommendations)} Recommendations")
    print(f"{'─' * 52}")

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n  #{rank}  {song['title']}  —  {song['artist']}")
        print(f"       Genre: {song['genre']}  |  Mood: {song['mood']}"
              f"  |  Energy: {song['energy']}")
        print(f"       Score: {score:.2f} / 6.00")
        for reason in explanation.split(" | "):
            print(f"         + {reason}")

    print(f"\n{'─' * 52}\n")


if __name__ == "__main__":
    main()
