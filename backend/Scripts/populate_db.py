from qdrant_client import QdrantClient, models
import pandas as pd
from fastembed import TextEmbedding
import ast
import numpy as np
from random import sample
import dotenv
import os

dotenv.load_dotenv()




client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API"),
    timeout=60,
)


embedding_size = 384


collection_name = "spotify_playlists"
if not client.collection_exists(collection_name=collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=embedding_size, distance=models.Distance.COSINE),
    )
    print(f"Collection '{collection_name}' created successfully.")


# Initialize the embedding model
embedding_model = TextEmbedding()

df = pd.read_csv("../Data/track_playlist_mapping.csv")

embeddings = []

df["genres"] = [[] for _ in range(len(df))]

for i, row in df.iloc[:4000].iterrows():

    if i%200 == 0:
        print(f"Processing row {i} of {len(df)} - {i/len(df)*100}%")

    playlist_titles = ast.literal_eval(row["playlist_titles"])
    if isinstance(playlist_titles, list) and playlist_titles:

        # Sample 8 playlist titles
        if len(playlist_titles) > 8:
            playlist_titles = sample(playlist_titles, 8)

        # Get song vector as average vector of playlist titles, then add to features
        song_vec = np.mean(list(embedding_model.embed(playlist_titles)), axis=0)
        embeddings.append(song_vec)

        # Store genres based on playlist titles
        if any("lofi" in name.lower() or "chillhop" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Lofi")
        if any("rock" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Rock")
        if any("pop" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Pop")
        if any("rap" in name.lower() or "hip hop" in name.lower() for name in playlist_titles):
            if any("lofi" in name.lower() or "chillhop" in name.lower() for name in playlist_titles):
                df.at[i, "genres"].append("Lofi")
            else:
                df.at[i, "genres"].append("Rap")
        if any("country" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Country")
        if any("indie" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Indie")
        if any("dance" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Dance")
        if any("metal" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Metal")
        if any("jazz" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Jazz")
        if any("blues" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Blues")
        if any("classical" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Classical")
        if any("electronic" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Electronic")
        if any("folk" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Folk")
        if any("r&b" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("R&B")
        if any("soul" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Soul")
        if any("funk" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Funk")
        if any("disco" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Disco")
        if any("reggae" in name.lower() for name in playlist_titles):
            df.at[i, "genres"].append("Reggae")

df["name_artist"] = df["name_artist"].apply(lambda x: ast.literal_eval(x))
df["name_artist"] = df["name_artist"].apply(lambda x: x[0])


# Prepare the points for upload to Qdrant
points = [
    models.PointStruct(
        id=i,  # Use a unique ID for each point
        vector=embeddings[i],
        payload={
            "genres": df.iloc[i]["genres"],
            "name_artist": df.iloc[i]["name_artist"],
        },
    )
    for i in range(len(embeddings))
]

# Upload the points to the collection

for i in range(1, len(points), 100):
    print(f"Uploading points {i} of {len(points)} - {i/len(points)*100}%")
    client.upsert(
        collection_name="spotify_playlists",
        wait=True,
        points=points[:i],
    )

print(f"Successfully uploaded {len(points)} points to Qdrant.")