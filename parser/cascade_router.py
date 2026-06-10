import os
import fitz
import tempfile
import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from parser.cache_manager import CacheManager
from parser.djvu_converter import DjvuConverter
from parser.geo_chunker import GeoChunker
from parser.pdf_extractor import extract_text_and_tables
import requests
import time

class CascadeRouter:
    def __init__(self, colab_url: str = None):
        self.colab_url = (colab_url or os.environ.get("COLAB_API_URL") or "").rstrip("/")
        self.cache = CacheManager()
        self.djvu_converter = DjvuConverter()
        self.chunker = GeoChunker()

    def route_document(self, file_path: str, doc_id: str = None) -> dict:
        doc_id = doc_id or os.path.splitext(os.path.basename(file_path))[0]
        lower_path = file_path.lower()

        if lower_path.endswith(".docx"):
            return self._process_docx(file_path, doc_id)

        if lower_path.endswith(".djvu"):
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_pdf_path = tmp.name
            try:
                self.djvu_converter.convert_to_pdf(file_path, tmp_pdf_path)
                result = self._process_pdf(tmp_pdf_path, doc_id)
                result["type"] = "djvu"
                return result
            finally:
                if os.path.exists(tmp_pdf_path):
                    os.remove(tmp_pdf_path)

        if lower_path.endswith(".pdf"):
            return self._process_pdf(file_path, doc_id)

        raise ValueError(f"Unsupported document format: {file_path}")

    def process_document(self, file_path: str, doc_id: str):
        result = self.route_document(file_path, doc_id)
        for page in result["pages"]:
            yield page

    def _process_pdf(self, file_path: str, doc_id: str) -> dict:
        with fitz.open(file_path) as doc:
            page_count = len(doc)
            text_lengths = [len(doc.load_page(i).get_text().strip()) for i in range(page_count)]

        if text_lengths and all(length >= 50 for length in text_lengths):
            document_type = "text_pdf"
        elif any(length >= 50 for length in text_lengths):
            document_type = "mixed_pdf"
        else:
            document_type = "scan_pdf"

        pages = []
        max_workers = min(4, max(1, page_count))
        processed = 0
        start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._process_pdf_page, file_path, page_num, doc_id): page_num
                for page_num in range(page_count)
            }

            for future in as_completed(futures):
                page_num = futures[future]
                try:
                    pages.append(future.result())
                except Exception as exc:
                    pages.append({
                        "doc_id": doc_id,
                        "page_num": page_num,
                        "content": "",
                        "type": document_type,
                        "error": f"Page processing failed: {exc}",
                    })
                processed += 1
                print(f"[parser] processed {processed}/{page_count} pages from {os.path.basename(file_path)}", flush=True)

        pages.sort(key=lambda page: page["page_num"])
        elapsed = time.perf_counter() - start
        return {
            "doc_id": doc_id,
            "pages": pages,
            "type": document_type,
            "page_count": page_count,
            "elapsed_seconds": round(elapsed, 3),
        }

    def _process_pdf_page(self, file_path: str, page_num: int, doc_id: str) -> dict:
        with fitz.open(file_path) as doc:
            page = doc.load_page(page_num)
            text = page.get_text("text").strip()
            if len(text) >= 50:
                content = extract_text_and_tables(page)
                return {
                    "doc_id": doc_id,
                    "page_num": page_num,
                    "content": content,
                    "type": "text_pdf",
                }

            page_signature = self._page_signature(file_path, page_num)
            cached_hash = self.cache.get_page_hash(page_signature)
            if cached_hash:
                cached = self.cache.get(cached_hash)
                if cached:
                    cached["cache_hit"] = True
                    return cached

            pix = page.get_pixmap(dpi=300, alpha=False)
            img_bytes = pix.tobytes("png")

        page_hash = self.cache.get_hash(img_bytes)
        cached = self.cache.get(page_hash)
        if cached:
            self.cache.set_page_hash(page_signature, page_hash)
            cached["cache_hit"] = True
            return cached

        res = self._ocr_scan_page(img_bytes, doc_id, page_num)
        res["cache_hit"] = False
        res["dpi"] = 300
        self.cache.set(page_hash, res)
        self.cache.set_page_hash(page_signature, page_hash)
        return res

    def _page_signature(self, file_path: str, page_num: int) -> str:
        stat = os.stat(file_path)
        raw = f"{os.path.abspath(file_path)}:{stat.st_size}:{stat.st_mtime_ns}:{page_num}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _ocr_scan_page(self, img_bytes: bytes, doc_id: str, page_num: int) -> dict:
        if not self.colab_url or "insert-your-cloudflared-url" in self.colab_url:
            return {
                "doc_id": doc_id,
                "page_num": page_num,
                "content": "",
                "type": "scan_pdf",
                "error": "Colab OCR is not configured. Set COLAB_API_URL to a live tunnel before OCR.",
            }

        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        retries = 2
        last_error = None
        while retries > 0:
            try:
                headers = {"x-api-key": os.environ.get("COLAB_API_KEY", "")}
                resp = requests.post(
                    f"{self.colab_url}/ocr",
                    json={"image_base64": b64_img},
                    headers=headers,
                    timeout=(2, 8),
                )
                resp.raise_for_status()
                md = resp.json().get("markdown", "")
                return {"doc_id": doc_id, "page_num": page_num, "content": md, "type": "scan_pdf"}
            except Exception as e:
                last_error = e
                retries -= 1
                if retries > 0:
                    time.sleep(0.25)

        return {
            "doc_id": doc_id,
            "page_num": page_num,
            "content": "",
            "type": "scan_pdf",
            "error": f"Colab OCR failed: {last_error}",
        }

    def _process_docx(self, file_path: str, doc_id: str) -> dict:
        try:
            from docx import Document
            from docx.table import Table
            from docx.text.paragraph import Paragraph
        except ImportError as exc:
            raise RuntimeError("DOCX support requires python-docx") from exc

        document = Document(file_path)
        content = []

        for child in document.element.body.iterchildren():
            if child.tag.endswith("}p"):
                paragraph = Paragraph(child, document)
                formatted = self._format_docx_paragraph(paragraph)
                if formatted:
                    content.append(formatted)
            elif child.tag.endswith("}tbl"):
                table = Table(child, document)
                formatted = self._format_docx_table(table)
                if formatted:
                    content.append(formatted)

        markdown = "\n\n".join(content)
        return {
            "doc_id": doc_id,
            "pages": [{"doc_id": doc_id, "page_num": 0, "content": markdown, "type": "docx"}],
            "type": "docx",
            "page_count": 1,
            "elapsed_seconds": 0,
        }

    def _format_docx_paragraph(self, paragraph) -> str:
        parts = []
        for run in paragraph.runs:
            text = run.text
            if not text:
                continue
            parts.append(f"**{text}**" if run.bold else text)

        line = "".join(parts).strip()
        if not line:
            return ""

        style_name = paragraph.style.name.lower() if paragraph.style else ""
        if style_name.startswith("heading") or style_name.startswith("title"):
            return f"## {line}"
        return line

    def _format_docx_table(self, table) -> str:
        rows = []
        for row in table.rows:
            rows.append([cell.text.strip().replace("\n", " ") for cell in row.cells])
        if not rows:
            return ""

        width = max(len(row) for row in rows)
        normalized = [row + [""] * (width - len(row)) for row in rows]
        header = normalized[0]
        separator = ["---"] * width
        body = normalized[1:]

        markdown_rows = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(separator) + " |",
        ]
        markdown_rows.extend("| " + " | ".join(row) + " |" for row in body)
        return "\n".join(markdown_rows)


def route_document(file_path: str, doc_id: str = None, colab_url: str = None) -> dict:
    return CascadeRouter(colab_url=colab_url).route_document(file_path, doc_id=doc_id)
