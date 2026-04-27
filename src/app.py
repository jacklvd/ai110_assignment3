"""
Streamlit UI for the AI-powered Music Recommender.
Run with: streamlit run src/app.py
"""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

try:
    from src.recommender import load_songs
    from src.ai_agent import MusicRecommenderAgent
    from src.logger import RecommendationLogger
except ModuleNotFoundError:
    from recommender import load_songs
    from ai_agent import MusicRecommenderAgent
    from logger import RecommendationLogger

load_dotenv()

_DATA_PATH = Path(__file__).parent.parent / "data" / "songs.csv"
_LOGGER = RecommendationLogger()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="VibeFinder",
    page_icon="🎵",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS — warm parchment palette
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    /* ── Global ── */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #FDF8F0;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #F0E6CC;
        border-right: 1px solid #D9C9A8;
    }
    [data-testid="stSidebar"] * {
        color: #2D1B0E !important;
    }

    /* ── Page title ── */
    h1 {
        color: #4A3118 !important;
        font-family: Georgia, serif;
        letter-spacing: 0.02em;
        border-bottom: 2px solid #C4A265;
        padding-bottom: 0.3rem;
    }

    /* ── Section headings ── */
    h2, h3 {
        color: #5C3D1E !important;
        font-family: Georgia, serif;
    }

    /* ── Primary button ── */
    div.stButton > button[kind="primary"] {
        background-color: #7C5C2E;
        color: #FDF8F0;
        border: none;
        border-radius: 6px;
        font-family: Georgia, serif;
        font-size: 1rem;
        padding: 0.55rem 1.4rem;
        transition: background-color 0.2s;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #5C3D1E;
        color: #FDF8F0;
    }

    /* ── Text area ── */
    textarea {
        background-color: #FFFDF7 !important;
        border: 1px solid #C4A265 !important;
        border-radius: 6px !important;
        color: #2D1B0E !important;
        font-family: Georgia, serif !important;
    }

    /* ── Metric labels & values ── */
    [data-testid="stMetricLabel"] p {
        color: #7C5C2E !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    [data-testid="stMetricValue"] {
        color: #2D1B0E !important;
        font-family: Georgia, serif;
    }

    /* ── Info / warning boxes ── */
    [data-testid="stAlert"] {
        background-color: #F5ECD5 !important;
        border-left: 4px solid #C4A265 !important;
        border-radius: 6px;
        color: #2D1B0E !important;
    }

    /* ── Expander ── */
    details summary {
        color: #7C5C2E !important;
        font-family: Georgia, serif;
    }

    /* ── Song card container ── */
    .song-card {
        background-color: #FFFDF7;
        border: 1px solid #D9C9A8;
        border-left: 4px solid #C4A265;
        border-radius: 8px;
        padding: 0.9rem 1.1rem 0.6rem;
        margin-bottom: 0.7rem;
        box-shadow: 0 1px 4px rgba(90,60,20,0.08);
    }
    .song-card-title {
        font-family: Georgia, serif;
        font-size: 1.05rem;
        font-weight: bold;
        color: #2D1B0E;
        margin-bottom: 0.25rem;
    }
    .song-card-artist {
        font-style: italic;
        color: #7C5C2E;
    }
    .song-tag {
        display: inline-block;
        background-color: #F0E6CC;
        color: #5C3D1E;
        border-radius: 4px;
        padding: 0.15rem 0.55rem;
        font-size: 0.78rem;
        margin-right: 0.4rem;
        margin-top: 0.4rem;
        font-family: Georgia, serif;
    }
    .rank-badge {
        display: inline-block;
        background-color: #C4A265;
        color: #FDF8F0;
        border-radius: 50%;
        width: 1.7rem;
        height: 1.7rem;
        line-height: 1.7rem;
        text-align: center;
        font-size: 0.85rem;
        font-weight: bold;
        margin-right: 0.5rem;
    }

    /* ── Divider ── */
    hr {
        border-color: #D9C9A8 !important;
    }

    /* ── Spinner text ── */
    [data-testid="stSpinner"] p {
        color: #7C5C2E !important;
    }

    /* ── Caption / small text ── */
    [data-testid="stCaptionContainer"] p,
    .stCaption {
        color: #8B7355 !important;
        font-family: Georgia, serif;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🎵 VibeFinder")
st.caption(
    "Describe what you want to hear in plain English — "
    "Gemini will parse your vibe, find the best matches, and explain why they fit."
)

# ---------------------------------------------------------------------------
# Sidebar — API key + stats + recent queries
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input(
        "Gemini API Key",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
        help="Get a free key at https://aistudio.google.com/app/apikey",
    )

    st.divider()
    st.subheader("📊 Stats")
    stats = _LOGGER.get_stats()
    col_a, col_b = st.columns(2)
    col_a.metric("Queries", stats["total_queries"])
    col_b.metric("Avg Score", f"{stats['avg_confidence']}/10" if stats["avg_confidence"] else "—")

    st.divider()
    st.subheader("🕘 Recent")
    recent = [l for l in _LOGGER.get_recent_logs(10) if l["event"] == "recommendation"]
    if recent:
        for log in reversed(recent[-5:]):
            score = log.get("confidence_score")
            score_str = f" · {score:.1f}" if score is not None else ""
            q = log.get("query", "")
            st.caption(f"• {q[:32]}{'…' if len(q) > 32 else ''}{score_str}")
    else:
        st.caption("No recommendations yet.")

# ---------------------------------------------------------------------------
# Main — query input
# ---------------------------------------------------------------------------

if not api_key:
    st.warning("Enter your Gemini API Key in the sidebar to get started.")
    st.stop()

st.markdown("### What are you in the mood for?")
query = st.text_area(
    label="query",
    label_visibility="collapsed",
    placeholder=(
        "e.g. 'something upbeat and energetic for my morning run' "
        "or 'chill acoustic music to study to at night'"
    ),
    height=100,
)

col_btn, col_iter = st.columns([3, 1])
with col_btn:
    submit = st.button("Find My Songs", type="primary", use_container_width=True)
with col_iter:
    max_iter = st.selectbox("Refinement loops", [1, 2, 3], index=1)

# ---------------------------------------------------------------------------
# Load songs and agent (cached in session state)
# ---------------------------------------------------------------------------

if "songs" not in st.session_state:
    with st.spinner("Loading catalog…"):
        st.session_state.songs = load_songs(str(_DATA_PATH))

if "agent_key" not in st.session_state or st.session_state.agent_key != api_key:
    st.session_state.agent = MusicRecommenderAgent(
        api_key=api_key, songs=st.session_state.songs
    )
    st.session_state.agent_key = api_key

agent: MusicRecommenderAgent = st.session_state.agent

# ---------------------------------------------------------------------------
# Run the agentic pipeline
# ---------------------------------------------------------------------------

if submit and query.strip():
    with st.spinner("Gemini is analyzing your request…"):
        result = agent.run_agentic_loop(query.strip(), max_iterations=max_iter)

    if "error" in result:
        st.error(result["error"])
        _LOGGER.log_error(query, result["error"])
        st.stop()

    _LOGGER.log_recommendation(query, result)

    st.divider()

    # ------------------------------------------------------------------
    # Confidence row
    # ------------------------------------------------------------------
    score = result.get("final_score", 0)
    critique = result.get("final_critique", "")
    history = result.get("iterations_history", [])

    col_score, col_iters, col_genre, col_mood = st.columns(4)
    col_score.metric("Confidence", f"{score:.1f} / 10")
    col_iters.metric("Refinement loops", len(history))
    prefs = result["user_profile"]
    col_genre.metric("Parsed genre", prefs["genre"].title())
    col_mood.metric("Parsed mood", prefs["mood"].title())

    # Parsed profile detail
    with st.expander("Full parsed profile", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Genre", prefs["genre"].title())
        c2.metric("Mood", prefs["mood"].title())
        c3.metric("Energy", f"{prefs['energy']:.2f}")
        c4.metric("Acoustic", "Yes" if prefs["likes_acoustic"] else "No")

    if critique:
        st.info(f"**AI Assessment:** {critique}")

    if len(history) > 1:
        with st.expander("Refinement history", expanded=False):
            for h in history:
                st.write(
                    f"Loop {h['iteration']} — score: **{h['score']:.1f}** | "
                    f"genre weight: {h['weights']['genre']}, "
                    f"energy weight: {h['weights']['energy']} — "
                    f"{h['critique']}"
                )

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------
    st.markdown("### Why these songs?")
    st.markdown(
        f"<div style='background:#F5ECD5;border-left:4px solid #C4A265;"
        f"border-radius:6px;padding:0.8rem 1rem;font-family:Georgia,serif;"
        f"color:#2D1B0E;line-height:1.6'>{result['explanation']}</div>",
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Song cards
    # ------------------------------------------------------------------
    st.markdown("### Your top picks")
    for rank, song in enumerate(result["songs"], 1):
        energy_pct = int(song.energy * 100)
        acoustic_pct = int(song.acousticness * 100)
        st.markdown(
            f"""
            <div class="song-card">
                <div class="song-card-title">
                    <span class="rank-badge">{rank}</span>
                    {song.title}
                    <span class="song-card-artist"> — {song.artist}</span>
                </div>
                <span class="song-tag">🎸 {song.genre.title()}</span>
                <span class="song-tag">😊 {song.mood.title()}</span>
                <span class="song-tag">⚡ Energy {energy_pct}%</span>
                <span class="song-tag">🎵 {int(song.tempo_bpm)} BPM</span>
                <span class="song-tag">🪵 Acoustic {acoustic_pct}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

elif submit and not query.strip():
    st.warning("Please describe what you're in the mood for before searching.")
