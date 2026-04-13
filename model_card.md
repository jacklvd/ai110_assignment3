# Model Card: Music Recommender Simulation

## 1. Model Name

VibeFinder 1.0

---

## 2. Goal / Task

VibeFinder tries to answer one question: "Given what I know about a listener's taste, which songs in this catalog will they most enjoy right now?"

It does this by comparing a user's stated preferences — their favorite genre, current mood, how energetic they want the music, and whether they like acoustic sounds — against the features of every song in the catalog. The goal is to surface the songs that are the closest match, not just the most popular or highest-energy ones.

---

## 3. Data Used

- **Catalog size**: 18 songs
- **Features per song**: genre, mood, energy (0.0–1.0), tempo in BPM, valence (positivity), danceability, and acousticness
- **Genres covered**: pop, lofi, rock, ambient, jazz, synthwave, indie pop, hip-hop, country, metal, EDM, folk, R&B, classical, blues
- **Moods covered**: happy, chill, intense, relaxed, focused, moody, energetic, nostalgic, melancholic, romantic, serene, sad
- **Limits**: The catalog is tiny and was built by hand. It skews heavily toward Western, English-language genres. Several genres have only 1 song (metal, classical, blues, EDM, folk, R&B), while lofi has 3. No real listening data was used — all songs and feature values are fictional.

---

## 4. Algorithm Summary

Think of it like a point system at a talent show. Each song "auditions" against your preferences, and a panel of judges awards points:

- **Genre judge** gives 2 points if the song's genre matches your favorite. Otherwise 0.
- **Mood judge** gives 1 point if the song's mood matches your current mood. Otherwise 0.
- **Energy judge** gives up to 2 points based on how close the song's energy is to your target. A perfect match gets 2 points; a complete mismatch gets 0. Songs closer to your target get more points.
- **Acoustic judge** gives 1 bonus point if you said you like acoustic music and the song is highly acoustic.

The maximum any song can score is 6 points. All 18 songs are scored this way, then sorted from highest to lowest. The top 5 are the recommendations.

---

## 5. Observed Behavior / Biases

**What works well**: When a user's preferences align cleanly with a genre that has multiple catalog entries, the system is accurate. The "Chill Lofi Study" profile scored the top three results between 5.90 and 5.96 out of 6.00, and all three were genuinely appropriate songs. The acoustic bonus adds a meaningful secondary filter that separates lofi (organic) from ambient (also low-energy but electronic).

**Bias 1 — Genre dominance**: The +2.0 genre bonus is always fixed. The energy score, by contrast, is rarely perfect — it only reaches 2.0 when a song's energy is exactly the user's target. This means genre almost always wins ties, even when the energy mismatch is severe. A test with a "Classical + Energetic" profile exposed this: *Morning Sonata* (energy 0.18, serene) ranked first for a user who asked for high-energy music at 0.9 — solely because it matched the genre label. The songs that actually fit the user's energy request ranked below it.

**Bias 2 — Catalog skew**: Lofi users have three genre matches to choose from. Metal, blues, and classical users each have one. A metal fan whose single metal song doesn't fit their mood ends up getting ranked pop and EDM songs as "recommendations." The system isn't wrong mathematically, but the results feel irrelevant.

**Bias 3 — Mood vocabulary lock-in**: Moods are matched as exact strings. "Energetic" and "intense" describe nearly identical feelings at high tempo, but a user requesting "energetic" will never receive mood credit for a song tagged "intense." This creates invisible gaps in coverage that have nothing to do with actual musical similarity.

---

## 6. Evaluation Process

Six user profiles were tested — three typical, three adversarial — plus one weight-shift experiment.

**High-Energy Pop** (`genre=pop, mood=happy, energy=0.8`): Sunrise City ranked #1 with 4.96/6.00 — a correct, satisfying result. Gym Hero at #2 was a small surprise; it's tagged "intense" not "happy," but its pop genre and near-target energy (0.93) gave it enough points to beat all non-pop songs. This confirmed that genre weight is powerful enough to keep "close-but-wrong-mood" pop songs above "perfect-mood-wrong-genre" songs.

**Chill Lofi Study** (`genre=lofi, mood=chill, energy=0.4, likes_acoustic=True`): All three lofi songs landed in the top 3 with scores above 5.0 / 6.00. This was the most accurate result. The acoustic bonus meaningfully separated them from ambient songs (also quiet and organic but wrong genre).

**Deep Intense Rock** (`genre=rock, mood=intense, energy=0.92`): Storm Runner was correctly #1. But Gym Hero (pop) ranked #2 ahead of Iron Cathedral (metal), both with the same mood. Gym Hero won because its energy (0.93) was 0.01 closer to the target than Iron Cathedral (0.96). A real rock fan would not prefer pop over metal — this was the clearest sign that genre weight needs to be heavier relative to small energy differences.

**Conflicting: Classical + Energetic** (`genre=classical, mood=energetic, energy=0.9, likes_acoustic=True`): The system recommended Morning Sonata at #1 — a nearly silent classical piece — over Block Party Anthem and Signal Burst, which both matched the user's mood and energy. This is the adversarial result that most clearly shows the genre-dominance flaw.

**Unknown Genre: kpop**: With no genre matches in the catalog, the system fell back to mood and energy. Rooftop Lights (indie pop, happy, energy=0.76) ranked first with 2.98 — a reasonable fallback. The system degraded gracefully.

**Extreme Low Energy** (`genre=folk, mood=melancholic, energy=0.05, likes_acoustic=True`): Hollow Road scored 5.62/6.00 with four dimensions aligning. The energy formula worked correctly at the floor — the lowest-energy songs in the catalog rose to the top.

**Weight experiment** (genre weight halved to 1.0, energy multiplier doubled to 4.0, same High-Energy Pop profile): Rooftop Lights moved from #3 to #2, displacing Gym Hero. Rooftop Lights has energy=0.76, which is closer to the target 0.8 than Gym Hero's 0.93. When energy precision mattered more, the more accurate song won. This confirmed that default weights favor broad category matching over precise vibe tuning.

---

## 7. Intended Use and Non-Intended Use

**This system is designed for:**

- Learning how content-based recommenders work
- Classroom exploration of scoring functions, weights, and bias
- Experimenting with how small weight changes affect ranked outputs
- Understanding why real-world recommendation systems need much more data

**This system should NOT be used for:**

- Actual music discovery for real users — the catalog is too small and fictional
- Any production or commercial context
- Drawing conclusions about what users "really want" — preferences were manually typed, not inferred from behavior
- Evaluating the quality of real songs or artists — all song names and artists are invented

---

## 8. Ideas for Improvement

- **Energy mismatch penalty**: if the energy gap between a song and the user's target is greater than 0.4, reduce the genre bonus proportionally. This would fix the "Classical + Energetic" problem without removing genre matching entirely.
- **Mood similarity groups**: instead of exact string matching, map related moods into clusters ("intense" ↔ "energetic", "chill" ↔ "relaxed" ↔ "serene") and award partial credit for near-misses.
- **Catalog diversity cap**: if the top-k results are all the same genre, swap the lowest-scoring one for the best-scoring song from a different genre. This prevents a lofi user from seeing only lofi results and never discovering something new.

---

## 9. Personal Reflection

**Biggest learning moment**: The adversarial "Classical + Energetic" test was the turning point. I expected the energy proximity formula to compete evenly with the genre bonus, since both can contribute up to 2.0 points. But a genre match always earns the full 2.0 automatically, while energy proximity almost never reaches 2.0 in practice — it only does when a song's energy is exactly the user's target. That asymmetry means the genre bonus effectively dominates in almost every tie. I had designed a system I thought was balanced, and a single bad test case proved it wasn't.

**How AI tools helped — and where I had to double-check**: The AI was useful for quickly suggesting profile designs (like the "conflicting preferences" adversarial idea) and for explaining why sorted() is preferable to .sort() in terms of mutability. But it generated the scoring formula without flagging the genre-dominance flaw — I only discovered that by actually running the profiles and inspecting the outputs. That was a good reminder that AI-generated code can be syntactically correct while still producing behavior you didn't intend. You have to run it, not just read it.

**What surprised me about simple algorithms**: Before this project I expected recommendations to feel mechanical and obviously wrong. What surprised me was how often the results felt right — especially for the "Chill Lofi Study" and "Extreme Low Energy" profiles, where four features aligned and the output was intuitively correct. It made me realize that real recommender systems probably aren't dramatically more complex in their core logic — the difference is the scale of data they learn from and the richness of the feature set, not some fundamentally different kind of math.

**What I'd try next**: I'd extend the catalog to 100+ songs and add a valence preference to the user profile. Valence (musical positivity) is what separates "happy chill" from "melancholic chill" — two moods that share the same genre and energy range but feel completely different. The current system treats them the same unless the mood label is an exact match, which it often isn't. Adding valence proximity as a fifth scoring dimension would make the recommendations feel more emotionally precise.
