"""Pure ranking logic for the recommendation pipeline.

These functions provide the logic of ranking as used by the recommendation pipeline
in the form of helper functions. They operate on pure vector/point inputs to allow
for independent loading and unit testing outside of Qdrant/Spotify/network dependencies.
"""

from __future__ import annotations

import numpy as np

VECTOR_DIM = 384

# Composite scoring weights when a personalized taste profile is available.
W_VIBE = 0.50
W_POPULARITY = 0.15
W_ARTIST = 0.35

# Fallback weights when there is no logged-in taste profile.
W_VIBE_ANON = 0.75
W_POPULARITY_ANON = 0.25

# Soft artist-affinity: cosine similarity is remapped from [COSINE_FLOOR, 1.0] 
# to [0, 1] so only genuinely close artists get a boost.
COSINE_FLOOR = 0.6

# MMR defaults.
MMR_LAMBDA = 0.7
N_SELECT = 20
MAX_PER_ARTIST = 3


def popularity_score(playlist_count: int) -> float:
    """Diminishing-returns popularity score from a song's playlist count."""
    return float(np.log1p(playlist_count) / 10.0)


def artist_affinity(candidate_artist, candidate_vector, top_artist_names, artist_vectors):
    """Boost for how well a candidate matches the user's taste.

    1.0 for a song by one of the user's top artists; otherwise a soft boost in
    [0, 1] based on cosine similarity to the nearest top-artist vector.
    """
    if not top_artist_names:
        return 0.0
    if candidate_artist in top_artist_names:
        return 1.0
    if artist_vectors and candidate_vector:
        c_vec = np.asarray(candidate_vector, dtype=float)
        best_sim = max(np.dot(c_vec, np.asarray(av, dtype=float)) for av in artist_vectors.values())
        return max(0.0, (best_sim - COSINE_FLOOR) / (1.0 - COSINE_FLOOR))
    return 0.0


def score_candidate(point, top_artist_names, artist_vectors) -> float:
    """Composite score for a single candidate point."""
    vibe = point.score
    pop = popularity_score(point.payload.get("playlist_count", 1))

    if top_artist_names:
        boost = artist_affinity(
            point.payload.get("artist", ""),
            point.vector,
            top_artist_names,
            artist_vectors,
        )
        return W_VIBE * vibe + W_POPULARITY * pop + W_ARTIST * boost

    return W_VIBE_ANON * vibe + W_POPULARITY_ANON * pop


def score_candidates(points, top_artist_names, artist_vectors):
    """Score every candidate, returning ``[(point, score), ...]``."""
    return [
        (p, score_candidate(p, top_artist_names, artist_vectors))
        for p in points
    ]


def mmr_select(
    scored_candidates,
    mmr_lambda=MMR_LAMBDA,
    n_select=N_SELECT,
    max_per_artist=MAX_PER_ARTIST,
    dim=VECTOR_DIM,
):
    """Maximal Marginal Relevance selection with a per-artist cap.

    Iteratively picks candidates that balance composite score (relevance)
    against similarity to already-selected songs (diversity), never exceeding
    manual cap 'max_per_artist' songs from any single artist.
    """
    candidate_vecs = [
        np.asarray(c.vector, dtype=float) if c.vector else np.zeros(dim)
        for c, _ in scored_candidates
    ]

    selected: list[int] = []
    remaining = list(range(len(scored_candidates)))
    artist_counts: dict[str, int] = {}

    for _ in range(min(n_select, len(scored_candidates))):
        best_idx = None
        best_mmr = -float("inf")

        for i in remaining:
            artist = scored_candidates[i][0].payload.get("artist", "")
            if artist_counts.get(artist, 0) >= max_per_artist:
                continue

            relevance = scored_candidates[i][1]
            max_sim = max(
                (float(np.dot(candidate_vecs[i], candidate_vecs[j])) for j in selected),
                default=0.0,
            )
            mmr_score = mmr_lambda * relevance - (1 - mmr_lambda) * max_sim

            if mmr_score > best_mmr:
                best_mmr = mmr_score
                best_idx = i

        if best_idx is None:
            # Every remaining candidate is artist-capped.
            break

        selected.append(best_idx)
        remaining.remove(best_idx)
        artist = scored_candidates[best_idx][0].payload.get("artist", "")
        artist_counts[artist] = artist_counts.get(artist, 0) + 1

    return [scored_candidates[i] for i in selected]
