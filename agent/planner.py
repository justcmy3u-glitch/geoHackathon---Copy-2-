import requests
import os
import json
from typing import Optional
from retriever.hybrid_rag import HybridRAG


class AgentPlanner:
    def __init__(
        self,
        colab_url: Optional[str] = None,
        hybrid_rag: Optional[HybridRAG] = None,
    ):
        """Both dependencies are optional and resolved from env vars / defaults."""
        self.colab_url = colab_url or os.environ.get("COLAB_API_URL", "").rstrip("/")
        self.hybrid_rag = hybrid_rag or HybridRAG()
        self.api_key = os.environ.get("COLAB_API_KEY", "")

    def decompose_query(self, query: str) -> list[str]:
        system_prompt = """Разбей сложный геологический вопрос на 2-3 простых подзапроса для поиска по базе фактов.
Верни только валидный JSON-массив строк. Например: ["Какая глубина скважины 1?", "Какие пласты вскрыты?"]"""  # noqa: E501

        if not self.colab_url:
            # No LLM available — return the query as-is (single subquery)
            return [query]

        try:
            headers = {"x-api-key": self.api_key}
            resp = requests.post(
                f"{self.colab_url}/generate",
                json={
                    "context": "",
                    "question": query,
                    "system_prompt": system_prompt,
                    "max_new_tokens": 200,
                },
                headers=headers,
                timeout=30,
            )

            if resp.status_code == 200:
                text = resp.json().get("response", "[]")
                try:
                    start = text.find('[')
                    end = text.rfind(']') + 1
                    if start != -1 and end != 0:
                        return json.loads(text[start:end])
                except Exception:
                    pass
        except Exception:
            pass

        return [query]

    def solve(self, query: str) -> list[dict]:
        """
        Decomposes the query, runs Hybrid RAG for each sub-query, and merges the context.
        """
        subqueries = self.decompose_query(query)
        all_results: dict = {}

        for sq in subqueries:
            hits = self.hybrid_rag.retrieve(sq, top_k=2)
            for hit in hits:
                all_results[hit["chunk_id"]] = hit

        return list(all_results.values())[:6]

    def run(self, question: str) -> list[dict]:
        """Alias for solve() — used in tests."""
        return self.solve(question)
