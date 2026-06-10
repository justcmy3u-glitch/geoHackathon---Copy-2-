from graph.neo4j_writer import Neo4jWriter
from graph.cypher_queries import CYPHER_TEMPLATES

class GraphRAG:
    def __init__(self, neo4j_writer: Neo4jWriter):
        self.neo4j = neo4j_writer

    def extract_context(self, template_key: str, params: dict) -> str:
        """
        Runs a predefined Cypher query and formats the result as RAG context.
        """
        if template_key not in CYPHER_TEMPLATES:
            return ""

        query = CYPHER_TEMPLATES[template_key]
        context_parts = []

        with self.neo4j.driver.session() as session:
            result = session.run(query, **params)
            for record in result:
                # Format depends on returned keys, we do a generic formatting 
                # but ensure doc_id and page are present if available.
                doc = record.get("doc", "unknown")
                page = record.get("page", 0)
                
                # Exclude doc and page from the properties string
                props = ", ".join(f"{k}: {v}" for k, v in record.items() if k not in ["doc", "page"])
                
                context_parts.append(f"[Источник: {doc}, Страница: {page}]\nНайдено по графу: {props}\n")

        return "\n".join(context_parts)
