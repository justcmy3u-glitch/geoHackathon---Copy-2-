from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from qdrant_client.http.exceptions import ResponseHandlingException
import os

class QdrantWriter:
    def __init__(self, collection_name="georag"):
        self.client = QdrantClient(host=os.environ.get("QDRANT_HOST", "localhost"), port=6333)
        self.collection_name = collection_name
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            if not self.client.collection_exists(self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
                )
        except Exception as e:
            print(f"Failed to ensure collection: {e}")

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]):
        points = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = chunk["chunk_id"]
            # Try to avoid duplicates by deterministic ID if possible, but for MVP we use random UUIDs or hash
            import uuid
            pid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))
            
            points.append(
                PointStruct(
                    id=pid,
                    vector=emb,
                    payload=chunk
                )
            )
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception as e:
            print(f"Qdrant indexing failed: {e}")

    def search(self, query_vector: list[float], top_k: int = 5):
        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            results = []
            for hit in hits:
                meta = hit.payload.copy()
                meta["score"] = hit.score
                results.append(meta)
            return results
        except Exception as e:
            print(f"Qdrant search failed: {e}")
            return []
