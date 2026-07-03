import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import uuid
import numpy as np
from dotenv import load_dotenv
from qdrant_client import models

load_dotenv()

# Simple in-memory session store
sessions = {}

def get_auth_url():
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope="user-top-read user-library-read playlist-modify-public"
    )
    return sp_oauth.get_authorize_url()

def exchange_code(code: str):
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

def build_taste_profile(session_id: str, qdrant_client):

    session = sessions.get(session_id)
    if not session:
        return None
    
    sp = spotipy.Spotify(auth=session["access_token"])
    
    # ── 1. Pull the user's top artists from Spotify ──
    top_artists_data = sp.current_user_top_artists(
        limit=50,
        time_range='medium_term'
    )
    
    top_artist_names = set()
    if top_artists_data and 'items' in top_artists_data:
        for artist in top_artists_data['items']:
            top_artist_names.add(artist['name'])
    
    # ── 2. For each top artist, fetch their songs from Qdrant ──
    #    and compute an average "artist vector"
    artist_vectors = {}  # {artist_name: normalized_avg_vector}
    
    for artist_name in top_artist_names:
        try:
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
            
            if results:
                vecs = [np.array(p.vector) for p in results if p.vector]
                if vecs:
                    avg = np.mean(vecs, axis=0)
                    artist_vectors[artist_name] = (avg / np.linalg.norm(avg)).tolist()
        except Exception:
            continue  # Skip artists that cause query issues
    
    # ── 3. Store everything in the session ──
    sessions[session_id]["top_artist_names"] = list(top_artist_names)
    sessions[session_id]["artist_vectors"] = artist_vectors
    
    print(f"[Taste Profile] {len(top_artist_names)} top artists, "
          f"{len(artist_vectors)} matched in Qdrant")
    
    return {
        "top_artists": list(top_artist_names),
        "artist_vectors_count": len(artist_vectors)
    }

def save_playlist(session_id, track_uris, playlist_name):
    sp = spotipy.Spotify(auth=sessions[session_id]["access_token"])
    
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
