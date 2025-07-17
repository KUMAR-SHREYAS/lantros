import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
# Qdrant cloud configuration
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.yXrjU4jnZZlYc37tTB7QBNyIjZGbszeAsfyjJq_drN0"
QDRANT_URL = "https://577436df-ea24-47dc-b703-252fb680f34d.eu-west-1-0.aws.cloud.qdrant.io"
if not QDRANT_API_KEY or not QDRANT_URL:
    raise RuntimeError("Please set QDRANT_API_KEY and QDRANT_URL environment variables.")

qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)
print(qdrant.get_collections())


def ensure_collection(collection_name, vector_size):
    """Create or recreate a Qdrant collection if it does not exist."""
    if collection_name not in qdrant.get_collections().collections:
        qdrant.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )

def upsert_embeddings(collection_name, embeddings, chunks):
    """Upsert embeddings and their text chunks into Qdrant."""
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding.tolist(),
            payload={"text": chunk}
        )
        for embedding, chunk in zip(embeddings, chunks)
    ]
    qdrant.upsert(collection_name=collection_name, points=points) 