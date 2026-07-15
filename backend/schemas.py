"""Pydantic request/response models for the Catch A Vibe API.

Centralizing these gives us automatic request validation (malformed bodies
return 422 instead of an unhandled KeyError -> 500) and self-documenting
responses in the generated OpenAPI schema.
"""

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Free-text vibe/playlist title")
    session_id: str | None = None
    liked_songs: list[str] = Field(default_factory=list)
    disliked_songs: list[str] = Field(default_factory=list)


class SongResult(BaseModel):
    song_id: str | None = None
    artist: str
    track: str
    track_uri: str | None = None
    score: float


class RecommendResponse(BaseModel):
    results: list[SongResult]


class AuthCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Spotify OAuth authorization code")


class AuthCallbackResponse(BaseModel):
    session_id: str
    has_taste_profile: bool


class LoginResponse(BaseModel):
    url: str


class SavePlaylistRequest(BaseModel):
    session_id: str
    track_uris: list[str] = Field(..., min_length=1)
    name: str = "Catch A Vibe Playlist"


class SavePlaylistResponse(BaseModel):
    playlist_url: str


class HealthResponse(BaseModel):
    status: str
