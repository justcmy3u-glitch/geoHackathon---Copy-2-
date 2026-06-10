import time
from indexer.bm25_index import BM25Index
from retriever.hybrid_rag import HybridRAG

# Pseudo evaluation script
def run_eval():
    queries = [
        "На какой глубине вскрыта баженовская свита в скважине 247?",
        "Какие методы ГИС применялись?"
    ]
    
    print("Running Baseline BM25 vs HybridRAG...")
    
    # Needs actual populated index to run
    print("Evaluation completed. (Mock)")

if __name__ == "__main__":
    run_eval()
