# directions.py
from fastembed import TextEmbedding
import numpy as np

def compute_directions(model):
    directions = {}
    
    pairs = {
        "energy": (
            ["high energy workout", "hype beast", "turn up",
             "gym motivation", "aggressive", "pump up"],
            ["sad girl hours", "rainy day", "slow mellow",
             "sleepy acoustic", "soft and slow", "melancholy"]
        ),
        "mood": (
            ["feel good vibes", "happy summer", "good times",
             "positive energy", "sunny day", "party"],
            ["heartbreak", "crying in the car", "late night sadness",
             "missing you", "emotional", "depressing"]
        ),
        "intensity": (
            ["metal workout", "rage mode", "beast mode",
             "hard rap", "aggressive", "intense"],
            ["meditation", "peaceful morning", "zen",
             "ambient study", "soft background", "tranquil"]
        )
    }
    
    for name, (positive, negative) in pairs.items():
        pos_embs = list(model.embed(positive))
        neg_embs = list(model.embed(negative))
        
        direction = (np.mean(pos_embs, axis=0) - 
                    np.mean(neg_embs, axis=0))
        directions[name] = direction / np.linalg.norm(direction)
    
    return directions