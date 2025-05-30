import spotipy
from spotipy.oauth2 import SpotifyOAuth
import streamlit as st
import secrets

SCOPE = ["user-library-read", "playlist-modify-public"]

def authorize():
    try:
        # Generate a random state parameter for security
        if 'oauth_state' not in st.session_state:
            st.session_state.oauth_state = secrets.token_urlsafe(16)

        sp_auth = SpotifyOAuth(scope=SCOPE, 
                              client_id=st.secrets["client_id"],
                              client_secret=st.secrets["client_secret"],
                              redirect_uri=st.secrets["redirect_uri"],
                              open_browser=False,
                              state=st.session_state.oauth_state)
        
        if "sp" not in st.session_state:
            st.session_state.sp = None

        # Check if we have a code in the URL
        query_params = st.query_params
        code = query_params.get("code", [None])[0]
        state = query_params.get("state", [None])[0]

        # Verify state parameter matches
        if state and state != st.session_state.oauth_state:
            st.error("Invalid state parameter. Please try logging in again.")
            return False

        if code:
            try:
                # We have a code, exchange it for a token
                token_info = sp_auth.get_access_token(code)
                if not token_info:
                    st.error("Failed to get access token")
                    return False

                access_token = token_info["access_token"]
                st.session_state.sp = spotipy.Spotify(auth=access_token)
                
                # Verify the connection
                try:
                    st.session_state.sp.me()
                    # Clear the state after successful authorization
                    st.session_state.oauth_state = None
                    return True
                except Exception as e:
                    st.error(f"Failed to verify Spotify connection: {str(e)}")
                    return False
            except Exception as e:
                st.error(f"Error during token exchange: {str(e)}")
                # Clear the state on error
                st.session_state.oauth_state = None
                return False
        else:
            # No code, generate the authorization URL
            auth_url = sp_auth.get_authorize_url()
            st.markdown(f'<a href="{auth_url}" target="_self">Click here to authorize with Spotify</a>', unsafe_allow_html=True)
            return False
            
    except Exception as e:
        st.error(f"Authorization failed: {str(e)}")
        # Clear the state on error
        st.session_state.oauth_state = None
        return False

# Use OAth to create a playlist for the user
def create_playlist(df, playlist_name):
    try:
        if st.session_state.sp is None:
            st.error("Please log in with Spotify first.")
            return False
        
        sp = st.session_state.sp
        
        # Verify we have a valid connection
        try:
            user = sp.me()
        except Exception as e:
            st.error(f"Spotify connection lost: {str(e)}")
            return False

        song_ids = df['track_id'][:30].tolist()
        
        # Create the playlist
        try:
            playlist = sp.user_playlist_create(user=user['id'], name=playlist_name, public=True)
        except Exception as e:
            st.error(f"Failed to create playlist: {str(e)}")
            return False

        # Add tracks to the playlist
        try:
            sp.user_playlist_add_tracks(user=user['id'], playlist_id=playlist['id'], tracks=song_ids)
        except Exception as e:
            st.error(f"Failed to add tracks to playlist: {str(e)}")
            return False

        return True
    except Exception as e:
        st.error(f"Unexpected error in create_playlist: {str(e)}")
        return False