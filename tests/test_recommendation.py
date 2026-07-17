"""Unit tests for the pure ranking logic in backend/recommendation.py.
"""

import numpy as np
import pytest

import recommendation as rec


class FakePoint:
    """Minimal stand-in for a Qdrant scored point."""

    def __init__(self, score, artist="", playlist_count=1, vector=None, song_id="s", track="t", track_uri="u"):
        self.score = score
        self.vector = vector
        self.payload = {
            "artist": artist,
            "playlist_count": playlist_count,
            "song_id": song_id,
            "track": track,
            "track_uri": track_uri,
        }


# Rocchio

def test_apply_rocchio_moves_toward_liked_and_normalizes():
    q = np.array([1.0, 0.0])
    liked = [np.array([0.0, 1.0])]
    out = rec.apply_rocchio(q, liked, [])
    assert out[1] > 0.0  # shifted toward the liked direction
    assert np.isclose(np.linalg.norm(out), 1.0)


def test_apply_rocchio_moves_away_from_disliked():
    q = np.array([1.0, 1.0])
    out = rec.apply_rocchio(q, [], [np.array([0.0, 1.0])])
    # Away from +y means the y component shrinks relative to x.
    assert out[0] > out[1]
    assert np.isclose(np.linalg.norm(out), 1.0)


def test_apply_rocchio_no_feedback_just_normalizes():
    q = np.array([3.0, 4.0])
    out = rec.apply_rocchio(q, [], [])
    assert np.allclose(out, [0.6, 0.8])


# popularity

def test_popularity_score_matches_formula_and_is_monotonic():
    assert rec.popularity_score(1) == pytest.approx(np.log1p(1) / 10.0)
    assert rec.popularity_score(1000) > rec.popularity_score(10) > rec.popularity_score(1)


# artist affinity

def test_artist_affinity_zero_without_profile():
    assert rec.artist_affinity("Drake", [1.0, 0.0], set(), {}) == 0.0


def test_artist_affinity_full_for_top_artist():
    boost = rec.artist_affinity("Drake", [1.0, 0.0], {"Drake"}, {"Drake": [1.0, 0.0]})
    assert boost == 1.0


def test_artist_affinity_soft_match_remap():
    # cosine == COSINE_FLOOR -> 0, cosine == 1 -> 1
    top = {"SomebodyElse"}
    at_floor = rec.artist_affinity("Other", [rec.COSINE_FLOOR, np.sqrt(1 - rec.COSINE_FLOOR**2)],
                                   top, {"a": [1.0, 0.0]})
    assert at_floor == pytest.approx(0.0, abs=1e-9)
    perfect = rec.artist_affinity("Other", [1.0, 0.0], top, {"a": [1.0, 0.0]})
    assert perfect == pytest.approx(1.0)


# composite scoring

def test_score_candidate_anonymous_weights():
    p = FakePoint(score=0.8, playlist_count=1)
    expected = rec.W_VIBE_ANON * 0.8 + rec.W_POPULARITY_ANON * rec.popularity_score(1)
    assert rec.score_candidate(p, set(), {}) == pytest.approx(expected)


def test_score_candidate_personalized_weights():
    p = FakePoint(score=0.8, artist="Drake", playlist_count=1, vector=[1.0, 0.0])
    expected = (rec.W_VIBE * 0.8
                + rec.W_POPULARITY * rec.popularity_score(1)
                + rec.W_ARTIST * 1.0)
    assert rec.score_candidate(p, {"Drake"}, {"Drake": [1.0, 0.0]}) == pytest.approx(expected)


def test_score_candidates_preserves_points():
    pts = [FakePoint(score=0.5), FakePoint(score=0.9)]
    scored = rec.score_candidates(pts, set(), {})
    assert [p for p, _ in scored] == pts


# MMR

def test_mmr_respects_per_artist_cap():
    scored = [(FakePoint(score=1.0 - i * 0.01, artist="A", vector=[float(i), 0.0]), 1.0 - i * 0.01)
              for i in range(5)]
    out = rec.mmr_select(scored, max_per_artist=2)
    assert len(out) == 2


def test_mmr_prefers_diverse_second_pick():
    c0 = FakePoint(score=0.90, artist="A", vector=[1.0, 0.0])
    c1 = FakePoint(score=0.89, artist="B", vector=[1.0, 0.0])
    c2 = FakePoint(score=0.85, artist="C", vector=[0.0, 1.0])
    scored = [(c0, 0.90), (c1, 0.89), (c2, 0.85)]
    out = rec.mmr_select(scored, mmr_lambda=0.7)
    ordered = [c for c, _ in out]
    assert ordered[0] is c0
    assert ordered[1] is c2


def test_mmr_caps_at_n_select():
    scored = [(FakePoint(score=0.5, artist=f"artist-{i}", vector=[float(i), 1.0]), 0.5)
              for i in range(30)]
    out = rec.mmr_select(scored, n_select=20)
    assert len(out) == 20
