import re

class QueryClassifier:
    """
    Classifies queries into strategies: HYBRID_RAG, GRAPH_RAG, or AGENT.
    Priority: AGENT (complex) > GRAPH (relations) > HYBRID (facts).
    """
    def classify(self, query: str) -> str:
        query_lower = query.lower()
        
        # 1. Complex/Multi-hop -> AGENT
        agent_keywords = ["сравни", "проанализируй", "разница", "почему", "вывод", "история"]
        if any(k in query_lower for k in agent_keywords) or len(query.split()) > 15:
            return "AGENT"
            
        # 2. Relational/Graph -> GRAPH_RAG
        graph_keywords = ["связан", "влияет", "относится к", "вскрыл", "состоит из", "структура"]
        if any(k in query_lower for k in graph_keywords):
            return "GRAPH_RAG"
            
        # 3. Factual/Default -> HYBRID_RAG
        return "HYBRID_RAG"
