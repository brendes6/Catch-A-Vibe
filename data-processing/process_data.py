import json
import logging
import os
import hashlib
from collections import defaultdict

import numpy as np
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("catch_a_vibe.data")

DATA_DIR = "./mpd-dataset"
BATCH_SIZE = 500
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "spotify-mpd")

def load_slices(data_dir, max_slices=None):
    song_to_playlists = defaultdict(list)
    song_metadata = {}

    slice_files = sorted([
        f for f in os.listdir(data_dir)
        if f.endswith('.json')
    ])
    if max_slices is not None:
        slice_files = slice_files[:max_slices]

    logger.info("Processing %d slices...", len(slice_files))
    
    for i, filename in enumerate(slice_files):
        with open(os.path.join(data_dir, filename)) as f:
            data = json.load(f)
        
        for playlist in data['playlists']:
            title = playlist['name'].strip().lower()
            if not title:
                continue
            for track in playlist['tracks']:
                song_id = f"{track['artist_name']}:{track['track_name']}"
                song_to_playlists[song_id].append(title)

                if song_id not in song_metadata:
                    song_metadata[song_id] = {
                        "track_uri": track['track_uri'],
                        "artist": track['artist_name'],
                        "track": track['track_name'],
                        "album": track['album_name']
                    }
        
        del data
        
        if i % 20 == 0:
            logger.info(
                "Slice %d/%d — %d unique songs so far",
                i + 1, len(slice_files), len(song_to_playlists),
            )
    
    return song_to_playlists, song_metadata

def compute_song_vectors(song_to_playlists):
    model = TextEmbedding()
    
    # Get all unique playlist titles
    all_titles = list(set(
        title 
        for titles in song_to_playlists.values() 
        for title in titles
    ))
    
    logger.info("Embedding %d unique playlist titles...", len(all_titles))

    # Embed in batches
    title_to_embedding = {}
    titles_list = list(all_titles)
    
    for i in range(0, len(titles_list), BATCH_SIZE):
        batch = titles_list[i:i+BATCH_SIZE]
        embeddings = list(model.embed(batch))
        for title, emb in zip(batch, embeddings):
            title_to_embedding[title] = np.array(emb)
        
        if i % 5000 == 0:
            logger.info("Embedded %d/%d titles", i, len(titles_list))
    
    # Compute song vectors
    logger.info("Computing song vectors...")
    song_vectors = {}
    
    for song_id, playlist_titles in song_to_playlists.items():
        embs = [title_to_embedding[t] for t in playlist_titles 
                if t in title_to_embedding]
        if embs:
            vec = np.mean(embs, axis=0)
            song_vectors[song_id] = vec / np.linalg.norm(vec)
    
    logger.info("Computed %d song vectors", len(song_vectors))
    return song_vectors

def _stable_point_id(song_id: str) -> int:
    """Deterministic 63-bit point id for a song.

    Python's built-in hash() is salted per process (PYTHONHASHSEED), so the
    same song got a different id on every run, which breaks idempotent
    re-uploads (you'd insert duplicates instead of overwriting). Hashing with
    md5 makes the id stable across runs.
    """
    digest = hashlib.md5(song_id.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2**63)


def upload_to_qdrant(song_vectors, song_metadata, song_to_playlists):
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

    # Get vector dimension from first entry
    dim = len(next(iter(song_vectors.values())))

    # (Re)create the collection. recreate_collection is deprecated, so we
    # explicitly drop-if-exists then create.
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    songs = list(song_vectors.items())
    logger.info("Uploading %d songs to Qdrant collection '%s'...", len(songs), COLLECTION_NAME)

    for i in range(0, len(songs), BATCH_SIZE):
        batch = songs[i:i+BATCH_SIZE]

        points = [
            PointStruct(
                id=_stable_point_id(song_id),
                vector=vector.tolist(),
                payload={
                    "song_id": song_id,
                    "artist": song_metadata[song_id]["artist"],
                    "track": song_metadata[song_id]["track"],
                    "album": song_metadata[song_id]["album"],
                    "track_uri": song_metadata[song_id]["track_uri"],
                    "playlist_count": len(song_to_playlists[song_id])
                }
            )
            for song_id, vector in batch
        ]

        client.upsert(collection_name=COLLECTION_NAME, points=points)

        if i % 5000 == 0:
            logger.info("Uploaded %d/%d songs", i, len(songs))

    logger.info("Done - uploaded %d songs to '%s'", len(songs), COLLECTION_NAME)

if __name__ == "__main__":
    song_to_playlists, song_metadata = load_slices(DATA_DIR)
    song_vectors = compute_song_vectors(song_to_playlists)
    upload_to_qdrant(song_vectors, song_metadata, song_to_playlists)