import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from auth import get_auth_url, exchange_code, build_taste_profile, save_playlist, sessions
import numpy as np
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import PayloadSchemaType, TextIndexParams, TokenizerType
from dotenv import load_dotenv

from schemas import (
    AuthCallbackRequest,
    AuthCallbackResponse,
    HealthResponse,
    LoginResponse,
    RecommendRequest,
    RecommendResponse,
    SavePlaylistRequest,
    SavePlaylistResponse,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("catch_a_vibe")

COLLECTION_NAME = "spotify-mpd"


def ensure_payload_indexes(client: QdrantClient) -> None:
    """Create the payload indexes needed for filtered search.

    Idempotent: re-creating an existing index is a no-op error we can ignore,
    so this is safe to run on every startup.
    """
    for field, schema in [("song_id", PayloadSchemaType.KEYWORD),
                          ("playlist_count", PayloadSchemaType.INTEGER)]:
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field,
                field_schema=schema,
            )
        except Exception as exc:
            logger.debug("Skipping payload index for %s: %s", field, exc)

    for text_field in ["artist", "track"]:
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=text_field,
                field_schema=TextIndexParams(
                    type="text",
                    tokenizer=TokenizerType.WORD,
                    min_token_len=2,
                    max_token_len=20,
                    lowercase=True
                ),
            )
        except Exception as exc:
            logger.debug("Skipping text index for %s: %s", text_field, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize heavy resources once on startup instead of at import time.

    Loading the embedding model and reaching out to Qdrant at import made the
    module impossible to import for tests without live credentials and slowed
    cold starts. Doing it here keeps import side-effect free.
    """
    logger.info("Startup: connecting to Qdrant and loading embedding model")
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    ensure_payload_indexes(client)
    app.state.qdrant_client = client
    app.state.embedding_model = TextEmbedding()
    logger.info("Startup complete")
    try:
        yield
    finally:
        logger.info("Shutdown: closing Qdrant client")
        client.close()


app = FastAPI(title="Catch A Vibe API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_qdrant_client(request: Request) -> QdrantClient:
    """Dependency: the Qdrant client created during startup."""
    return request.app.state.qdrant_client


def get_embedding_model(request: Request) -> TextEmbedding:
    """Dependency: the embedding model loaded during startup."""
    return request.app.state.embedding_model


@app.get("/health", response_model=HealthResponse)
async def health(request: Request):
    """Liveness/readiness probe for Cloud Run (no network calls)."""
    ready = (
        getattr(request.app.state, "embedding_model", None) is not None
        and getattr(request.app.state, "qdrant_client", None) is not None
    )
    return HealthResponse(status="ok" if ready else "starting")


@app.get("/api/auth/login", response_model=LoginResponse)
async def login():
    """Return Spotify authorization URL"""
    return LoginResponse(url=get_auth_url())


@app.post("/api/auth/callback", response_model=AuthCallbackResponse)
async def callback(
    body: AuthCallbackRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
):
    """Handle Spotify callback and return session ID"""
    session_id = exchange_code(body.code)
    taste_profile = build_taste_profile(session_id, qdrant_client)
    return AuthCallbackResponse(
        session_id=session_id,
        has_taste_profile=taste_profile is not None,
    )

@app.post("/recommend", response_model=RecommendResponse)
async def recommend(
    body: RecommendRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    embedding_model: TextEmbedding = Depends(get_embedding_model),
):
    """Return recommendations based on query"""

    query = body.query
    session_id = body.session_id
    liked_songs = body.liked_songs
    disliked_songs = body.disliked_songs
    
    # Embed query
    query_vector = np.array(
        list(embedding_model.embed([query]))[0]
    )
    
    # If recommendation based on liked/disliked songs, apply Rocchio feedback
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
    
    # Generate candidates based on pure query and user personalization
    session_data = sessions.get(session_id, {}) if session_id else {}
    top_artist_names = set(session_data.get("top_artist_names", []))
    artist_vectors = session_data.get("artist_vectors", {})
    
    query_list = query_vector.tolist()
    pop_filter = models.FieldCondition(
        key="playlist_count",
        range=models.Range(gte=100)
    )
    
    # Retrieval 1: Pure query embedding search
    result_a = qdrant_client.query_points(
        collection_name="spotify-mpd",
        query=query_list,
        query_filter=models.Filter(must=[pop_filter]),
        limit=30,
        with_payload=True,
        with_vectors=True
    )
    
    # Retrieval 2: Personalized search filtering only based on user's top artists
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
    
    # Merge and deduplicate candidates retrieved
    seen_ids = set()
    candidates = []
    for point in list(result_a.points) + result_b_points:
        if point.id not in seen_ids:
            seen_ids.add(point.id)
            candidates.append(point)
    
    # Composite Scoring based on query match, popularity, and personalization
    scored_candidates = []
    for c in candidates:
        base_vibe_score = c.score
        
        # Score popularity by log of playlist count
        pop_count = c.payload.get("playlist_count", 1)
        pop_score = np.log1p(pop_count) / 10.0
        
        # Score artist affinity
        artist_boost = 0.0
        candidate_artist = c.payload.get("artist", "")

        # If an artist is in user's top 50 artists, boost score by 1.0
        # Else, check if embedding is similar to any top artist embeddings
        # via cosine similarity scale 0.0 -> 1.0
        if top_artist_names:
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
        
        # Composite score based on 
        # 50% query match, 15% popularity, 35% artist affinity
        if top_artist_names:
            final_score = (0.50 * base_vibe_score +
                          0.15 * pop_score +
                          0.35 * artist_boost)
        else:
            # If no personalization available, use 75% query match and 25% popularity
            final_score = 0.75 * base_vibe_score + 0.25 * pop_score
            
        scored_candidates.append((c, final_score))
    
    # MMR Diversity Selection
    # Instead of just taking top 20, iteratively select songs that are
    # both high-scoring AND different from songs already selected.
    # mmr_lambda controls relevance vs diversity tradeoff (1.0 = pure relevance, 0.0 = pure diversity)
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
    
    # Manually cap artist counts per playlist by 3
    artist_counts = {}
    max_per_artist = 3
    
    for _ in range(min(n_select, len(scored_candidates))):
        best_idx = None
        best_mmr = -float('inf')
        
        for i in remaining:
            # Enforce artist cap
            artist = scored_candidates[i][0].payload.get("artist", "")
            if artist_counts.get(artist, 0) >= max_per_artist:
                continue
            
            relevance = scored_candidates[i][1]
            
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

@app.post("/api/save-playlist", response_model=SavePlaylistResponse)
async def save_playlist_endpoint(body: SavePlaylistRequest):
    if body.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    url = save_playlist(body.session_id, body.track_uris, body.name)
    if url is None:
        raise HTTPException(status_code=502, detail="Failed to save playlist to Spotify")
    return SavePlaylistResponse(playlist_url=url)