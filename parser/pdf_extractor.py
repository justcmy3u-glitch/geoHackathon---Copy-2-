import fitz
import re


def _looks_like_heading(text: str, font_size: float) -> bool:
    text = text.strip()
    if not text or len(text) > 120:
        return False
    return font_size >= 14 and not text.endswith((".", ",", ";", ":"))


def _looks_like_formula(text: str) -> bool:
    text = text.strip()
    if not text or text.startswith(("#", "|", "$")):
        return False
    if "=" not in text:
        return False
    return bool(re.fullmatch(r"[A-Za-zА-Яа-я0-9\s_{}()[\].,+\-*/^=<>≤≥πΠα-ωΑ-Ω]+", text))


def _format_line(text: str, font_size: float) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    if _looks_like_heading(text, font_size):
        return f"## {text}"
    if _looks_like_formula(text):
        return f"${text}$"
    return text


def _normalize_markdown_table(markdown: str) -> str:
    rows = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            rows.append(stripped)
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(row for row in rows if row)

def extract_text_and_tables(page: fitz.Page) -> str:
    """
    Extracts text and tables from a PyMuPDF page and formats them into Markdown.
    """
    content = []
    
    # Extract tables first
    tabs = page.find_tables()
    table_bboxes = []
    if tabs:
        for tab in tabs.tables:
            table_bboxes.append(tab.bbox)
            markdown = _normalize_markdown_table(tab.to_markdown().strip())
            if markdown:
                content.append(markdown)

    # Extract text block by block
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] == 0:  # text block
            b_bbox = fitz.Rect(b["bbox"])
            # Skip text if it's already part of a table
            if any(b_bbox.intersects(tb) for tb in table_bboxes):
                continue
            
            lines = []
            for l in b["lines"]:
                line_parts = []
                max_size = 0
                for s in l["spans"]:
                    line_parts.append(s["text"])
                    max_size = max(max_size, s.get("size", 0))
                formatted = _format_line(" ".join(line_parts), max_size)
                if formatted:
                    lines.append(formatted)
            block_text = "\n".join(lines).strip()
            if block_text:
                content.append(block_text)

    return "\n\n".join(content)
