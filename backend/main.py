from backend.directions import compute_directions
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.auth import get_auth_url, exchange_code, build_taste_profile, save_playlist, sessions
import numpy as np
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from qdrant_client import QdrantClient
from fastembed import TextEmbedding

qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# Ensure payload indexes exist
from qdrant_client.http.models import PayloadSchemaType
for field, schema in [("song_id", PayloadSchemaType.KEYWORD),
                      ("playlist_count", PayloadSchemaType.INTEGER)]:
    try:
        qdrant_client.create_payload_index(
            collection_name="spotify-mpd",
            field_name=field,
            field_schema=schema,
        )
    except Exception:
        pass  # Index already exists

embedding_model = TextEmbedding()

direction_vectors = compute_directions(embedding_model)

@app.get("/api/auth/login")
async def login():
    return {"url": get_auth_url()}

@app.post("/api/auth/callback")
async def callback(body: dict):
    code = body["code"]
    session_id = exchange_code(code)
    taste_profile = build_taste_profile(session_id, qdrant_client)
    return {
        "session_id": session_id,
        "has_taste_profile": taste_profile is not None
    }

@app.post("/recommend")
async def recommend(body: dict):
    query = body["query"]
    session_id = body.get("session_id")
    direction = body.get("direction")
    strength = body.get("strength", 0.3)
    
    # Embed query
    query_vector = np.array(
        list(embedding_model.embed([query]))[0]
    )
    
    # Blend with closest taste cluster if authenticated
    if session_id and session_id in sessions:
        clusters = sessions[session_id].get("taste_clusters")
        if clusters:
            # Find which taste cluster is most relevant to this query
            similarities = [
                np.dot(query_vector, np.array(c))
                for c in clusters
            ]
            best_cluster = np.array(clusters[np.argmax(similarities)])
            # 70% query, 30% relevant taste cluster
            query_vector = (0.6 * query_vector + 
                          0.4 * best_cluster)
            query_vector = query_vector / np.linalg.norm(query_vector)
    
    # Apply embedding arithmetic if direction specified
    if direction and direction in direction_vectors:
        dir_vec = direction_vectors[direction]
        query_vector = query_vector + strength * dir_vec
        query_vector = query_vector / np.linalg.norm(query_vector)
    
    # Stage 1: retrieve top 50 (filter out obscure songs)
    from qdrant_client.http import models
    result = qdrant_client.query_points(
        collection_name="spotify-mpd",
        query=query_vector.tolist(),
        query_filter=models.Filter(
            must=[models.FieldCondition(
                key="playlist_count",
                range=models.Range(gte=100)
            )]
        ),
        limit=50,
        with_payload=True,
        with_vectors=True  # Important: We need the vectors for hyper-personalization scoring
    )
    candidates = result.points
    
    # Stage 2: Custom RecSys Scoring
    # Replaces the text cross-encoder with semantic + popularity + hyper-personalization scoring
    user_clusters = sessions.get(session_id, {}).get("taste_clusters", []) if session_id else []
    
    scored_candidates = []
    for c in candidates:
        base_vibe_score = c.score  # Cosine similarity to the blended query (from Qdrant)
        
        # 1. Popularity Boost (Log scale: 100 plays -> ~4.6, 10000 plays -> ~9.2)
        pop_count = c.payload.get("playlist_count", 1)
        pop_score = np.log1p(pop_count) / 10.0  # Normalize roughly to 0-1 range
        
        # 2. Hyper-Personalization Affinity
        # Does this song strongly match ANY of the user's specific taste clusters?
        personalization_boost = 0.0
        if user_clusters and c.vector:
            c_vec = np.array(c.vector)
            # Find the max similarity to any of the user's taste modes
            cluster_sims = [np.dot(c_vec, np.array(cluster)) for cluster in user_clusters]
            personalization_boost = max(cluster_sims)
            
        # 3. Final Weighted Score
        if user_clusters:
            # 50% Query Vibe, 20% Popularity, 30% User Affinity
            final_score = 0.5 * base_vibe_score + 0.2 * pop_score + 0.3 * personalization_boost
        else:
            # 80% Query Vibe, 20% Popularity
            final_score = 0.8 * base_vibe_score + 0.2 * pop_score
            
        scored_candidates.append((c, final_score))
    
    # Sort by our custom composite score
    reranked = sorted(scored_candidates, key=lambda x: x[1], reverse=True)[:20]
    
    return {
        "results": [
            {
                "artist": c.payload["artist"],
                "track": c.payload["track"],
                "track_uri": c.payload.get("track_uri"),
                "score": float(score)
            }
            for c, score in reranked
        ]
    }

@app.post("/api/save-playlist")
async def save_playlist_endpoint(body: dict):
    session_id = body["session_id"]
    track_uris = body["track_uris"]
    name = body.get("name", "Catch A Vibe Playlist")
    
    url = save_playlist(session_id, track_uris, name)
    if url is None:
        return {"error": "Failed to save playlist"}
    return {"playlist_url": url}