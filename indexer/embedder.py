from FlagEmbedding import BGEM3FlagModel

class Embedder:
    def __init__(self):
        # We load BGE-M3 (dense only) to CPU by default or CUDA if available
        self.model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=False)

    def embed_text(self, text: str) -> list[float]:
        embeddings = self.model.encode(text, return_dense=True, return_sparse=False, return_colbert_vecs=False)
        return embeddings['dense_vecs'].tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        embeddings = self.model.encode(texts, batch_size=batch_size, return_dense=True, return_sparse=False, return_colbert_vecs=False)
        return embeddings['dense_vecs'].tolist()

    def encode(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Alias for embed_batch — used in tests and pipeline code."""
        return self.embed_batch(texts, batch_size=batch_size)

    def chunk_document(self, page_data: dict, max_tokens: int = 512) -> list[dict]:
        # Uses GeoChunker under the hood via CascadeRouter, this is just a wrapper for legacy code compatibility
        # If passed already chunked text, we just return it wrapped.
        content = page_data.get("content", "")
        if not content:
            return []

        return [{
            "chunk_id": f"{page_data['doc_id']}_{page_data['page_num']}_0",
            "doc_id": page_data["doc_id"],
            "page_num": page_data["page_num"],
            "content": content
        }]
