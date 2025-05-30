import spotipy
from spotipy.oauth2 import SpotifyOAuth
import streamlit as st

SCOPE= ["user-library-read", "playlist-modify-public"]

# Use OAth to create a playlist for the user
def create_playlist(df, playlist_name):
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE, client_id=st.secrets["client_id"],
                                                    client_secret=st.secrets["client_secret"],
                                                    redirect_uri=st.secrets["redirect_uri"],
                                                    open_browser=False))

        song_ids = df['track_id'][:30].tolist()

        playlist = sp.user_playlist_create(user=sp.me()['id'], name=playlist_name, public=True)
        sp.user_playlist_add_tracks(user=sp.me()['id'], playlist_id=playlist['id'], tracks=song_ids)

        return True
    except Exception as e:
        st.error(f"Failed to create playlist: {str(e)}")
        return False