import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import ast

# Load model and data globally
sentence_transformer = SentenceTransformer("clip-ViT-B-32")
df = pd.read_csv("Data/fullycleaned_data.csv")
features = [f"y{i}" for i in range(1, 513)]
df[features] = df[features].astype("float32")

feature_matrix = df[features].values
feature_matrix = feature_matrix / np.linalg.norm(feature_matrix, axis=1, keepdims=True)

image_df = pd.read_csv("Data/vibe_keywords.csv")
image_features = [f"y{i}" for i in range(1, 513)]

# Efficient cosine similarity
def cosine_sim(a, b):
    a = a / np.linalg.norm(a)
    return np.dot(b, a)


# Main recommendation function
def make_recommendations(vibe=None, image=None, song=None):

    # Assign vibe vector and playlist name based on input type
    if song:
        vibe_vector = get_song_vector(song)
        playlist_name = f"Playlist from song {song}"
    elif image:
        vibe_vector = sentence_transformer.encode(image)
        playlist_name = get_image_vibes(image)
    else:
        vibe_vector = sentence_transformer.encode(vibe)
        playlist_name = vibe

    # Calculate similarity between vibe vector and all songs' vectors
    similarities = cosine_sim(vibe_vector, feature_matrix)
    result_df = df.copy()
    result_df['overall_similarity'] = similarities

    # If vibe is provided, add a genre-based similarity score boost
    if vibe:
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
        

    return result_df.sort_values('overall_similarity', ascending=False)[['name_artist', 'track_id']], playlist_name

# Helper functions
def get_all_songs():
    return df['name_artist'].sort_values(ascending=True).unique()

def get_song_vector(song):
    return df[df['name_artist'] == song][features].values[0]

def get_image_vibes(image):
    vector = sentence_transformer.encode(image)
    similarities = cosine_sim(vector, image_df[image_features].values)
    image_df['overall_similarity'] = similarities
    result_df = image_df.sort_values('overall_similarity', ascending=False)[['vibe']]
    return result_df['vibe'].tolist()[0] + " " + result_df['vibe'].tolist()[1] + " mix"