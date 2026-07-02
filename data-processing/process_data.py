import json
import os
import numpy as np
from collections import defaultdict
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = "./mpd-dataset"
BATCH_SIZE = 500

def load_slices(data_dir, max_slices=200):
    song_to_playlists = defaultdict(list)
    song_metadata = {}

    slice_files = sorted([
        f for f in os.listdir(data_dir) 
        if f.endswith('.json')
    ])
    
    print(f"Processing {len(slice_files)} slices...")
    
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
            print(f"Slice {i+1}/{len(slice_files)} — "
                  f"{len(song_to_playlists)} unique songs so far")
    
    return song_to_playlists, song_metadata

def compute_song_vectors(song_to_playlists):
    model = TextEmbedding()
    
    # Get all unique playlist titles
    all_titles = list(set(
        title 
        for titles in song_to_playlists.values() 
        for title in titles
    ))
    
    print(f"Embedding {len(all_titles)} unique playlist titles...")
    
    # Embed in batches
    title_to_embedding = {}
    titles_list = list(all_titles)
    
    for i in range(0, len(titles_list), BATCH_SIZE):
        batch = titles_list[i:i+BATCH_SIZE]
        embeddings = list(model.embed(batch))
        for title, emb in zip(batch, embeddings):
            title_to_embedding[title] = np.array(emb)
        
        if i % 5000 == 0:
            print(f"Embedded {i}/{len(titles_list)} titles")
    
    # Compute song vectors
    print("Computing song vectors...")
    song_vectors = {}
    
    for song_id, playlist_titles in song_to_playlists.items():
        embs = [title_to_embedding[t] for t in playlist_titles 
                if t in title_to_embedding]
        if embs:
            vec = np.mean(embs, axis=0)
            song_vectors[song_id] = vec / np.linalg.norm(vec)
    
    print(f"Computed {len(song_vectors)} song vectors")
    return song_vectors

def upload_to_qdrant(song_vectors, song_metadata):
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    
    # Get vector dimension from first entry
    dim = len(next(iter(song_vectors.values())))
    
    # Recreate collection
    client.recreate_collection(
        collection_name=os.getenv("QDRANT_COLLECTION_NAME"),
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
    )
    
    songs = list(song_vectors.items())
    print(f"Uploading {len(songs)} songs to Qdrant...")
    
    for i in range(0, len(songs), BATCH_SIZE):
        batch = songs[i:i+BATCH_SIZE]
        
        points = [
            PointStruct(
                id=abs(hash(song_id)) % (2**63),
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
        
        client.upsert(collection_name=os.getenv("QDRANT_COLLECTION_NAME"), points=points)
        
        if i % 5000 == 0:
            print(f"Uploaded {i}/{len(songs)} songs")
    
    print("Done!")

if __name__ == "__main__":
    song_to_playlists, song_metadata = load_slices(DATA_DIR)
    song_vectors = compute_song_vectors(song_to_playlists)
    upload_to_qdrant(song_vectors, song_metadata)