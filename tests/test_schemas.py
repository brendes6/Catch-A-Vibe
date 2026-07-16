"""Validation tests for the Pydantic request models in backend/schemas.py.
"""

import pytest
from pydantic import ValidationError

import schemas


def test_recommend_request_rejects_empty_query():
    with pytest.raises(ValidationError):
        schemas.RecommendRequest(query="")


def test_recommend_request_defaults_to_empty_lists():
    req = schemas.RecommendRequest(query="late night drive")
    assert req.liked_songs == []
    assert req.disliked_songs == []
    assert req.session_id is None


def test_save_playlist_requires_track_uris():
    with pytest.raises(ValidationError):
        schemas.SavePlaylistRequest(session_id="abc", track_uris=[])


def test_save_playlist_has_default_name():
    req = schemas.SavePlaylistRequest(session_id="abc", track_uris=["spotify:track:1"])
    assert req.name == "Catch A Vibe Playlist"


def test_auth_callback_requires_code():
    with pytest.raises(ValidationError):
        schemas.AuthCallbackRequest(code="")
