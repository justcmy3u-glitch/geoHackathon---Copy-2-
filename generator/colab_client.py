import requests
import os
import base64
import io
from typing import Optional, Dict, Any
from core.answer_rules import SYSTEM_PROMPT_ANSWER


class ColabClient:
    """
    Client for the Colab FastAPI server (colab/app.py).

    Supports:
    - /generate  — text generation / question answering
    - /vision    — visual analysis of geological figures (returns structured JSON)
    - /ocr       — OCR of scanned page images
    """

    def __init__(self):
        self.colab_url = os.environ.get("COLAB_API_URL", "").rstrip("/")
        self.api_key = os.environ.get("COLAB_API_KEY", "")

    def _headers(self) -> Dict[str, str]:
        return {"x-api-key": self.api_key}

    def _is_configured(self) -> bool:
        return bool(self.colab_url) and "insert-your-cloudflared-url" not in self.colab_url

    # ------------------------------------------------------------------
    # Text generation / QA
    # ------------------------------------------------------------------

    def generate_answer(self, context: str, question: str) -> str:
        if not self._is_configured():
            return "ОШИБКА: COLAB_API_URL не настроен."

        try:
            resp = requests.post(
                f"{self.colab_url}/generate",
                json={
                    "context": context,
                    "question": question,
                    "system_prompt": SYSTEM_PROMPT_ANSWER,
                    "max_new_tokens": 1024,
                },
                headers=self._headers(),
                timeout=(5, 120),
                verify=True,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except requests.exceptions.RequestException as e:
            return f"Ошибка Colab сервера: {str(e)}"

    # ------------------------------------------------------------------
    # Vision (geological figure analysis)
    # ------------------------------------------------------------------

    def vision(
        self,
        image_b64: Optional[str] = None,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Analyse a geological figure using Qwen2.5-VL on Colab.

        Accepts one of:
        - image_b64:   already base64-encoded PNG/JPEG string
        - image_path:  local file path
        - image_bytes: raw bytes

        Returns dict with keys: graphic_type, key_entities, numerical_values,
        scale_info, coordinates, text_annotations, description_for_indexing.
        """
        if not self._is_configured():
            return {"error": "COLAB_API_URL не настроен."}

        # Resolve image to base64 string
        if image_b64 is None:
            if image_path is not None:
                with open(image_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode()
            elif image_bytes is not None:
                image_b64 = base64.b64encode(image_bytes).decode()
            else:
                return {"error": "Необходимо передать image_b64, image_path или image_bytes"}

        try:
            import json
            resp = requests.post(
                f"{self.colab_url}/vision",
                json={"image_base64": image_b64},
                headers=self._headers(),
                timeout=(5, 90),
                verify=True,
            )
            resp.raise_for_status()
            raw = resp.json().get("json_string", "")

            # Strip markdown fences if model wrapped JSON in ```json ... ```
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].strip()

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"error": "JSON decode failed", "raw": raw}

        except requests.exceptions.RequestException as e:
            return {"error": f"Colab request failed: {str(e)}"}

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------

    def ocr(
        self,
        image_b64: Optional[str] = None,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
    ) -> str:
        """
        OCR a scanned page via Colab Qwen.
        Returns Markdown text.
        """
        if not self._is_configured():
            return ""

        if image_b64 is None:
            if image_path is not None:
                with open(image_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode()
            elif image_bytes is not None:
                image_b64 = base64.b64encode(image_bytes).decode()
            else:
                return ""

        try:
            resp = requests.post(
                f"{self.colab_url}/ocr",
                json={"image_base64": image_b64},
                headers=self._headers(),
                timeout=(5, 90),
                verify=True,
            )
            resp.raise_for_status()
            return resp.json().get("markdown", "")
        except requests.exceptions.RequestException as e:
            return f"OCR error: {str(e)}"
