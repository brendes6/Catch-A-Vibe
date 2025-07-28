from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http import models as rest
import pandas as pd

client = QdrantClient(url="https://efdf7f2f-35c8-48ca-aca9-dd02d594b151.europe-west3-0.gcp.cloud.qdrant.io:6333", api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.6B78SBanmDCoiiUNHiwaPP2Hu-JOkzUS2-GKUJgXz10")


embedding_df = pd.read_csv("../Data/fullycleaned_data.csv")

# Upload your songs
for i, row in embedding_df.iterrows():
    vector = row.iloc[3:].tolist()
    payload = {"track_id": row["track_id"], "name_artist": row["name_artist"]}
    client.upsert(collection_name="songs", points=[
        rest.PointStruct(id=i, vector=vector, payload=payload)
    ])