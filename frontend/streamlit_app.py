import api_client
import streamlit as st

st.set_page_config(page_title="ResolveAI", page_icon=":material/shield:", layout="wide")

MODELS = {
    "Server default": None,
    "Claude Sonnet 5.5": "claude-sonnet-5-5",
    "Claude Opus 5.5": "claude-opus-5-5",
    "Claude Haiku 5.5": "claude-haiku-5-5",
}

st.session_state.setdefault("messages", [])
st.session_state.setdefault("last_result", None)

with st.sidebar:
    st.caption("Multi-agent incident intelligence")
    st.selectbox("Orchestration model", list(MODELS), key="model_label", help="Model used by the agents when an API key is configured.")
    status = api_client.health()
    if status is None:
        st.error("Backend unreachable", icon=":material/cloud_off:")
        st.caption(f"Expected at `{api_client.BACKEND_URL}`")
    else:
        st.success(f"Backend online · {status['database']}", icon=":material/cloud_done:")
        if not status["llm_enabled"]:
            st.warning("No API key: agents run in offline mode.", icon=":material/key_off:")

st.session_state["model"] = MODELS[st.session_state["model_label"]]

page = st.navigation(
    [
        st.Page(
            "app_pages/investigate.py", title="Investigate", icon=":material/forum:", default=True,
            help="Describe an incident and let the supervisor route it to the knowledge, incident, diagnostic and planning agents.",
        ),
        st.Page(
            "app_pages/monitor.py", title="Agent monitor", icon=":material/monitoring:",
            help="Step-by-step execution trace, retrieved runbook chunks and correlated incidents of the last investigation.",
        ),
        st.Page(
            "app_pages/incidents.py", title="Incident explorer", icon=":material/search:",
            help="Search and filter historical incidents and read their symptoms, root cause and resolution.",
        ),
        st.Page(
            "app_pages/knowledge.py", title="Knowledge base", icon=":material/menu_book:",
            help="Browse indexed runbooks, try hybrid search, and upload new documentation.",
        ),
        st.Page(
            "app_pages/evaluation.py", title="Evaluation", icon=":material/fact_check:",
            help="Latest benchmark results against the golden question set.",
        ),
    ],
    position="top",
)

st.title(page.title, icon=page.icon)
page.run()
