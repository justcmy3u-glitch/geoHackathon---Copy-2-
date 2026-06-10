import os
import pandas as pd
from typing import List, Dict
import re

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
        # How much of the answer's words exist in context?
        ctx_words = set(re.findall(r'\w+', ctx.lower()))
        overlap = ans_words.intersection(ctx_words)
        faithfulness = len(overlap) / len(ans_words) if ans_words else 0
        
        # 3. Citation Accuracy provided directly by validation step
        cit_acc = r.get("valid_citations_ratio", 1.0)
        
        data.append({
            "Question": r.get("question", ""),
            "Precision": precision,
            "Recall": recall,
            "Faithfulness": faithfulness,
            "Citation Accuracy": cit_acc,
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
