import numpy as np
import ast
import os
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
import pandas as pd
import dotenv

dotenv.load_dotenv()

embedding_model = TextEmbedding()
client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API"),
)
collection_name = "spotify_playlists"


def make_recommendations(vibe):
    """Generate song recommendations based on a vibe input.

    Input:
        vibe (str): A description of the desired vibe.
    Output:
        pd.DataFrame: A DataFrame containing recommended songs sorted by similarity.
    """

    query_embedding = list(embedding_model.embed([f"query: {vibe}"]))[0]

    # Search the Qdrant collection for similar embeddings
    search_results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=200,
        with_payload=True,  # Return the playlist metadata (title, id, etc.)
    )

    # Process and return the results
    recommendations = [
        {"name_artist": result.payload["name_artist"], "score": result.score, "genres": result.payload["genres"]}
        for result in search_results
    ]

    result_df = pd.DataFrame(recommendations)

    # Apply boosts to genre-specific vibes
    vibe_lower = vibe.lower()
    genre_keywords = ['rock', 'pop', 'rap', 'country', 'indie', 'dance', 'metal', 'jazz', 'electronic']
    for genre in genre_keywords:
        if genre in vibe_lower:
            result_df['score'] += 0.3 * result_df['genres'].apply(
                lambda x: genre in [g.lower() for g in x]
            )
    
    if 'lofi' in vibe_lower or 'study' in vibe_lower:
        result_df['score'] += 0.3 * result_df['genres'].apply(
            lambda x: 'lofi' in [g.lower() for g in x]
        )
    else:
        result_df['score'] -= 0.3 * result_df['genres'].apply(
            lambda x: 'lofi' in [g.lower() for g in x]
        )
    

    return result_df.sort_values('score', ascending=False)[['name_artist', 'score']]

if __name__ == "__main__":
    df = make_recommendations("chill")
    print(df.head(10))