import os
from typing import Optional


class MoondreamLocal:
    """
    Local Moondream2 vision model wrapper.

    Uses the official moondream Python package (pip install moondream) if
    available, otherwise falls back to HuggingFace transformers.

    The model is loaded lazily on first call to describe_image() so that
    import-time errors don't crash the whole service.
    """

    def __init__(self, model_dir: str = "./models/moondream2"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self._model = None
        self._tokenizer = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self):
        """Lazy-load the model (CPU, float32)."""
        if self._model is not None:
            return

        # Try the official lightweight moondream package first
        try:
            import moondream as md  # pip install moondream
            self._model = md.vl(model=self.model_dir)
            self._backend = "moondream_pkg"
            return
        except Exception:
            pass

        # Fallback: HuggingFace transformers
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._model = AutoModelForCausalLM.from_pretrained(
            "vikhyatk/moondream2",
            trust_remote_code=True,
            torch_dtype=torch.float32,
            cache_dir=self.model_dir,
        )
        self._tokenizer = AutoTokenizer.from_pretrained(
            "vikhyatk/moondream2",
            cache_dir=self.model_dir,
        )
        self._backend = "transformers"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def describe_image(
        self,
        image,  # PIL.Image.Image  OR  bytes
        prompt: Optional[str] = None,
    ) -> str:
        """
        Describe an image.

        Args:
            image: Either a PIL.Image.Image or raw bytes of an image file.
            prompt: Optional custom prompt. Defaults to a geological description prompt.

        Returns:
            Text description produced by the model.
        """
        from PIL import Image
        import io

        if isinstance(image, (bytes, bytearray)):
            image = Image.open(io.BytesIO(image))

        if prompt is None:
            prompt = (
                "Что изображено на этом рисунке? "
                "Перечисли все подписи, числа, обозначения, масштаб и координаты если есть."
            )

        self._load()

        if self._backend == "moondream_pkg":
            # Official package API
            enc = self._model.encode_image(image)
            return self._model.query(enc, prompt)["answer"]
        else:
            # HuggingFace transformers API
            enc_image = self._model.encode_image(image)
            return self._model.answer_question(enc_image, prompt, self._tokenizer)

    def is_complex(self, image_path: str, width_threshold: int = 800, height_threshold: int = 600) -> bool:
        """
        Heuristic: returns True if image should be routed to Colab (Qwen)
        instead of processed locally.

        Rules:
        - Image dimensions > threshold → complex (likely a detailed geo map)
        - Detected Cyrillic text in the image → complex (Moondream is English-centric)
        """
        from PIL import Image

        try:
            img = Image.open(image_path)
            w, h = img.size
            if w > width_threshold or h > height_threshold:
                return True
        except Exception:
            pass

        # Additional: check for Cyrillic via figure_detector
        try:
            from parser.figure_detector import is_complex_figure
            return is_complex_figure(image_path)
        except Exception:
            return False
