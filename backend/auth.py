from typing import Dict, Any
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import uuid 
import numpy as np
from dotenv import load_dotenv
from qdrant_client import models

load_dotenv()

# Simple in-memory session store
#TODO: Replace with redis for production
sessions = {}

def get_auth_url() -> str:
    """Get url to send to frontend for Spotify OAuth"""
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope="user-top-read user-library-read playlist-modify-public"
    )
    return sp_oauth.get_authorize_url()

def exchange_code(code: str) -> str:
    """Exchange the code for a session id"""
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope="user-top-read user-library-read playlist-modify-public"
    )
    token_info = sp_oauth.get_access_token(code)
    
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "access_token": token_info["access_token"],
        "refresh_token": token_info["refresh_token"]
    }
    return session_id

def build_taste_profile(session_id: str, qdrant_client) -> Dict[str, Any]:
    """Build a taste profile for the user based on their top artists"""

    # Get user session
    session = sessions.get(session_id)
    if not session:
        raise ValueError("Session not found")
    
    # Instantiate spotipy client
    sp = spotipy.Spotify(auth=session["access_token"])
    
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
    
    # Store everything in the session
    sessions[session_id]["top_artist_names"] = list(top_artist_names)
    sessions[session_id]["artist_vectors"] = artist_vectors
    
    # Log number of artist matches
    print(f"[Taste Profile] {len(top_artist_names)} top artists, "
          f"{len(artist_vectors)} matched in Qdrant")
    
    return {
        "top_artists": list(top_artist_names),
        "artist_vectors_count": len(artist_vectors)
    }

def save_playlist(session_id: str, track_uris: list[str], playlist_name: str) -> str | None:
    """Save a playlist to the user's Spotify account"""
    sp = spotipy.Spotify(auth=sessions[session_id]["access_token"])
    
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
