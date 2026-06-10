import requests
import json
import os
from typing import Dict, Any


class ColabNERClient:
    """
    Client for the Colab /ner endpoint.

    Can be constructed with an explicit URL or falls back to
    the COLAB_API_URL environment variable.
    """

    def __init__(self, colab_url: str = None):
        if colab_url:
            self.colab_url = colab_url.rstrip("/")
        else:
            self.colab_url = os.environ.get("COLAB_API_URL", "").rstrip("/")

        self.ner_url = f"{self.colab_url}/ner" if self.colab_url else ""
        self._api_key = os.environ.get("COLAB_API_KEY", "")

    def _headers(self) -> Dict[str, str]:
        return {"x-api-key": self._api_key}

    def extract(self, text: str, doc_id: str, page: int) -> Dict[str, Any]:
        """
        Calls the Colab LLM for structural NER and relationship extraction.

        Returns dict containing:
            {
                "entities": [...],
                "relations": [...],
            }
        or on failure:
            {
                "entities": [],
                "relations": [],
                "error": "<reason>",
            }
        """
        if not self.colab_url or "insert-your-cloudflared-url" in self.colab_url:
            return {
                "entities": [],
                "relations": [],
                "error": "No Colab URL provided — set COLAB_API_URL env var",
            }

        payload = {
            "text": text,
            "doc_id": doc_id,
            "page": page,
        }

        try:
            resp = requests.post(
                self.ner_url,
                json=payload,
                headers=self._headers(),
                timeout=(5, 90),
            )
            if resp.status_code == 200:
                raw_str = resp.json().get("json_string", "")

                # Strip markdown fences that the LLM sometimes adds
                if "```json" in raw_str:
                    raw_str = raw_str.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_str:
                    raw_str = raw_str.split("```")[1].strip()

                try:
                    parsed = json.loads(raw_str)
                except json.JSONDecodeError:
                    return {
                        "entities": [],
                        "relations": [],
                        "error": f"Failed to decode JSON from LLM. Raw: {raw_str[:200]}",
                    }

                # Inject provenance meta into every relation that's missing it
                for rel in parsed.get("relations", []):
                    meta = rel.setdefault("meta", {})
                    meta.setdefault("doc_id", doc_id)
                    meta.setdefault("page", page)

                return parsed

            else:
                return {
                    "entities": [],
                    "relations": [],
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                }

        except Exception as e:
            return {"entities": [], "relations": [], "error": str(e)}
