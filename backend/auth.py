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
    from sklearn.cluster import KMeans

    session = sessions.get(session_id)
    if not session:
        return None
    
    sp = spotipy.Spotify(auth=session["access_token"])
    
    # Get top 50 tracks
    top_tracks = sp.current_user_top_tracks(
        limit=50, 
        time_range='medium_term'
    )

    if top_tracks is None or 'items' not in top_tracks:
        return None
    top_tracks = top_tracks['items']
    
    taste_embeddings = []
    
    for track in top_tracks:
        song_id = f"{track['artists'][0]['name']}:{track['name']}"
        
        # Look up in Qdrant
        results = qdrant_client.query_points(
            collection_name="spotify-mpd",
            query=[0.0] * 384,  # dummy vector
            query_filter=models.Filter(
                must=[models.FieldCondition(
                    key="song_id",
                    match=models.MatchValue(value=song_id)
                )]
            ),
            with_vectors=True,
            limit=1
        ).points
        
        if results:
            taste_embeddings.append(
                np.array(results[0].vector)
            )
    
    if not taste_embeddings:
        return None
    
    embeddings_matrix = np.array(taste_embeddings)
    
    # Cluster into taste modes — fewer clusters if few matched songs
    n_clusters = min(6, max(1, len(taste_embeddings) // 3))
    
    if n_clusters <= 1:
        # Not enough songs to cluster, fall back to average
        profile = np.mean(embeddings_matrix, axis=0)
        clusters = [profile / np.linalg.norm(profile)]
    else:
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        kmeans.fit(embeddings_matrix)
        # Normalize each cluster centroid
        clusters = []
        for center in kmeans.cluster_centers_:
            clusters.append((center / np.linalg.norm(center)).tolist())
    
    sessions[session_id]["taste_clusters"] = clusters
    # Keep legacy single profile as fallback
    profile = np.mean(embeddings_matrix, axis=0)
    sessions[session_id]["taste_profile"] = \
        (profile / np.linalg.norm(profile)).tolist()
    
    return sessions[session_id]["taste_clusters"]

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
