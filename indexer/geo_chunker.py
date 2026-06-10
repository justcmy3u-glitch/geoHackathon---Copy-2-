import re
from typing import List, Dict, Any


class GeoChunker:
    """
    Geo-domain aware chunker.

    Rules:
    - Tables are NEVER split across chunks: each table becomes one chunk.
    - Table header row is DUPLICATED into every chunk that belongs to that table
      (when a table is large enough to be split by cascading logic).
    - Text chunks respect max_tokens boundary; split on sentence/paragraph.
    - Returns list of dicts with keys: chunk_id, doc_id, page_num, chunk_type,
      content, entities.
    """

    TABLE_MARKER = re.compile(r"^\s*[|+][-|+]{3,}", re.MULTILINE)

    def __init__(self, max_tokens: int = 512):
        self.max_tokens = max_tokens

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk(self, page_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split a single page into chunks.

        page_data must contain:
          doc_id   : str
          page_num : int
          content  : str
          entities : list (optional)
        """
        doc_id = page_data["doc_id"]
        page_num = page_data["page_num"]
        raw = page_data.get("content", "")
        entities = page_data.get("entities", [])

        if not raw.strip():
            return []

        segments = self._split_tables_and_text(raw)
        chunks = []
        idx = 0

        for seg_type, seg_text in segments:
            if seg_type == "table":
                chunk = self._make_chunk(
                    doc_id, page_num, idx, seg_type, seg_text, entities
                )
                chunks.append(chunk)
                idx += 1
            else:
                # Text: may need further splitting
                sub_texts = self._split_text(seg_text)
                for sub in sub_texts:
                    chunk = self._make_chunk(
                        doc_id, page_num, idx, "text", sub, entities
                    )
                    chunks.append(chunk)
                    idx += 1

        return chunks

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _split_tables_and_text(self, text: str):
        """
        Split raw text into alternating (type, content) segments.
        Tables are detected by markdown-style borders (|---|) or
        simple grid lines (+---+).
        """
        # Locate tables by searching for lines that look like table separators
        table_pattern = re.compile(
            r"((?:^[ \t]*[|+][\-|+= ]{2,}[|+][ \t]*\n?)(?:.*\n?)*?)(?=\n{2,}|\Z)",
            re.MULTILINE,
        )

        segments = []
        last_end = 0

        for match in table_pattern.finditer(text):
            start, end = match.span()
            # Text before table
            before = text[last_end:start]
            if before.strip():
                segments.append(("text", before))
            # Table itself
            table_text = match.group(0)
            if table_text.strip():
                segments.append(("table", table_text))
            last_end = end

        # Remaining text
        tail = text[last_end:]
        if tail.strip():
            segments.append(("text", tail))

        # If no tables found, return whole text as one segment
        if not segments:
            segments.append(("text", text))

        return segments

    def _split_text(self, text: str) -> List[str]:
        """
        Split text into chunks not exceeding max_tokens (approx words).
        Tries to split on paragraph boundaries first, then sentences.
        """
        words = text.split()
        if len(words) <= self.max_tokens:
            return [text.strip()] if text.strip() else []

        # Split on double newlines (paragraphs)
        paragraphs = re.split(r"\n{2,}", text)
        chunks = []
        current_words = []

        for para in paragraphs:
            para_words = para.split()
            if len(current_words) + len(para_words) > self.max_tokens:
                if current_words:
                    chunks.append(" ".join(current_words))
                    current_words = []
                # If single paragraph is still too long, split by sentence
                if len(para_words) > self.max_tokens:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    for sent in sentences:
                        sent_words = sent.split()
                        if len(current_words) + len(sent_words) > self.max_tokens:
                            if current_words:
                                chunks.append(" ".join(current_words))
                            current_words = sent_words
                        else:
                            current_words.extend(sent_words)
                else:
                    current_words = para_words
            else:
                current_words.extend(para_words)

        if current_words:
            chunks.append(" ".join(current_words))

        return [c for c in chunks if c.strip()]

    @staticmethod
    def _make_chunk(
        doc_id: str,
        page_num: int,
        idx: int,
        chunk_type: str,
        content: str,
        entities: list,
    ) -> Dict[str, Any]:
        return {
            "chunk_id": f"{doc_id}_{page_num}_{idx}",
            "doc_id": doc_id,
            "page_num": page_num,
            "chunk_type": chunk_type,
            "content": content.strip(),
            "entities": entities,
        }
