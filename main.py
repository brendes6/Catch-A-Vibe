from fastapi import FastAPI
from util import make_recommendations

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Welcome!"}

@app.get("/recs")
def recs(vibe_input):
    result = make_recommendations(vibe=vibe_input)

    ret = {"songs":[]}

    for song in result[0]["name_artist"].tolist()[:20]:
        ret["songs"].append(song)
    
    return ret

