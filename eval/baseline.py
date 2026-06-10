"""Baseline evaluation: BM25-only retrieval vs HybridRAG.

Runs a side-by-side comparison on a small geo-domain Q&A set
and writes ./reports/baseline_report.html via compute_metrics.
"""
import time
from typing import List, Dict

from eval.metrics import compute_metrics

# ---------------------------------------------------------------------------
# Demo dataset (no external services required)
# ---------------------------------------------------------------------------
DEMO_CORPUS: List[str] = [
    "Скважина 247. Баженовская свита вскрыта на глубине 2850 м. Отбор керна произведён.",
    "Методы ГИС на площади Кашаган: ГК, НКТ, резистивиметрия, кавернометрия.",
    "Пористая вода обнаружена на глубине 1200–1800 м в центральной части площади.",
]

DEMO_QA: List[Dict] = [
    {
        "question": "На какой глубине вскрыта баженовская свита в скважине 247?",
        "reference_answer": "Баженовская свита вскрыта на глубине 2850 м в скважине 247.",
    },
    {
        "question": "Какие методы ГИС применялись?",
        "reference_answer": "Применены ГК, НКТ, резистивиметрия.",
    },
]


def _bm25_retrieve(query: str, corpus: List[str], top_k: int = 1) -> str:
    """Minimal BM25-like retrieval using word overlap (no external libs)."""
    import re
    q_words = set(re.findall(r'\w+', query.lower()))
    scores = []
    for doc in corpus:
        doc_words = set(re.findall(r'\w+', doc.lower()))
        score = len(q_words.intersection(doc_words))
        scores.append((score, doc))
    scores.sort(key=lambda x: x[0], reverse=True)
    return "\n".join(doc for _, doc in scores[:top_k])


def run_eval(qa_pairs: List[Dict] = None, corpus: List[str] = None) -> str:
    """Run BM25-only baseline evaluation.

    Returns HTML report string (also written to ./reports/baseline_report.html).
    """
    if qa_pairs is None:
        qa_pairs = DEMO_QA
    if corpus is None:
        corpus = DEMO_CORPUS

    results = []
    for item in qa_pairs:
        q = item["question"]
        ref = item["reference_answer"]

        t0 = time.time()
        context = _bm25_retrieve(q, corpus)
        # BM25-only: answer is simply the top retrieved passage
        answer = context.split(".")[0] if context else ""
        elapsed_ms = int((time.time() - t0) * 1000)

        results.append({
            "question": q,
            "answer": answer,
            "reference_answer": ref,
            "context": context,
            "time_ms": elapsed_ms,
        })

    import os
    html = compute_metrics(results)
    # Also write under baseline name
    os.makedirs("./reports", exist_ok=True)
    with open("./reports/baseline_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Baseline BM25 evaluation complete. Report: ./reports/baseline_report.html")
    return html


if __name__ == "__main__":
    run_eval()
