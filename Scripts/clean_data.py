import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
import ast
from random import sample

# Read playlist data
df = pd.read_csv("track_playlist_mapping.csv")

# Initialize sentence transformer
model = SentenceTransformer("clip-ViT-B-32")

# Initialize features
for i in range(1, 513):
    df[f"y{i}"] = 0

# Initialize genres
df["genres"] = [[] for _ in range(len(df))]

# Process each row
for i, row in df.iterrows():
    if i%200 == 0:
        print(f"Processing row {i} of {len(df)} - {i/len(df)*100}%")

    # ast.literal_eval to get playlist titles since they are stored as strings
    playlist_titles = ast.literal_eval(row["playlist_titles"])
    if isinstance(playlist_titles, list) and playlist_titles:

        # Sample 8 playlist titles
        if len(playlist_titles) > 8:
            playlist_titles = sample(playlist_titles, 8)

        # Get song vector as average vector of playlist titles, then add to features
        song_vec = np.mean([model.encode(title) for title in playlist_titles], axis=0)
        for j in range(1, 513):
            df.at[i, f"y{j}"] = song_vec[j-1]

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


# Since name_artist is a string containing a list of name_artist's, we need to convert it to a list and get the first name_artist
df["name_artist"] = df["name_artist"].apply(lambda x: ast.literal_eval(x))
df["name_artist"] = df["name_artist"].apply(lambda x: x[0])



# Drop playlist_titles since we don't need it anymore
df.drop(columns=["playlist_titles"], inplace=True)
df.drop_duplicates(subset=["name_artist"], inplace=True)

# Save to csv
df.to_csv("fullycleaned_data.csv", index=False)

