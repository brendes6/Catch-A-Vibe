import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from auth import (
    get_auth_url,
    exchange_code,
    build_taste_profile,
    save_playlist,
    validate_oauth_state,
)
import numpy as np
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import PayloadSchemaType, TextIndexParams, TokenizerType
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
from recommendation import mmr_select, score_candidates
from redis_store import session_store
from observability import (
    PrometheusMiddleware,
    configure_logging,
    metrics_endpoint,
    stage_timer,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("catch_a_vibe")

COLLECTION_NAME = "spotify-mpd"

# Browser origins allowed to call this API. Defaults to list of allowed origins
# if none in environment variables, the default list is used.
DEFAULT_ALLOWED_ORIGINS = [
    "https://catch-a-vibe-six.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]


def get_allowed_origins() -> list[str]:
    """Get allowed origins overrides from env var, or return default list"""
    raw = os.getenv("ALLOWED_ORIGINS")
    if raw:
        parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
        if parsed:
            return parsed
    return DEFAULT_ALLOWED_ORIGINS


def ensure_payload_indexes(client: QdrantClient) -> None:
    """Create the payload indexes needed for filtered search.

    Schema-based indexes are either set or updated on each call,
    called on each server startup.
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

    Loads embedding model and starts Qdrant client only on app startup,
    allowing for simpler testing and faster cold starts.
    """
    configure_logging()
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
app.add_middleware(PrometheusMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/metrics")
def metrics():
    """Prometheus metrics scrape endpoint."""
    return metrics_endpoint()


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
    if not validate_oauth_state(body.state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

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

    with stage_timer("embed"):
        # Embed query
        query_vector = np.array(list(embedding_model.embed([query]))[0])
    
    with stage_timer("retrieve"):
        # Generate candidates based on pure query and user personalization
        session_data = (session_store.get(session_id) or {}) if session_id else {}
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
    
    with stage_timer("rank"):
        # Composite scoring: query match, popularity, and personalization
        scored_candidates = score_candidates(candidates, top_artist_names, artist_vectors)
    
        # MMR diversity selection with a per-artist cap
        reranked = mmr_select(scored_candidates)
    
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
    if not session_store.exists(body.session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    url = save_playlist(body.session_id, body.track_uris, body.name)
    if url is None:
        raise HTTPException(status_code=502, detail="Failed to save playlist to Spotify")
    return SavePlaylistResponse(playlist_url=url)
