
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import streamlit as st
import os
import datetime as dt
from PIL import Image
import io
from util import make_recommendations, get_all_songs


def get_token(oauth, code):

    token = oauth.get_access_token(code, as_dict=False, check_cache=False)
    # remove cached token saved in directory
    os.remove(".cache")
    
    # return the token
    return token



def sign_in(token):
    sp = spotipy.Spotify(auth=token)
    return sp



def app_get_token():
    try:
        token = get_token(st.session_state["oauth"], st.session_state["code"])
    except Exception as e:
        st.error("An error occurred during token retrieval!")
        st.write("The error is as follows:")
        st.write(e)
    else:
        st.session_state["cached_token"] = token



def app_sign_in():
    try:
        sp = sign_in(st.session_state["cached_token"])
    except Exception as e:
        st.error("An error occurred during sign-in!")
        st.write("The error is as follows:")
        st.write(e)
    else:
        st.session_state["signed_in"] = True
        app_display_welcome()
        st.success("Sign in success!")
        
    return sp



def app_display_welcome():
    
    # import secrets from streamlit deployment
    cid = st.secrets["client_id"]
    csecret = st.secrets["client_secret"]
    uri = st.secrets["redirect_uri"]

    # set scope and establish connection
    scopes = " ".join(["user-read-private",
                       "playlist-read-private",
                       "playlist-modify-private",
                       "playlist-modify-public",
                       "user-read-recently-played"])

    # create oauth object
    oauth = SpotifyOAuth(scope=scopes,
                         redirect_uri=uri,
                         client_id=cid,
                         client_secret=csecret)
    # store oauth in session
    st.session_state["oauth"] = oauth

    # retrieve auth url
    auth_url = oauth.get_authorize_url()
    
    # this SHOULD open the link in the same tab when Streamlit Cloud is updated
    # via the "_self" target
    link_html = " <a target=\"_self\" href=\"{url}\" >{msg}</a> ".format(
        url=auth_url,
        msg="Click me to authenticate!"
    )

    basic_link_html = " <a target=\"_self\" href=\"{url}\" >{msg}</a> ".format(
        url="https://catch-a-vibe-demo.streamlit.app",
        msg="Click me to go to skip the authentication and go to the demo app!"
    )
    

    st.title("Catch a Vibe")

    if not st.session_state["signed_in"]:
        st.markdown(link_html, unsafe_allow_html=True)
        st.markdown(basic_link_html, unsafe_allow_html=True)
        
        
def app(sp):
    
    # Common function for displaying results
    def display_recommendations(playlist_name, recs):
        st.markdown(f"### Recommendations for playlist: *{playlist_name}*")
        if recs.empty:
            st.warning("No recommendations found.")
            return
        columns = st.columns(2)
        for i, song in enumerate(recs['name_artist'].tolist()[:20]):
            columns[i % 2].markdown(f"🎵 {song}")


    tab1, tab2, tab3 = st.tabs(["Vibe/Title Prompt", "Song-based", "Image Upload"])

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

   
if "signed_in" not in st.session_state:
    st.session_state["signed_in"] = False
if "cached_token" not in st.session_state:
    st.session_state["cached_token"] = ""
if "code" not in st.session_state:
    st.session_state["code"] = ""
if "oauth" not in st.session_state:
    st.session_state["oauth"] = None

url_params = st.query_params

# attempt sign in with cached token
if st.session_state["cached_token"] != "":
    sp = app_sign_in()
# if no token, but code in url, get code, parse token, and sign in
elif "code" in url_params:
    # all params stored as lists, see doc for explanation
    st.session_state["code"] = url_params["code"][0]
    app_get_token()
    sp = app_sign_in()
# otherwise, prompt for redirect
else:
    app_display_welcome()
    

if st.session_state["signed_in"]:
    app(sp)