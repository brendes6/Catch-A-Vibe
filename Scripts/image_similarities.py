from sentence_transformers import SentenceTransformer
import pandas as pd

model = SentenceTransformer('clip-ViT-B-32')

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


features = [f"y{i}" for i in range(1, 513)]
cols = ["vibe"] + features
df = pd.DataFrame(columns=cols)
df["vibe"] = vibe_keywords

df[features] = model.encode(df["vibe"])
df[features] = df[features].astype("float32")

df = df.drop_duplicates(subset="vibe")

df.to_csv("vibe_keywords.csv", index=False)


