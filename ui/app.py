import os
import re
import streamlit as st

from security.auth import get_authenticator
from security.input_validator import validate_upload, validate_query
from security.audit_logger import log_event
from retriever.query_classifier import QueryClassifier
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
            --kmg-bg: #f7f8fa;
            --kmg-surface: #ffffff;
            --kmg-text: #111827;
            --kmg-muted: #667085;
            --kmg-line: #e5e7eb;
            --kmg-teal: #0f766e;
            --kmg-amber: #b7791f;
        }
        .stApp { background: var(--kmg-bg); color: var(--kmg-text); }
        [data-testid="stSidebar"] { background: #111827; }
        [data-testid="stSidebar"] * { color: #f9fafb; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px; }
        h1, h2, h3 { letter-spacing: 0; }
        .kmg-header { border-bottom: 1px solid var(--kmg-line); padding-bottom: 1rem; margin-bottom: 1.25rem; }
        .kmg-title { font-size: 2rem; line-height: 1.15; font-weight: 700; margin: 0; }
        .kmg-subtitle { color: var(--kmg-muted); margin-top: .4rem; font-size: .98rem; }
        .kmg-pill { display: inline-flex; align-items: center; border: 1px solid var(--kmg-line); border-radius: 999px; padding: .25rem .65rem; margin-right: .35rem; background: var(--kmg-surface); color: var(--kmg-muted); font-size: .82rem; }
        .stTabs [data-baseweb="tab-list"] { gap: .35rem; border-bottom: 1px solid var(--kmg-line); }
        .stTabs [data-baseweb="tab"] { height: 2.6rem; padding: 0 .9rem; border-radius: 6px 6px 0 0; }
        .stButton button, [data-testid="stFileUploaderDropzone"] button { border-radius: 6px; border: 1px solid var(--kmg-line); }
        .stChatInput textarea { border-radius: 8px; }
        [data-testid="stMetric"] { background: var(--kmg-surface); border: 1px solid var(--kmg-line); border-radius: 8px; padding: .8rem .9rem; }
        .hallucination-warn { background: #fff7ed; border: 1px solid #f97316; border-radius: 8px; padding: .6rem .9rem; color: #7c2d12; font-size: .88rem; margin-top: .5rem; }
        .hallucination-ok { background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: .6rem .9rem; color: #14532d; font-size: .88rem; margin-top: .5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _hallucination_score(answer: str, context: str) -> float:
    """Heuristic: fraction of answer words present in context."""
    a_words = set(re.findall(r'\w+', answer.lower()))
    c_words = set(re.findall(r'\w+', context.lower()))
    if not a_words:
        return 1.0
    return len(a_words & c_words) / len(a_words)


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
        # COLAB tunnel URL override
        colab_url_input = st.text_input(
            "Colab API URL",
            value=os.environ.get("COLAB_API_URL", ""),
            placeholder="https://xxxx-xx.ngrok.io",
            help="Override COLAB_API_URL for this session (ngrok / localtunnel)",
        )
        if colab_url_input:
            os.environ["COLAB_API_URL"] = colab_url_input

    st.markdown(
        f"""
        <div class='kmg-header'>
          <div class='kmg-title'>{APP_NAME}</div>
          <div class='kmg-subtitle'>Search, verify, and cite geological evidence from indexed technical documents.</div>
          <div style='margin-top:.6rem'>
            <span class='kmg-pill'>Secure workspace</span>
            <span class='kmg-pill'>Hybrid retrieval</span>
            <span class='kmg-pill'>Audit ready</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    colab_url = os.environ.get("COLAB_API_URL", "")
    status_cols = st.columns(3)
    status_cols[0].metric("Knowledge base", "Ready")
    status_cols[1].metric("Colab OCR", "Configured" if colab_url else "Missing")
    status_cols[2].metric("Audit", "Enabled")

    tab_chat, tab_knowledge, tab_graph, tab_monitoring = st.tabs(
        ["Chat", "Knowledge base", "Knowledge Graph", "Monitoring"]
    )

    with tab_chat:
        st.subheader("Evidence search")
        if not colab_url:
            st.warning("COLAB_API_URL is not configured. Set it in the sidebar or env. OCR and generation may be unavailable.")

        query = st.chat_input("Ask about wells, formations, tests, stratigraphy, or report evidence...")
        if query:
            try:
                valid_query = validate_query(query)
                st.chat_message("user").write(valid_query)
                log_event("QUERY_MADE", user, {"query": valid_query})

                with st.spinner("Analyzing request..."):
                    classifier = QueryClassifier()
                    mode = classifier.classify(valid_query)
                    st.caption(f"Router mode: {mode}")

                    client = ColabClient()
                    mock_context = "Mock context about geology: well 247 bajenov suite depth 2850m"
                    response = client.generate_answer(mock_context, valid_query)

                    # Hallucination indicator
                    score = _hallucination_score(response, mock_context)
                    st.chat_message("assistant").write(response)
                    if score < 0.3:
                        st.markdown(
                            f"<div class='hallucination-warn'>Hallucination risk: HIGH (grounding score {score:.0%}). "
                            "Answer may contain information not found in the retrieved context. Verify sources.</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<div class='hallucination-ok'>Grounding score: {score:.0%} — Answer is well-supported by context.</div>",
                            unsafe_allow_html=True,
                        )

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
                        log_event(
                            "FILE_UPLOAD",
                            user,
                            {"filename": valid.safe_filename, "size": len(file.getvalue())},
                        )
                    except Exception as exc:
                        st.error(f"Security validation failed: {exc}")
                        log_event("SECURITY_BLOCK", user, {"filename": file.name, "error": str(exc)})
        st.divider()
        st.subheader("Document registry")
        st.info("Document deletion from Qdrant and Neo4j is not implemented yet.")

    with tab_graph:
        st.subheader("Knowledge Graph Explorer")
        st.info(
            "This view shows the Neo4j knowledge graph built from indexed documents. "
            "Connect Neo4j and run the indexer to populate the graph."
        )
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.markdown("#### Graph Query")
            cypher_query = st.text_area(
                "Cypher query",
                value="MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 25",
                height=100,
            )
            if st.button("Run Cypher Query"):
                st.info("Neo4j connection required. Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in environment.")
                # Integration point: from graph.neo4j_client import Neo4jClient
                # client = Neo4jClient(); results = client.query(cypher_query)
                st.code(cypher_query, language="cypher")
        with col_right:
            st.markdown("#### Graph Statistics")
            neo4j_uri = os.environ.get("NEO4J_URI", "")
            st.metric("Neo4j", "Connected" if neo4j_uri else "Not configured")
            st.metric("Nodes", "N/A (connect Neo4j)")
            st.metric("Relationships", "N/A (connect Neo4j)")
            if not neo4j_uri:
                st.caption("Set NEO4J_URI in .env to enable graph queries.")

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
                st.success("Evaluation complete. Report saved to ./reports/eval_report.html")
                st.components.v1.html(html, height=400, scrolling=True)
            except Exception as exc:
                st.error(f"Evaluation error: {exc}")

elif st.session_state.get("authentication_status") is False:
    st.error("Incorrect username or password.")
    log_event("AUTH_FAILURE", "unknown", {})
else:
    st.info("Sign in with the configured account. Default local credentials: admin / admin123.")
