import spotipy
from spotipy.oauth2 import SpotifyOAuth
import streamlit as st

SCOPE= ["user-library-read", "playlist-modify-public"]

def authorize():
    sp_auth = SpotifyOAuth(scope=SCOPE, client_id=st.secrets["client_id"],
                                                    client_secret=st.secrets["client_secret"],
                                                    redirect_uri=st.secrets["redirect_uri"],
                                                    open_browser=False)
        
    if "sp" not in st.session_state:
        st.session_state.sp = None

    query_params = st.query_params
    print(query_params) 
    code = query_params.get("code", [None])[0]
    print(code)

    if code:
        token_info = sp_auth.get_access_token(code)
        access_token = token_info["access_token"]
        st.session_state.sp = spotipy.Spotify(auth=access_token)
        st.success("Logged in with Spotify!")
        return True
    else:
        return False

# Use OAth to create a playlist for the user
def create_playlist(df, playlist_name):
    try:
        if st.session_state.sp is None:
            st.error("Please log in with Spotify first.")
            return False
        
        sp = st.session_state.sp

        song_ids = df['track_id'][:30].tolist()

        playlist = sp.user_playlist_create(user=sp.me()['id'], name=playlist_name, public=True)
        sp.user_playlist_add_tracks(user=sp.me()['id'], playlist_id=playlist['id'], tracks=song_ids)

        return True
    except Exception as e:
        st.error(f"Failed to create playlist: {str(e)}")
        return False