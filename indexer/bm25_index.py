import pickle
import os
import threading
from rank_bm25 import BM25Okapi

class BM25Index:
    def __init__(self, save_path="./index/bm25_geo_documents.pkl"):
        self.save_path = save_path
        self.corpus = []
        self.metadata = []
        self.bm25 = None
        self._lock = threading.Lock()
        self.load()

    def add_chunks(self, chunks: list):
        with self._lock:
            for c in chunks:
                self.corpus.append(c["content"])
                self.metadata.append(c)
            # Full rebuild on delta
            tokenized_corpus = [doc.split(" ") for doc in self.corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)
            self.save()

    def search(self, query: str, top_k: int = 5):
        with self._lock:
            if not self.bm25:
                return []
            tokenized_query = query.split(" ")
            scores = self.bm25.get_scores(tokenized_query)

            top_n = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            results = []
            for i in top_n:
                meta = self.metadata[i].copy()
                meta["score"] = scores[i]
                results.append(meta)
            return results

    def save(self):
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        with open(self.save_path, "wb") as f:
            pickle.dump({"corpus": self.corpus, "metadata": self.metadata}, f)

    def load(self):
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, "rb") as f:
                    data = pickle.load(f)
                self.corpus = data["corpus"]
                self.metadata = data["metadata"]
                if self.corpus:
                    tokenized_corpus = [doc.split(" ") for doc in self.corpus]
                    self.bm25 = BM25Okapi(tokenized_corpus)
            except Exception as e:
                # Corrupted pickle
                print(f"BM25 corrupted, rebuilding: {e}")
                self.corpus = []
                self.metadata = []
                self.bm25 = None
