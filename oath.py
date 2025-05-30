import spotipy
from spotipy.oauth2 import SpotifyOAuth
import streamlit as st

SCOPE = ["user-library-read", "playlist-modify-public"]

def create_playlist(df, playlist_name):
    try:
        # Initialize Spotify OAuth
        sp_auth = SpotifyOAuth(scope=SCOPE, 
                              client_id=st.secrets["client_id"],
                              client_secret=st.secrets["client_secret"],
                              redirect_uri=st.secrets["redirect_uri"],
                              open_browser=False)

        # Check if we have a code in the URL
        query_params = st.query_params
        code = query_params.get("code", [None])[0]

        if not code:
            # No code yet, show authorization link
            url = sp_auth.get_authorize_url()
            st.markdown(f'<a href="{url}" target="_self">Click here to authorize with Spotify</a>', unsafe_allow_html=True)
            st.info("Please authorize with Spotify to create your playlist.")
            return False

        # We have a code, exchange it for a token
        token_info = sp_auth.get_access_token(code)
        if not token_info:
            st.error("Failed to get access token")
            return False

        # Create Spotify client with the token
        sp = spotipy.Spotify(auth=token_info["access_token"])

        # Now create the playlist
        song_ids = df['track_id'][:30].tolist()
        playlist = sp.user_playlist_create(user=sp.me()['id'], name=playlist_name, public=True)
        sp.user_playlist_add_tracks(user=sp.me()['id'], playlist_id=playlist['id'], tracks=song_ids)

        # Clear the code from the URL to prevent re-running
        st.query_params.clear()
        return True

    except Exception as e:
        st.error(f"Failed to create playlist: {str(e)}")
        return False