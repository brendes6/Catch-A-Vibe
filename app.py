import streamlit as st
from util import make_recommendations, get_all_songs
from oath import create_playlist, authorize
from PIL import Image
import io

st.set_page_config(page_title="Catch a Vibe", layout="wide")

# Add Spotify login button in top left
col1, col2 = st.columns([1, 5])
with col1:
    # Check if already authorized
    if "sp" in st.session_state and st.session_state.sp is not None:
        try:
            # Verify the connection is still valid
            st.session_state.sp.me()
            st.success("✓ Connected to Spotify")
        except:
            st.session_state.sp = None
            if st.button("Login with Spotify"):
                authorize()
    else:
        if st.button("Login with Spotify"):
            authorize()

st.title("Catch a Vibe")

st.markdown("""Generate a playlist from a vibe/title, image, or song.""")

# Initialize session state variables
if 'recs_df' not in st.session_state:
    st.session_state.recs_df = None

if 'playlist_name' not in st.session_state:
    st.session_state.playlist_name = None


tab1, tab2, tab3 = st.tabs(["Vibe/Title Prompt", "Song-based", "Image Upload"])

# Common function for displaying results
def display_recommendations(playlist_name, recs):
    st.markdown(f"### Recommendations for playlist: *{playlist_name}*")
    if recs.empty:
        st.warning("No recommendations found.")
        return
    columns = st.columns(2)
    for i, song in enumerate(recs['name_artist'].tolist()[:20]):
        columns[i % 2].markdown(f"🎵 {song}")

# Tab for vibe input
with tab1:
    vibe_input = st.text_input("Enter a vibe:", placeholder="e.g. nostalgic summer road trip songs")
    if st.button("Get Recommendations from Vibe", key="vibe"):
        if vibe_input:
            st.session_state.recs_df, st.session_state.playlist_name = make_recommendations(vibe=vibe_input)
            display_recommendations(st.session_state.playlist_name, st.session_state.recs_df)
        else:
            st.warning("Please enter a vibe.")

# Tab for song input
with tab2:
    song_input = st.selectbox("Select a song to get songs with a similar vibe:", get_all_songs(), placeholder="Select a song", index=None)
    if st.button("Get Recommendations from Song", key="song"):
        if song_input:
            st.session_state.recs_df, st.session_state.playlist_name = make_recommendations(song=song_input)
            display_recommendations(st.session_state.playlist_name, st.session_state.recs_df)
        else:
            st.warning("Please enter a song name.")

# Tab for image input
with tab3:
    uploaded_file = st.file_uploader("Upload an image (e.g. album cover, mood photo)", type=["jpg", "jpeg", "png"])
    if uploaded_file and st.button("Get Recommendations from Image", key="image"):
        # Process image, pass into make_recommendations
        image_bytes = uploaded_file.read()
        image = Image.open(io.BytesIO(image_bytes))
        st.session_state.recs_df, st.session_state.playlist_name = make_recommendations(image=image)
        display_recommendations(st.session_state.playlist_name, st.session_state.recs_df)

# If a playlist is created, allow the user to save it to their Spotify account
if st.session_state.recs_df is not None:
    if st.button("Save this playlist to Spotify"):
        if create_playlist(st.session_state.recs_df, st.session_state.playlist_name):
            st.success("Playlist created successfully!")
        else:
            st.error("Failed to create playlist.")
