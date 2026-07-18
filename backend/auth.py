from typing import Dict, Any
import os
import time
import uuid
import logging

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler
import numpy as np
from dotenv import load_dotenv
from qdrant_client import models

from redis_store import session_store

load_dotenv()

logger = logging.getLogger("catch_a_vibe")

SPOTIFY_SCOPE = "user-top-read user-library-read playlist-modify-public"

def _build_oauth() -> SpotifyOAuth:
    """Build a SpotifyOAuth client from environment configuration.

    Uses an in-memory cache handler so tokens are never written to a local
    .cache file on the server; we persist them ourselves in the session store.
    """
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=SPOTIFY_SCOPE,
        cache_handler=MemoryCacheHandler(),
    )


def get_auth_url() -> str:
    """Get url to send to frontend for Spotify OAuth"""
    return _build_oauth().get_authorize_url()


def exchange_code(code: str) -> str:
    """Exchange the authorization code for a session id, storing tokens."""
    oauth = _build_oauth()
    # as_dict=False avoids a deprecation warning; the full token payload
    # (including refresh_token and expires_at) is read back from the cache.
    oauth.get_access_token(code, as_dict=False, check_cache=False)
    token_info = oauth.cache_handler.get_cached_token()

    session_id = str(uuid.uuid4())
    session_store.set(session_id, {
        "access_token": token_info["access_token"],
        "refresh_token": token_info["refresh_token"],
        "expires_at": token_info["expires_at"],
    })
    return session_id


def _get_access_token(session_id: str) -> str:
    """Return a valid access token for the session, refreshing if needed.

    Spotify access tokens expire after ~1 hour. Previously the stored
    refresh_token was never used, so any request made more than an hour after
    login (e.g. saving a playlist) failed with a 401. This refreshes the token
    on demand and updates the session in place.
    """
    session = session_store.get(session_id)
    if not session:
        raise ValueError("Session not found")

    if time.time() >= session.get("expires_at", 0):
        token_info = _build_oauth().refresh_access_token(session["refresh_token"])
        session["access_token"] = token_info["access_token"]
        session["expires_at"] = token_info["expires_at"]
        # Spotify only sometimes returns a rotated refresh token.
        if token_info.get("refresh_token"):
            session["refresh_token"] = token_info["refresh_token"]
        session_store.set(session_id, session)
        logger.info("Refreshed Spotify access token")

    return session["access_token"]


def _spotify_client(session_id: str) -> spotipy.Spotify:
    """Return a Spotify client backed by a valid (auto-refreshed) token."""
    return spotipy.Spotify(auth=_get_access_token(session_id))

def build_taste_profile(session_id: str, qdrant_client) -> Dict[str, Any]:
    """Build a taste profile for the user based on their top artists"""

    # Instantiate spotipy client (auto-refreshes the access token if expired)
    sp = _spotify_client(session_id)
    
    # Pull the user's top 50 artists from Spotify
    top_artists_data = sp.current_user_top_artists(
        limit=50,
        time_range='medium_term'
    )
    
    # Extract artist names from top artists data
    top_artist_names = set()
    if top_artists_data and 'items' in top_artists_data:
        for artist in top_artists_data['items']:
            top_artist_names.add(artist['name'])
    
    # For each top artist, fetch their songs from Qdrant and compute an average "artist vector"
    artist_vectors = {}
    
    for artist_name in top_artist_names:
        try:
            # Query qdrant for songs by the current artist
            results = qdrant_client.scroll(
                collection_name="spotify-mpd",
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(
                        key="artist",
                        match=models.MatchText(text=artist_name)
                    )]
                ),
                limit=30,
                with_vectors=True,
                with_payload=False
            )[0]
            
            # Compute the average vector for the current artist
            if results:
                vecs = [np.array(p.vector) for p in results if p.vector]
                if vecs:
                    avg = np.mean(vecs, axis=0)
                    artist_vectors[artist_name] = (avg / np.linalg.norm(avg)).tolist()
        except Exception:
            continue
    
    # Persist the taste profile back to the session
    session = session_store.get(session_id) or {}
    session["top_artist_names"] = list(top_artist_names)
    session["artist_vectors"] = artist_vectors
    session_store.set(session_id, session)
    
    # Log number of artist matches
    logger.info(
        "Taste profile built: %d top artists, %d matched in Qdrant",
        len(top_artist_names),
        len(artist_vectors),
    )
    
    return {
        "top_artists": list(top_artist_names),
        "artist_vectors_count": len(artist_vectors)
    }

def save_playlist(session_id: str, track_uris: list[str], playlist_name: str) -> str | None:
    """Save a playlist to the user's Spotify account"""
    sp = _spotify_client(session_id)
    
    # Get user id
    user_id = sp.current_user()
    if user_id is None or "id" not in user_id:
        return None
    user_id = user_id["id"]
    playlist = sp.user_playlist_create(user_id, playlist_name)
    if playlist is None or "id" not in playlist:
        return None
    playlist_id = playlist["id"]
    
    sp.playlist_add_items(playlist_id, track_uris)
    
    return playlist["external_urls"]["spotify"]
