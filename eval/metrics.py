import os
import pandas as pd
from typing import List, Dict, Optional
import re


def citation_accuracy(answer: str, context: str) -> float:
    """Ratio of answer sentences that are supported by context words."""
    ans_words = set(re.findall(r'\w+', answer.lower()))
    ctx_words = set(re.findall(r'\w+', context.lower()))
    if not ans_words:
        return 1.0
    return len(ans_words.intersection(ctx_words)) / len(ans_words)


def faithfulness(answer: str, context: str) -> float:
    """How much of the answer's words exist in context."""
    return citation_accuracy(answer, context)


def answer_relevance(answer: str, question: str) -> float:
    """Naive word-overlap relevance between answer and question."""
    ans_words = set(re.findall(r'\w+', answer.lower()))
    q_words = set(re.findall(r'\w+', question.lower()))
    if not q_words:
        return 1.0
    return len(ans_words.intersection(q_words)) / len(q_words)


def compute_metrics(results: List[Dict]) -> str:
    """
    Computes heuristic metrics and outputs an HTML report.
    results items should contain:
    'question', 'answer', 'reference_answer', 'context', 'time_ms', 'valid_citations_ratio'
    """
    data = []

    for r in results:
        ans = r.get("answer", "")
        ref = r.get("reference_answer", "")
        ctx = r.get("context", "")
        q = r.get("question", "")

        # 1. Entity Precision/Recall (naive overlap)
        ans_words = set(re.findall(r'\w+', ans.lower()))
        ref_words = set(re.findall(r'\w+', ref.lower()))
        if not ref_words:
            precision = 1.0
            recall = 1.0
        else:
            intersection = ans_words.intersection(ref_words)
            precision = len(intersection) / len(ans_words) if ans_words else 0
            recall = len(intersection) / len(ref_words)

        # 2. Faithfulness
        faith = faithfulness(ans, ctx)

        # 3. Citation Accuracy
        cit_acc = r.get("valid_citations_ratio", citation_accuracy(ans, ctx))

        # 4. Answer Relevance
        relevance = answer_relevance(ans, q)

        data.append({
            "Question": q,
            "Precision": precision,
            "Recall": recall,
            "Faithfulness": faith,
            "Citation Accuracy": cit_acc,
            "Answer Relevance": relevance,
            "Time (ms)": r.get("time_ms", 0)
        })

    df = pd.DataFrame(data)

    html = f"""
<html>
<head>
  <title>Eval Report</title>
  <style>body{{font-family: Arial, sans-serif;}} table{{border-collapse: collapse; width: 100%;}} th, td{{border: 1px solid #ddd; padding: 8px;}} th{{background-color: #f2f2f2;}}</style>
</head>
<body>
  <h2>Geo-RAG Evaluation Metrics</h2>
  {df.to_html(index=False, float_format="%.2f")}
  <br>
  <h3>Average Metrics</h3>
  {df.mean(numeric_only=True).to_frame(name="Mean").to_html(float_format="%.2f")}
</body>
</html>
"""

    os.makedirs("./reports", exist_ok=True)
    with open("./reports/eval_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    return html


def run_evaluation(results: Optional[List[Dict]] = None) -> str:
    """
    Entry-point for automated evaluation.
    If results is None, uses built-in demo dataset.
    Returns HTML report string and writes to ./reports/eval_report.html
    """
    if results is None:
        results = [
            {
                "question": "На какой глубине вскрыта баженовская свита в скважине 247?",
                "answer": "Баженовская свита вскрыта на глубине 2850 м.",
                "reference_answer": "Баженовская свита вскрыта на глубине 2850 м в скважине 247.",
                "context": "Скважина 247. Баженовская свита вскрыта на глубине 2850 м. Отбор керна произведён.",
                "time_ms": 320,
                "valid_citations_ratio": 0.95,
            },
            {
                "question": "Какие методы ГИС применялись?",
                "answer": "Применялись методы ГК, НКТ и резистивиметрия.",
                "reference_answer": "Применены ГК, НКТ, резистивиметрия.",
                "context": "Методы ГИС: ГК, НКТ, резистивиметрия, кавернометрия.",
                "time_ms": 210,
                "valid_citations_ratio": 0.90,
            },
        ]
    return compute_metrics(results)
