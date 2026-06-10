import os
import re
import streamlit as st

from security.auth import get_authenticator
from security.input_validator import validate_upload, validate_query
from security.audit_logger import log_event
from retriever.query_classifier import QueryClassifier
from retriever.hybrid_rag import HybridRAG
from generator.colab_client import ColabClient
from generator.openai_client import OpenAIClient

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
            --bg: #0b1220;
            --bg-soft: #111a2b;
            --surface: rgba(255, 255, 255, 0.88);
            --surface-2: rgba(255, 255, 255, 0.72);
            --card: #ffffff;
            --text: #0f172a;
            --muted: #667085;
            --line: rgba(15, 23, 42, 0.08);
            --teal: #0f766e;
            --teal-2: #14b8a6;
            --amber: #b7791f;
            --red: #dc2626;
            --shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
            --radius: 18px;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(20,184,166,0.10), transparent 28%),
                radial-gradient(circle at top right, rgba(183,121,31,0.10), transparent 22%),
                linear-gradient(180deg, #f5f7fb 0%, #eef2f7 100%);
            color: var(--text);
        }

        .main .block-container {
            max-width: 1220px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(8,15,27,0.98) 0%, rgba(15,23,42,0.98) 100%);
            border-right: 1px solid rgba(255,255,255,0.08);
        }

        [data-testid="stSidebar"] * {
            color: #f8fafc;
        }

        [data-testid="stSidebar"] .stTextInput input {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.10);
            color: #fff;
            border-radius: 12px;
        }

        [data-testid="stSidebar"] .stTextInput label,
        [data-testid="stSidebar"] .stCaption {
            color: rgba(248,250,252,0.78) !important;
        }

        /* Hero */
        .hero {
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(135deg, rgba(15,118,110,0.96) 0%, rgba(17,24,39,0.98) 55%, rgba(183,121,31,0.92) 100%);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 24px;
            padding: 1.6rem 1.6rem 1.45rem 1.6rem;
            margin-bottom: 1.35rem;
            box-shadow: 0 20px 45px rgba(15, 23, 42, 0.18);
        }

        .hero:before {
            content: "";
            position: absolute;
            inset: auto -80px -80px auto;
            width: 220px;
            height: 220px;
            background: radial-gradient(circle, rgba(255,255,255,0.16), transparent 65%);
            pointer-events: none;
        }

        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            padding: .35rem .7rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.12);
            color: #ecfeff;
            font-size: .76rem;
            font-weight: 700;
            letter-spacing: .02em;
            text-transform: uppercase;
            border: 1px solid rgba(255,255,255,0.14);
            margin-bottom: .85rem;
        }

        .hero-title {
            margin: 0;
            color: #ffffff;
            font-size: 2rem;
            line-height: 1.1;
            font-weight: 800;
            letter-spacing: -0.02em;
        }

        .hero-subtitle {
            margin-top: .55rem;
            max-width: 850px;
            color: rgba(255,255,255,0.82);
            font-size: .98rem;
            line-height: 1.55;
        }

        .hero-chips {
            display: flex;
            flex-wrap: wrap;
            gap: .55rem;
            margin-top: 1rem;
        }

        .hero-chip {
            display: inline-flex;
            align-items: center;
            padding: .38rem .72rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.12);
            color: #f8fafc;
            font-size: .8rem;
            font-weight: 600;
        }

        /* Metrics */
        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(255,255,255,0.88));
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1rem 1rem .9rem 1rem;
            box-shadow: var(--shadow);
        }

        div[data-testid="stMetricLabel"] {
            color: var(--muted);
            font-weight: 600;
        }

        div[data-testid="stMetricValue"] {
            color: var(--text);
            font-weight: 800;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: .45rem;
            background: rgba(255,255,255,0.56);
            border: 1px solid rgba(15,23,42,0.06);
            padding: .35rem;
            border-radius: 16px;
            margin-bottom: 1rem;
            backdrop-filter: blur(8px);
        }

        .stTabs [data-baseweb="tab"] {
            height: 2.7rem;
            padding: 0 1rem;
            border-radius: 12px;
            color: var(--muted);
            font-weight: 600;
            transition: .2s ease;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, var(--teal), #0b4f52);
            color: #ffffff !important;
            box-shadow: 0 8px 18px rgba(15,118,110,0.22);
        }

        /* Cards / sections */
        .section-note {
            background: linear-gradient(180deg, rgba(255,255,255,0.82), rgba(255,255,255,0.74));
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 1rem 1.05rem;
            margin-bottom: 1rem;
            box-shadow: var(--shadow);
        }

        .section-note-title {
            font-size: .95rem;
            font-weight: 800;
            color: var(--text);
            margin-bottom: .3rem;
        }

        .section-note-text {
            color: var(--muted);
            font-size: .92rem;
            line-height: 1.55;
        }

        /* Inputs */
        .stTextInput input,
        .stTextArea textarea,
        [data-testid="stChatInput"] textarea,
        [data-testid="stFileUploader"] section {
            border-radius: 14px !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        [data-testid="stChatInput"] textarea {
            background: rgba(255,255,255,0.92) !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
            color: var(--text) !important;
            box-shadow: inset 0 1px 2px rgba(15,23,42,0.03);
        }

        [data-testid="stChatInput"] {
            background: transparent;
        }

        /* Buttons */
        .stButton > button,
        .stDownloadButton > button {
            border: 0 !important;
            border-radius: 12px !important;
            background: linear-gradient(135deg, var(--teal), #0b4f52) !important;
            color: #fff !important;
            font-weight: 700 !important;
            padding: .62rem 1rem !important;
            box-shadow: 0 10px 20px rgba(15,118,110,0.18);
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            filter: brightness(1.03);
            transform: translateY(-1px);
        }

        /* Alerts */
        [data-testid="stAlert"] {
            border-radius: 14px;
            border: 1px solid rgba(15,23,42,0.06);
        }

        /* Expanders */
        .streamlit-expanderHeader {
            font-weight: 700;
            color: var(--text);
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255,255,255,0.84);
            box-shadow: var(--shadow);
        }

        /* Chat messages */
        div[data-testid="stChatMessage"] {
            background: rgba(255,255,255,0.80);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: .25rem .25rem;
            box-shadow: var(--shadow);
        }

        /* Result cards */
        .result-card {
            background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,255,255,0.90));
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            margin-bottom: .85rem;
            box-shadow: var(--shadow);
        }

        .result-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            margin-bottom: .35rem;
        }

        .result-source {
            color: var(--text);
            font-size: .92rem;
            font-weight: 800;
        }

        .result-score {
            display: inline-flex;
            align-items: center;
            padding: .28rem .55rem;
            border-radius: 999px;
            background: rgba(15,118,110,0.08);
            color: var(--teal);
            font-size: .78rem;
            font-weight: 800;
            white-space: nowrap;
        }

        .result-meta {
            color: var(--muted);
            font-size: .8rem;
            margin-bottom: .65rem;
        }

        .result-snippet {
            color: #334155;
            font-size: .93rem;
            line-height: 1.6;
        }

        .rel-wrap {
            height: 7px;
            background: #e5e7eb;
            border-radius: 999px;
            overflow: hidden;
            margin-top: .8rem;
        }

        .rel-fill {
            height: 7px;
            border-radius: 999px;
        }

        /* Code blocks */
        .stCodeBlock, pre {
            border-radius: 16px !important;
        }

        /* File uploader */
        [data-testid="stFileUploader"] section {
            background: rgba(255,255,255,0.86);
            border: 1px dashed rgba(15,23,42,0.16);
            padding: 1rem;
        }

        /* Small polish */
        hr {
            border-color: rgba(15,23,42,0.08);
        }
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
    pct = min(max(int(score * 100), 0), 100)
    color = "#0f766e" if pct > 60 else "#b7791f" if pct > 30 else "#ef4444"
    return (
        f'<div class="rel-wrap">'
        f'<div class="rel-fill" style="width:{pct}%; background:{color};"></div>'
        f'</div>'
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
        f"""
        <div class="hero">
            <div class="hero-badge">KMG • GeoEvidence Platform</div>
            <div class="hero-title">{APP_NAME}</div>
            <div class="hero-subtitle">
                Search, verify, and cite geological evidence from indexed technical documents.
            </div>
            <div class="hero-chips">
                <span class="hero-chip">Evidence-first answers</span>
                <span class="hero-chip">Hybrid retrieval</span>
                <span class="hero-chip">Audit-enabled workflow</span>
            </div>
        </div>
        """,
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
        st.markdown(
            """
            <div class="section-note">
                <div class="section-note-title">Рабочее пространство для поиска доказательной информации</div>
                <div class="section-note-text">
                    Задавайте вопросы по скважинам, пластам, испытаниям и стратиграфии.
                    Ниже будут показаны ответы и найденные фрагменты с указанием источников.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
                        response = client.generate_answer(context, valid_query)
                        st.markdown(response)
                    else:

                if hits:
                    with st.expander(f"Источники ({len(hits)} фрагментов)", expanded=True):
                        for hit in hits:
                            doc_id = hit.get("doc_id", "unknown")
                            page = hit.get("page_num", "?")
                            score = float(hit.get("rrf_score", hit.get("score", 0)))
                            content = hit.get("content", "").strip()[:250]
                            chunk_type = hit.get("type", "text")
                            st.markdown(
                                f"""
                                <div class="result-card">
                                    <div class="result-top">
                                        <div class="result-source">📄 {doc_id}</div>
                                        <div class="result-score">score: {score:.3f}</div>
                                    </div>
                                    <div class="result-meta">стр. {page} · [{chunk_type}]</div>
                                    <div class="result-snippet">{content}...</div>
                                    {_rel_bar(score)}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                else:
                    st.warning("Фрагменты не найдены. Загрузите документы во вкладке 'Knowledge base'.")

            except Exception as exc:
                st.error(str(exc))
                log_event("SECURITY_BLOCK", user, {"query": query, "error": str(exc)})

    with tab_knowledge:
        st.subheader("Document intake")
        st.markdown(
            """
            <div class="section-note">
                <div class="section-note-title">Загрузка и валидация документов</div>
                <div class="section-note-text">
                    Добавляйте PDF, DJVU и DOCX-файлы с геологическими отчётами.
                    Валидация безопасности и логирование остаются включёнными.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
        st.markdown(
            """
            <div class="section-note">
                <div class="section-note-title">Просмотр и диагностика графа знаний</div>
                <div class="section-note-text">
                    Интерфейс ниже оставлен без изменения по логике: можно вставить Cypher-запрос
                    и посмотреть статус конфигурации Neo4j.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
        st.markdown(
            """
            <div class="section-note">
                <div class="section-note-title">Мониторинг и проверка качества</div>
                <div class="section-note-text">
                    Журнал аудита и блок оценки оставлены без функциональных изменений.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
