import re

class QueryClassifier:
    """
    Classifies queries into strategies: HYBRID_RAG, GRAPH_RAG, or AGENT.
    Priority: AGENT (complex) > GRAPH (relations) > HYBRID (facts).
    """

    def classify(self, query: str) -> str:
        query_lower = query.lower()

        # 1. Complex/Multi-hop -> AGENT
        # Includes definitional questions ("что такое"), analytical ("сравни", "проанализируй"),
        # causal ("почему", "как образу"), summary ("вывод", "история")
        agent_keywords = [
            "сравни", "проанализируй", "разница", "почему", "вывод", "история",
            "что такое", "как образу", "объясни", "опиши механизм", "расскажи",
        ]
        if any(k in query_lower for k in agent_keywords) or len(query.split()) > 15:
            return "AGENT"

        # 2. Relational/Graph -> GRAPH_RAG
        # Note: use substring roots so "вскрыл", "вскрыла", "вскрыли", "вскрыта" all match "вскрыл"
        graph_keywords = [
            "связан", "влияет", "относится к", "вскрыл", "вскрыт",
            "состоит из", "структура", "в каких скважинах", "все скважины",
        ]
        if any(k in query_lower for k in graph_keywords):
            return "GRAPH_RAG"

        # 3. Factual/Default -> HYBRID_RAG
        return "HYBRID_RAG"


def classify_query(query: str) -> str:
    """Module-level convenience wrapper around QueryClassifier.classify."""
    return QueryClassifier().classify(query)
