import os
import re
import streamlit as st

from security.auth import get_authenticator
from security.input_validator import validate_upload, validate_query
from security.audit_logger import log_event
from retriever.query_classifier import QueryClassifier
from retriever.hybrid_rag import HybridRAG
from generator.colab_client import ColabClient

APP_NAME = "KMG GeoEvidence Copilot"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="KMG",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        :root {
            --kmg-bg: #f7f8fa; --kmg-surface: #ffffff; --kmg-text: #111827;
            --kmg-muted: #667085; --kmg-line: #e5e7eb;
            --kmg-teal: #0f766e; --kmg-amber: #b7791f;
        }
        .stApp { background: var(--kmg-bg); color: var(--kmg-text); }
        [data-testid="stSidebar"] { background: #111827; }
        [data-testid="stSidebar"] * { color: #f9fafb; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px; }
        .kmg-header { border-bottom: 1px solid var(--kmg-line); padding-bottom: 1rem; margin-bottom: 1.25rem; }
        .kmg-title { font-size: 2rem; font-weight: 700; margin: 0; }
        .kmg-subtitle { color: var(--kmg-muted); margin-top: .4rem; font-size: .98rem; }
        .stTabs [data-baseweb="tab-list"] { gap: .35rem; border-bottom: 1px solid var(--kmg-line); }
        .stTabs [data-baseweb="tab"] { height: 2.6rem; padding: 0 .9rem; border-radius: 6px 6px 0 0; }
        .result-card { background:#fff; border:1px solid var(--kmg-line); border-radius:10px; padding:1rem 1.2rem; margin-bottom:.8rem; }
        .result-score { font-size:.78rem; color:var(--kmg-muted); float:right; }
        .result-source { font-size:.8rem; color:var(--kmg-teal); font-weight:600; margin-bottom:.4rem; }
        .result-snippet { font-size:.92rem; line-height:1.55; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _build_answer(query: str, hits: list) -> str:
    if not hits:
        return "По вашему запросу ничего не найдено в базе документов. Загрузите геологические отчёты во вкладке 'Knowledge base'."
    snippets = [h.get("content", "").strip()[:300] for h in hits[:3] if h.get("content", "").strip()]
    if not snippets:
        return "Документы найдены, но текстовое содержимое недоступно."
    answer = "На основе найденных документов:\n\n"
    for i, s in enumerate(snippets, 1):
        answer += f"**[{i}]** {s}\n\n"
    return answer


def _rel_bar(score: float) -> str:
    pct = min(int(score * 100), 100)
    color = "#0f766e" if pct > 60 else "#b7791f" if pct > 30 else "#ef4444"
    return f'<div style="height:5px;border-radius:3px;background:#e5e7eb;margin-top:6px"><div style="width:{pct}%;height:5px;border-radius:3px;background:{color}"></div></div>'


authenticator, auth_config = get_authenticator()
authenticator.login("main")

if st.session_state.get("authentication_status"):
    user = st.session_state.get("username", "user")

    with st.sidebar:
        st.markdown(f"### {APP_NAME}")
        st.caption("Evidence-grounded geology assistant")
        st.divider()
        st.write(f"Signed in as **{user}**")
        authenticator.logout("Sign out", "sidebar")
        st.divider()
        colab_url_input = st.text_input(
            "Colab API URL",
            value=os.environ.get("COLAB_API_URL", ""),
            placeholder="https://xxxx-xx.ngrok.io",
            help="Если задан - используется LLM для генерации. Без него - поисковый режим.",
        )
        if colab_url_input:
            os.environ["COLAB_API_URL"] = colab_url_input

    st.markdown(
        f'<div class="kmg-header"><div class="kmg-title">{APP_NAME}</div>'
        f'<div class="kmg-subtitle">Search, verify, and cite geological evidence from indexed technical documents.</div></div>',
        unsafe_allow_html=True,
    )

    colab_url = os.environ.get("COLAB_API_URL", "")
    c1, c2, c3 = st.columns(3)
    c1.metric("Knowledge base", "Ready")
    c2.metric("Mode", "LLM + Search" if colab_url else "Search only")
    c3.metric("Audit", "Enabled")

    tab_chat, tab_knowledge, tab_graph, tab_monitoring = st.tabs(
        ["Chat", "Knowledge base", "Knowledge Graph", "Monitoring"]
    )

    with tab_chat:
        st.subheader("Evidence search")
        if not colab_url:
            st.info(
                "Colab API не настроен — работает **поисковый режим**: "
                "система находит релевантные фрагменты из документов и показывает их напрямую. "
                "Укажите Colab URL в сайдбаре для режима генерации ответов."
            )

        query = st.chat_input("Спросите о скважинах, пластах, испытаниях, стратиграфии...")
        if query:
            try:
                valid_query = validate_query(query)
                st.chat_message("user").write(valid_query)
                log_event("QUERY_MADE", user, {"query": valid_query})

                with st.spinner("Поиск по базе документов..."):
                    classifier = QueryClassifier()
                    mode = classifier.classify(valid_query)
                    rag = HybridRAG()
                    hits = rag.retrieve(valid_query, top_k=5)

                with st.chat_message("assistant"):
                    if colab_url and hits:
                        context = "\n\n".join([h.get("content", "")[:400] for h in hits[:4]])
                        client = ColabClient()
                        response = client.generate_answer(context, valid_query)
                        st.markdown(response)
                    else:
                        st.markdown(_build_answer(valid_query, hits))
                    st.caption(f"Режим: `{mode}` · Найдено фрагментов: {len(hits)}")

                if hits:
                    with st.expander(f"Источники ({len(hits)} фрагментов)", expanded=True):
                        for hit in hits:
                            doc_id = hit.get("doc_id", "unknown")
                            page = hit.get("page_num", "?")
                            score = float(hit.get("rrf_score", hit.get("score", 0)))
                            content = hit.get("content", "").strip()[:250]
                            chunk_type = hit.get("type", "text")
                            st.markdown(
                                f'<div class="result-card">'
                                f'<span class="result-score">score: {score:.3f}</span>'
                                f'<div class="result-source">\U0001f4c4 {doc_id} &middot; стр. {page} &middot; [{chunk_type}]</div>'
                                f'<div class="result-snippet">{content}...</div>'
                                f'{_rel_bar(score)}</div>',
                                unsafe_allow_html=True,
                            )
                else:
                    st.warning("Фрагменты не найдены. Загрузите документы во вкладке 'Knowledge base'.")

            except Exception as exc:
                st.error(str(exc))
                log_event("SECURITY_BLOCK", user, {"query": query, "error": str(exc)})

    with tab_knowledge:
        st.subheader("Document intake")
        uploaded_files = st.file_uploader(
            "Upload geological reports",
            type=["pdf", "djvu", "docx"],
            accept_multiple_files=True,
        )
        if st.button("Upload and index"):
            if not uploaded_files:
                st.warning("No files selected.")
            else:
                for file in uploaded_files:
                    try:
                        valid = validate_upload(file.getvalue(), file.name)
                        st.success(f"{valid.safe_filename} passed validation ({valid.mime})")
                        log_event("FILE_UPLOAD", user, {"filename": valid.safe_filename, "size": len(file.getvalue())})
                    except Exception as exc:
                        st.error(f"Security validation failed: {exc}")
                        log_event("SECURITY_BLOCK", user, {"filename": file.name, "error": str(exc)})
        st.divider()
        st.subheader("Document registry")
        st.info("Document deletion from Qdrant and Neo4j is not implemented yet.")

    with tab_graph:
        st.subheader("Knowledge Graph Explorer")
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.markdown("#### Graph Query")
            cypher_query = st.text_area("Cypher query", value="MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 25", height=100)
            if st.button("Run Cypher Query"):
                st.info("Neo4j connection required.")
                st.code(cypher_query, language="cypher")
        with col_right:
            st.markdown("#### Graph Statistics")
            neo4j_uri = os.environ.get("NEO4J_URI", "")
            st.metric("Neo4j", "Connected" if neo4j_uri else "Not configured")
            st.metric("Nodes", "N/A")
            st.metric("Relationships", "N/A")

    with tab_monitoring:
        st.subheader("System audit")
        st.write("Recent security and activity events are stored in PostgreSQL.")
        st.code("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 10;", language="sql")
        st.divider()
        st.subheader("Evaluation Metrics")
        if st.button("Run evaluation baseline"):
            try:
                from eval.metrics import run_evaluation
                html = run_evaluation()
                st.success("Evaluation complete.")
                st.components.v1.html(html, height=400, scrolling=True)
            except Exception as exc:
                st.error(f"Evaluation error: {exc}")

elif st.session_state.get("authentication_status") is False:
    st.error("Incorrect username or password.")
    log_event("AUTH_FAILURE", "unknown", {})
else:
    st.info("Sign in with the configured account. Default local credentials: admin / admin123.")
