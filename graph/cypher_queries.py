CYPHER_TEMPLATES = {
    # ---------------------------------------------------------------
    # Wells with core studies at a given field
    # ---------------------------------------------------------------
    "скважины_с_исследованиями": """
        MATCH (m:Месторождение {id: $field_name})<-[:НАХОДИТСЯ_В]-(w:Скважина)
              -[:ВСКРЫЛ]->(f)
              -[:ИМЕЕТ_ИССЛЕДОВАНИЕ]->(s:Исследование)
        WHERE s.type = 'КЕРН'
        RETURN w.id as well, f.id as formation, s.doc_id as doc, s.page as page
        LIMIT 50
    """,

    # ---------------------------------------------------------------
    # Parameters of a specific formation in a given well
    # ---------------------------------------------------------------
    "параметры_пласта": """
        MATCH (w:Скважина {id: $well_id})-[:ВСКРЫЛ]->(f {id: $formation})
              -[:ИМЕЕТ_ПАРАМЕТР]->(p:Параметр)
        RETURN p.type as param, p.value as val, p.unit as unit,
               p.doc_id as doc, p.page as page
    """,

    # ---------------------------------------------------------------
    # Multi-hop: field → well → formation (2 hops)
    # ---------------------------------------------------------------
    "multi_hop_field_well_formation": """
        MATCH (m:Месторождение)-[:НАХОДИТСЯ_В]->(w:Скважина)-[:ВСКРЫЛ]->(f)
        RETURN m.id AS field, w.id AS well, f.id AS formation
        LIMIT 50
    """,

    # ---------------------------------------------------------------
    # All wells that penetrated a given formation
    # ---------------------------------------------------------------
    "скважины_в_пласте": """
        MATCH (w:Скважина)-[r:ВСКРЫЛ]->(f {id: $formation})
        RETURN w.id as well, r.doc_id as doc, r.page as page
        ORDER BY w.id
        LIMIT 50
    """,

    # ---------------------------------------------------------------
    # Health check — total node / edge counts
    # ---------------------------------------------------------------
    "health_check": """
        MATCH (n) RETURN labels(n)[0] AS label, count(n) AS total
        ORDER BY total DESC
        LIMIT 20
    """,
}
