import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time
import pandas as pd
from tqdm import tqdm
from collections import defaultdict
import streamlit as st

# Build a training set of tracks and the playlists they appear on
def build_playlist_training_set():
    # Initialize Spotify client
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=st.secrets["client_id"],
        client_secret=st.secrets["client_secret"]
    ))

    # Define vibe keywords
    vibe_keywords = [
    # General moods
    "happy", "joyful", "uplifting", "feel good",
    "sad", "melancholy", "heartbreak",
    "romantic", "lovestruck", "dreamy", "intimate", "passionate",
    "chill", "relaxed", "calm",
    "energetic", "hype", "pumped up", "intense", "powerful", "driving rhythm",
    "nostalgic", "throwback", 
    "angry", "frustrated", "edgy",

    # Genres
    "classic rock", "yacht rock", "modern rock", "punk rock", "metal", "grunge", "progressive rock", "psychedelic rock",
    "oldies rock and roll", "soft rock", "indie rock", "alt rock", "garage rock", 
    "mainstream pop", "indie pop", "sad pop", "dance pop", "bedroom pop", "dream pop", "synth pop", "power pop",
    "hip hop", "old school rap", "emo rap", "rap for studying", "conscious rap", "underground rap", "drill rap",
    "lofi", "lofi beats", "lofi chillhop", "jazz", "smooth jazz", "funk", "disco", "soul",
    "r&b", "blues", "folk", "indie folk", "folk rock", "country", "sad country", "country rock", "country pop",

    # Activity & Contexts
    "road trip", "late night drive", "driving at sunset", "highway tunes", "travel playlist",
    "study music", "focus beats", "concentration instrumental", "deep work instrumental", "no lyrics study",
    "gym workout", "running playlist", "cardio mix", "pre-game hype", "dance party",
    "cooking dinner", "brunch with friends", "dinner music", "hosting friends", "background music",
    "morning routine", "waking up", "coffee time",
    "night time", "evening chill", "unwinding", "sleepy time",
    "rainy day", "cozy winter morning", "fireplace songs", "indoor comfort",
    "summer beach day", "poolside chilling", "sunny afternoon", "outdoor fun",
    "urban exploring", "walking through the city", "driving through a vibrant city at midnight", "walking alone at night", "lonely desert highway",
    "campfire night", "acoustic session", 

    # Genre & Era Blends
    "classic rock", "70s rock anthems", "80s rock ballads", "90s grunge alternative", "modern rock hits",
    "hip hop essentials", "trap bangers", "melodic rap", "drill beats",
    "lofi chillhop", "lofi instrumental", "jazz lounge", "smooth jazz", 
    "soulful grooves", "r&b classics", "funk anthems", "disco party", "alternative rock",
    "country roads", "americana folk", "bluegrass jams", "western tunes",
    "electronic dance music", "deep house"
    ]



    # Store tracks_id's to playlist names
    track_to_playlists = defaultdict(list)
    track_to_nameartist = defaultdict(list)

    # Parameters for search
    max_playlists_per_vibe = 40
    max_tracks_per_playlist = 15

    # Search for playlists using tqdm
    for keyword in tqdm(vibe_keywords, desc="Searching playlists"):

        results = sp.search(q=keyword, type="playlist", limit=max_playlists_per_vibe)
        playlists = results.get("playlists", {}).get("items", [])

        # For each playlist, get tracks and store track_id's to playlist names
        for playlist in playlists:
            if playlist == None:
                continue
            playlist_id = playlist["id"]
            playlist_name = playlist["name"]

            tracks = sp.playlist_tracks(playlist_id, limit=max_tracks_per_playlist)["items"]
            for item in tracks:
                track = item.get("track")
                if not track: continue
                track_id = track.get("id")
                if not track_id: continue
                track_to_playlists[track_id].append(playlist_name)
                track_to_nameartist[track_id].append((f"{track['name']} - {track['artists'][0]['name']}"))
            
            time.sleep(0.5)  # Sleep to avoid rate limit

    # Store track_id's to playlist names and name_artist
    rows = []
    for track_id, playlist_titles in track_to_playlists.items():
        name_artist = track_to_nameartist[track_id]
        rows.append({
            "track_id": track_id,
            "playlist_titles": playlist_titles,
            "name_artist": name_artist
        })

    # Create dataframe
    df = pd.DataFrame(rows)
    df['playlist_count'] = df["playlist_titles"].apply(len)

    # Filter out songs with less than 2 playlists
    df = df[df["playlist_count"] > 2]

    # Save to csv
    df.to_csv("track_playlist_mapping.csv", index=False)


if __name__ == "__main__":
    build_playlist_training_set()