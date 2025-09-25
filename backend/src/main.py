from fastapi import FastAPI
from util import make_recommendations
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Welcome!"}

@app.get("/recs")
def recs(vibe_input):
    """Generate song recommendations based on a vibe input.

    Input:
        vibe_input (str): A description of the desired vibe.
    Output:
        ret (dict): A dictionary containing the recommended songs.
    """
    # Call our FastEmbed-based recommendation engine
    result = make_recommendations(vibe=vibe_input)

    ret = {"songs":[]}

    for song in result["name_artist"].tolist()[:20]:
        ret["songs"].append(song)
    
    return ret

