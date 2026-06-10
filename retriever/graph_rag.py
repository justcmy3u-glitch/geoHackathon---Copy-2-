import os
from typing import Optional
from graph.neo4j_writer import Neo4jWriter
from graph.cypher_queries import CYPHER_TEMPLATES


class GraphRAG:
    def __init__(self, neo4j_writer: Optional[Neo4jWriter] = None):
        """neo4j_writer is optional; if not provided, it is initialised from env vars."""
        self.neo4j = neo4j_writer or Neo4jWriter(
            uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            user=os.environ.get("NEO4J_USER", "neo4j"),
            password=os.environ.get("NEO4J_PASSWORD", ""),
        )

    def extract_context(self, template_key: str, params: dict) -> str:
        """
        Runs a predefined Cypher query and formats the result as RAG context.
        """
        if template_key not in CYPHER_TEMPLATES:
            return ""

        query = CYPHER_TEMPLATES[template_key]
        context_parts = []

        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query, **params)
                for record in result:
                    doc = record.get("doc", "unknown")
                    page = record.get("page", 0)
                    props = ", ".join(f"{k}: {v}" for k, v in record.items() if k not in ["doc", "page"])
                    context_parts.append(f"[Источник: {doc}, Страница: {page}]\nНайдено по графу: {props}\n")
        except Exception as e:
            return f"Ошибка выполнения Cypher-запроса: {e}"

        if not context_parts:
            return "Данных по запросу не найдено."

        return "\n".join(context_parts)

    def search(
        self,
        question: str,
        entities: Optional[list] = None,
        template_key: str = "wells_by_formation",
    ) -> str:
        """
        High-level search interface used in tests and pipeline code.

        Attempts to auto-select a Cypher template based on entities,
        then delegates to extract_context().

        If the graph is empty or Neo4j is unreachable, returns an honest
        'no data' message instead of crashing.
        """
        entities = entities or []
        params: dict = {}

        # Auto-select template by heuristics on question + entities
        q_lower = question.lower()
        if "свита" in q_lower or "свите" in q_lower or any(
            e in ["БЖ", "Баженовская", "Тюменская"] for e in entities
        ):
            template_key = "wells_by_formation"
            # Pass formation name from entities if available
            for e in entities:
                if e not in ["Месторождение_X", "Месторождение_Y"]:
                    params["formation"] = e
                    break
        if "месторождение" in q_lower or any(
            "Месторождение" in e for e in entities
        ):
            params["field"] = next(
                (e for e in entities if "Месторождение" in e), "unknown"
            )

        context = self.extract_context(template_key, params)
        return context if context else "Данных в графе не найдено."
