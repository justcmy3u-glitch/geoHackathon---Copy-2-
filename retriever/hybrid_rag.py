from indexer.bm25_index import BM25Index
from indexer.qdrant_writer import QdrantWriter
from indexer.embedder import Embedder

def min_max_scale(scores: list[float]) -> list[float]:
    if not scores:
        return []
    min_val = min(scores)
    max_val = max(scores)
    if max_val == min_val:
        return [1.0] * len(scores)
    return [(s - min_val) / (max_val - min_val) for s in scores]

class HybridRAG:
    def __init__(self, bm25_index: BM25Index, qdrant_writer: QdrantWriter, embedder: Embedder):
        self.bm25 = bm25_index
        self.qdrant = qdrant_writer
        self.embedder = embedder
        
    def retrieve(self, query: str, top_k: int = 5, k: int = 60) -> list[dict]:
        # BM25 Search
        bm25_hits = self.bm25.search(query, top_k=top_k * 2)
        bm25_scores = [hit["score"] for hit in bm25_hits]
        bm25_norm = min_max_scale(bm25_scores)
        
        # Qdrant Search
        query_vec = self.embedder.embed_text(query)
        qdrant_hits = self.qdrant.search(query_vec, top_k=top_k * 2)
        qdrant_scores = [hit["score"] for hit in qdrant_hits]
        qdrant_norm = min_max_scale(qdrant_scores)
        
        # RRF Fusion
        rrf_scores = {}
        docs = {}
        
        for rank, (hit, norm_score) in enumerate(zip(bm25_hits, bm25_norm)):
            chunk_id = hit["chunk_id"]
            docs[chunk_id] = hit
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1.0 / (k + rank + 1) + norm_score * 0.1
            
        for rank, (hit, norm_score) in enumerate(zip(qdrant_hits, qdrant_norm)):
            chunk_id = hit["chunk_id"]
            docs[chunk_id] = hit
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1.0 / (k + rank + 1) + norm_score * 0.1
            
        sorted_chunks = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
        
        results = []
        for chunk_id, score in sorted_chunks[:top_k]:
            meta = docs[chunk_id]
            meta["rrf_score"] = score
            results.append(meta)
            
        return results
