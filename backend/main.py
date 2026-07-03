from backend.directions import compute_directions
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.auth import get_auth_url, exchange_code, build_taste_profile, save_playlist, sessions
import numpy as np
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from dotenv import load_dotenv
import os
import time

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
from qdrant_client.http.models import PayloadSchemaType, TextIndexParams, TokenizerType
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

for text_field in ["artist", "track"]:
    try:
        qdrant_client.create_payload_index(
            collection_name="spotify-mpd",
            field_name=text_field,
            field_schema=TextIndexParams(
                type="text",
                tokenizer=TokenizerType.WORD,
                min_token_len=2,
                max_token_len=20,
                lowercase=True
            ),
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
    from qdrant_client.http import models
    query = body["query"]
    session_id = body.get("session_id")
    liked_songs = body.get("liked_songs", [])
    disliked_songs = body.get("disliked_songs", [])
    
    # Embed query
    query_vector = np.array(
        list(embedding_model.embed([query]))[0]
    )
    
    # ── Apply Rocchio Feedback (Relevance Feedback) ──
    if liked_songs or disliked_songs:
        def fetch_song_vectors(song_ids):
            vecs = []
            for sid in song_ids:
                res = qdrant_client.query_points(
                    collection_name="spotify-mpd",
                    query=[0.0] * 384,
                    query_filter=models.Filter(
                        must=[models.FieldCondition(
                            key="song_id",
                            match=models.MatchValue(value=sid)
                        )]
                    ),
                    with_vectors=True,
                    limit=1
                ).points
                if res and res[0].vector:
                    vecs.append(np.array(res[0].vector))
            return vecs
            
        liked_vecs = fetch_song_vectors(liked_songs)
        disliked_vecs = fetch_song_vectors(disliked_songs)
        
        # Rocchio formula weights
        alpha, beta = 0.5, 0.5
        
        if liked_vecs:
            query_vector = query_vector + alpha * np.mean(liked_vecs, axis=0)
        if disliked_vecs:
            query_vector = query_vector - beta * np.mean(disliked_vecs, axis=0)
            
        query_vector = query_vector / np.linalg.norm(query_vector)
    
    # ── Stage 1: Multi-Source Candidate Generation ──
    session_data = sessions.get(session_id, {}) if session_id else {}
    top_artist_names = set(session_data.get("top_artist_names", []))
    artist_vectors = session_data.get("artist_vectors", {})
    
    query_list = query_vector.tolist()
    pop_filter = models.FieldCondition(
        key="playlist_count",
        range=models.Range(gte=100)
    )
    
    # Retrieval A: Pure vibe search
    result_a = qdrant_client.query_points(
        collection_name="spotify-mpd",
        query=query_list,
        query_filter=models.Filter(must=[pop_filter]),
        limit=30,
        with_payload=True,
        with_vectors=True
    )
    
    # Retrieval B: Personalized — same vibe, but only from user's top artists
    result_b_points = []
    if top_artist_names:
        result_b = qdrant_client.query_points(
            collection_name="spotify-mpd",
            query=query_list,
            query_filter=models.Filter(
                must=[pop_filter],
                should=[
                    models.FieldCondition(
                        key="artist",
                        match=models.MatchText(text=name)
                    )
                    for name in top_artist_names
                ]
            ),
            limit=20,
            with_payload=True,
            with_vectors=True
        )
        result_b_points = result_b.points
    
    # Merge and deduplicate by point ID
    seen_ids = set()
    candidates = []
    for point in list(result_a.points) + result_b_points:
        if point.id not in seen_ids:
            seen_ids.add(point.id)
            candidates.append(point)
    
    # ── Stage 2: Composite Scoring with Artist Affinity ──
    
    scored_candidates = []
    for c in candidates:
        base_vibe_score = c.score  # Cosine similarity from Qdrant
        
        # 1. Popularity (log-scaled)
        pop_count = c.payload.get("playlist_count", 1)
        pop_score = np.log1p(pop_count) / 10.0
        
        # 2. Artist affinity — the key personalization signal
        artist_boost = 0.0
        candidate_artist = c.payload.get("artist", "")
        
        if top_artist_names:
            # Direct match: candidate IS one of the user's top artists
            if candidate_artist in top_artist_names:
                artist_boost = 1.0
            elif artist_vectors and c.vector:
                # Soft match: candidate's vector is similar to a top artist's vector
                c_vec = np.array(c.vector)
                artist_sims = [
                    np.dot(c_vec, np.array(av))
                    for av in artist_vectors.values()
                ]
                best_sim = max(artist_sims)
                artist_boost = max(0.0, (best_sim - 0.6) / 0.4)
        
        # Composite score
        if top_artist_names:
            # Personalized: 50% vibe, 15% popularity, 35% artist affinity
            final_score = (0.50 * base_vibe_score +
                          0.15 * pop_score +
                          0.35 * artist_boost)
        else:
            # Anonymous: 75% vibe, 25% popularity
            final_score = 0.75 * base_vibe_score + 0.25 * pop_score
            
        scored_candidates.append((c, final_score))
    
    # ── Stage 3: MMR Diversity Selection ──
    # Instead of just taking top 20, iteratively select songs that are
    # both high-scoring AND different from songs already selected.
    # λ controls relevance vs diversity tradeoff (1.0 = pure relevance, 0.0 = pure diversity)
    mmr_lambda = 0.7
    n_select = 20
    
    # Pre-compute candidate vectors
    candidate_vecs = []
    for c, score in scored_candidates:
        if c.vector:
            candidate_vecs.append(np.array(c.vector))
        else:
            candidate_vecs.append(np.zeros(384))
    
    selected_indices = []
    remaining = list(range(len(scored_candidates)))
    artist_counts = {}  # Cap per-artist to prevent repetition
    max_per_artist = 3
    
    for _ in range(min(n_select, len(scored_candidates))):
        best_idx = None
        best_mmr = -float('inf')
        
        for i in remaining:
            # Enforce artist cap
            artist = scored_candidates[i][0].payload.get("artist", "")
            if artist_counts.get(artist, 0) >= max_per_artist:
                continue
            
            relevance = scored_candidates[i][1]  # Composite score
            
            # Max similarity to any already-selected song
            if selected_indices:
                max_sim = max(
                    np.dot(candidate_vecs[i], candidate_vecs[j])
                    for j in selected_indices
                )
            else:
                max_sim = 0.0
            
            mmr_score = mmr_lambda * relevance - (1 - mmr_lambda) * max_sim
            
            if mmr_score > best_mmr:
                best_mmr = mmr_score
                best_idx = i
        
        if best_idx is not None:
            selected_indices.append(best_idx)
            remaining.remove(best_idx)
            artist = scored_candidates[best_idx][0].payload.get("artist", "")
            artist_counts[artist] = artist_counts.get(artist, 0) + 1
    
    reranked = [scored_candidates[i] for i in selected_indices]
    
    return {
        "results": [
            {
                "song_id": c.payload.get("song_id"),
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