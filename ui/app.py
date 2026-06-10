import os
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

      .stApp {
        background: var(--kmg-bg);
        color: var(--kmg-text);
      }

      [data-testid="stSidebar"] {
        background: #111827;
      }

      [data-testid="stSidebar"] * {
        color: #f9fafb;
      }

      .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1180px;
      }

      h1, h2, h3 {
        letter-spacing: 0;
      }

      .kmg-header {
        border-bottom: 1px solid var(--kmg-line);
        padding-bottom: 1rem;
        margin-bottom: 1.25rem;
      }

      .kmg-title {
        font-size: 2rem;
        line-height: 1.15;
        font-weight: 700;
        margin: 0;
      }

      .kmg-subtitle {
        color: var(--kmg-muted);
        margin-top: .4rem;
        font-size: .98rem;
      }

      .kmg-pill {
        display: inline-flex;
        align-items: center;
        border: 1px solid var(--kmg-line);
        border-radius: 999px;
        padding: .25rem .65rem;
        margin-right: .35rem;
        background: var(--kmg-surface);
        color: var(--kmg-muted);
        font-size: .82rem;
      }

      .stTabs [data-baseweb="tab-list"] {
        gap: .35rem;
        border-bottom: 1px solid var(--kmg-line);
      }

      .stTabs [data-baseweb="tab"] {
        height: 2.6rem;
        padding: 0 .9rem;
        border-radius: 6px 6px 0 0;
      }

      .stButton button,
      [data-testid="stFileUploaderDropzone"] button {
        border-radius: 6px;
        border: 1px solid var(--kmg-line);
      }

      .stChatInput textarea {
        border-radius: 8px;
      }

      [data-testid="stMetric"] {
        background: var(--kmg-surface);
        border: 1px solid var(--kmg-line);
        border-radius: 8px;
        padding: .8rem .9rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


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

    st.markdown(
        f"""
        <div class="kmg-header">
          <p class="kmg-title">{APP_NAME}</p>
          <p class="kmg-subtitle">Search, verify, and cite geological evidence from indexed technical documents.</p>
          <span class="kmg-pill">Secure workspace</span>
          <span class="kmg-pill">Hybrid retrieval</span>
          <span class="kmg-pill">Audit ready</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    colab_url = os.environ.get("COLAB_API_URL", "")
    status_cols = st.columns(3)
    status_cols[0].metric("Knowledge base", "Ready")
    status_cols[1].metric("Colab OCR", "Configured" if colab_url else "Missing")
    status_cols[2].metric("Audit", "Enabled")

    tab_chat, tab_knowledge, tab_monitoring = st.tabs(["Chat", "Knowledge base", "Monitoring"])

    with tab_chat:
        st.subheader("Evidence search")
        if not colab_url:
            st.warning("COLAB_API_URL is not configured. OCR and generation calls may be unavailable.")

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
                    response = client.generate_answer("Mock context about geology", valid_query)
                    st.chat_message("assistant").write(response)

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

    with tab_monitoring:
        st.subheader("System audit")
        st.write("Recent security and activity events are stored in PostgreSQL.")
        st.code("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 10;", language="sql")

elif st.session_state.get("authentication_status") is False:
    st.error("Incorrect username or password.")
    log_event("AUTH_FAILURE", "unknown", {})
else:
    st.info("Sign in with the configured account. Default local credentials: admin / admin123.")
