import pandas as pd
import numpy as np
import ast
import os
from fastembed import TextEmbedding

model = TextEmbedding()

current_script_dir = os.path.dirname(__file__)
data_relative_path = os.path.join(current_script_dir, "Data", "fullycleaned_data.csv")

df = pd.read_csv(data_relative_path)
features = [f"y{i}" for i in range(1, 385)]
df[features] = df[features].astype("float32")

feature_matrix = df[features].values
feature_matrix = feature_matrix / np.linalg.norm(feature_matrix, axis=1, keepdims=True)


# Efficient cosine similarity
def cosine_sim(a, b):
    a = a / np.linalg.norm(a)
    return np.dot(b, a)

def make_recommendations(vibe):
    """Generate song recommendations based on a vibe input.

    Input:
        vibe (str): A description of the desired vibe.
    Output:
        pd.DataFrame: A DataFrame containing recommended songs sorted by similarity.
    """

    # Get vector for inputted vibe
    vibe_vector = list(model.embed(vibe))[0]

    # Calculate similarity between vibe vector and all songs' vectors
    similarities = cosine_sim(vibe_vector, feature_matrix)
    result_df = df.copy()
    result_df['overall_similarity'] = similarities

    # Apply boosts to genre-specific vibes
    vibe_lower = vibe.lower()
    genre_keywords = ['rock', 'pop', 'rap', 'country', 'indie', 'dance', 'metal', 'jazz', 'electronic']
    for genre in genre_keywords:
        if genre in vibe_lower:
            result_df['overall_similarity'] += 0.3 * result_df['genres'].apply(
                lambda x: genre in [g.lower() for g in ast.literal_eval(x)]
            )
    
    if 'lofi' in vibe_lower or 'study' in vibe_lower:
        result_df['overall_similarity'] += 0.3 * result_df['genres'].apply(
            lambda x: 'lofi' in [g.lower() for g in ast.literal_eval(x)]
        )
    else:
        result_df['overall_similarity'] -= 0.3 * result_df['genres'].apply(
            lambda x: 'lofi' in [g.lower() for g in ast.literal_eval(x)]
        )
    

    return result_df.sort_values('overall_similarity', ascending=False)[['name_artist', 'track_id']]