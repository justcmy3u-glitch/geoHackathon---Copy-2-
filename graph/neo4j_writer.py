from neo4j import GraphDatabase
import os
import logging

logger = logging.getLogger(__name__)


class Neo4jWriter:
    """
    Writes entities and relations into a Neo4j graph using MERGE
    to avoid duplicates.

    Node labels are TYPED (Скважина, Пласт, Месторождение, Параметр, …)
    instead of the generic Сущность, so the Cypher template queries in
    cypher_queries.py (which match on specific labels) work correctly.
    """

    _TYPE_TO_LABEL = {
        "СКВАЖИНА":      "Скважина",
        "ПЛАСТ":         "Пласт",
        "СВИТА":         "Пласт",      # treated as Пласт for graph purposes
        "МЕСТОРОЖДЕНИЕ": "Месторождение",
        "ПАРАМЕТР":      "Параметр",
        "ИССЛЕДОВАНИЕ":  "Исследование",
    }

    def __init__(self):
        uri      = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
        user     = os.environ.get("NEO4J_USER",     "neo4j")
        password = os.environ.get("NEO4J_PASSWORD",  "password123")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_entities_batch(self, entities: list):
        """MERGE entities with proper typed labels."""
        if not entities:
            return

        with self.driver.session() as session:
            for ent in entities:
                label = self._resolve_label(ent.get("type", ""))
                session.run(
                    f"""
                    MERGE (e:{label} {{id: $entity_id}})
                    SET e.name          = $canonical_name,
                        e.type          = $type,
                        e.value         = $value,
                        e.unit          = $unit,
                        e.raw_mention   = $raw_mention
                    """,
                    entity_id=ent.get("entity_id", ent.get("id", "")),
                    canonical_name=ent.get("canonical_name", ent.get("name", "")),
                    type=ent.get("type", ""),
                    value=str(ent.get("value", "")) if ent.get("value") is not None else "",
                    unit=ent.get("unit", ""),
                    raw_mention=ent.get("raw_mention", ""),
                )

    def add_relations_batch(self, relations: list):
        """
        MERGE typed nodes and create labelled relationships.

        Each relation dict must contain:
          subject_id, subject_name, subject_type,
          object_id,  object_name,  object_type,
          relation_type, doc_id, page (optional)
        """
        if not relations:
            return

        with self.driver.session() as session:
            for rel in relations:
                s_label = self._resolve_label(rel.get("subject_type", ""))
                o_label = self._resolve_label(rel.get("object_type", ""))
                rel_type = self._sanitize_rel_type(rel.get("relation_type", "СВЯЗЬ"))

                session.run(
                    f"""
                    MERGE (s:{s_label} {{id: $subject_id}})
                    ON CREATE SET s.name = $subject_name, s.type = $subject_type
                    MERGE (o:{o_label} {{id: $object_id}})
                    ON CREATE SET o.name = $object_name, o.type = $object_type
                    MERGE (s)-[r:{rel_type} {{doc_id: $doc_id}}]->(o)
                    SET r.page = $page
                    """,
                    subject_id=rel.get("subject_id", rel.get("subject", "")),
                    subject_name=rel.get("subject_name", rel.get("subject_id", "")),
                    subject_type=rel.get("subject_type", ""),
                    object_id=rel.get("object_id", rel.get("object", "")),
                    object_name=rel.get("object_name", rel.get("object_id", "")),
                    object_type=rel.get("object_type", ""),
                    doc_id=rel.get("doc_id", rel.get("meta", {}).get("doc_id", "")),
                    page=rel.get("page", rel.get("meta", {}).get("page", 0)),
                )

    def write_from_ner_result(self, ner_result: dict, doc_id: str = "", page: int = 0):
        """
        Convenience method: takes the raw NER result from ColabNERClient.extract()
        and writes both entities and relations.

        Automatically builds subject/object metadata for relations using the
        entity id→type lookup from the same NER result.
        """
        entities = ner_result.get("entities", [])
        relations = ner_result.get("relations", [])

        self.add_entities_batch(entities)

        # Build entity_id → {type, name} map for relation enrichment
        id_map = {e["entity_id"]: e for e in entities if "entity_id" in e}

        enriched_relations = []
        for rel in relations:
            subj_id = rel.get("subject", "")
            obj_id  = rel.get("object", "")
            meta    = rel.get("meta", {})

            subj_ent = id_map.get(subj_id, {})
            obj_ent  = id_map.get(obj_id, {})

            enriched_relations.append({
                "subject_id":   subj_id,
                "subject_name": subj_ent.get("canonical_name", subj_id),
                "subject_type": subj_ent.get("type", ""),
                "object_id":    obj_id,
                "object_name":  obj_ent.get("canonical_name", obj_id),
                "object_type":  obj_ent.get("type", ""),
                "relation_type": rel.get("relation", "СВЯЗЬ"),
                "doc_id":       meta.get("doc_id", doc_id),
                "page":         meta.get("page", page),
            })

        self.add_relations_batch(enriched_relations)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_label(self, entity_type: str) -> str:
        return self._TYPE_TO_LABEL.get(entity_type.upper(), "Сущность")

    @staticmethod
    def _sanitize_rel_type(rel_type: str) -> str:
        """Cypher relationship types must be ASCII-safe identifiers."""
        import re
        # Keep Cyrillic, latin, digits and underscores; replace others with _
        sanitized = re.sub(r'[^\w]', '_', rel_type, flags=re.UNICODE)
        return sanitized or "СВЯЗЬ"

    def verify_graph(self) -> dict:
        """Quick health-check: returns node/edge counts per label."""
        with self.driver.session() as session:
            total = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            wells = session.run("MATCH (n:Скважина) RETURN count(n) AS c").single()["c"]
            formations = session.run("MATCH (n:Пласт) RETURN count(n) AS c").single()["c"]
            rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        return {
            "total_nodes":  total,
            "wells":        wells,
            "formations":   formations,
            "total_edges":  rels,
        }

    def close(self):
        self.driver.close()
