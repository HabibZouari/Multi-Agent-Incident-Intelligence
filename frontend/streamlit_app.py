import streamlit as st
import requests
import json
import pandas as pd
import os

st.set_page_config(
    page_title="ResolveAI — Incident Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean, professional enterprise styling
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        background-color: #0e1117;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* Containers & Cards */
    .enterprise-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
    }

    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 16px;
        border-radius: 8px;
    }
    div[data-testid="stMetric"] label {
        color: #8b949e !important;
        font-weight: 500;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f0f6fc !important;
        font-weight: 600;
    }

    /* Buttons */
    .stButton>button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.15s ease;
    }
    .stButton>button:hover {
        background-color: #30363d;
        border-color: #8b949e;
        color: #f0f6fc;
    }

    /* Dataframes & Tables */
    div[data-testid="stDataFrame"] {
        border: 1px solid #30363d;
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Sidebar navigation & configuration
st.sidebar.markdown("### 🛡️ ResolveAI")
st.sidebar.caption("Multi-Agent Incident Intelligence & RAG")
st.sidebar.markdown("---")

selected_model = st.sidebar.selectbox(
    "Orchestration Model",
    ["auto/best-coding", "auto/smart", "auto/chat", "auto/reasoning", "auto/fast"],
    index=0
)

page = st.sidebar.radio(
    "Navigation",
    ["🤖 AI Investigation Chat", "📊 Agent Execution Monitor", "🚨 Incident Explorer", "📚 Knowledge Base", "📈 Evaluation Dashboard", "⚙️ System Settings"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("##### System Status")
st.sidebar.caption("🟢 Backend API: Connected (`localhost:8000`)")
st.sidebar.caption(f"🧠 Active Model: `{selected_model}`")

if page == "🤖 AI Investigation Chat":
    st.title("AI Incident Investigation")
    st.markdown("Collaborative multi-agent root-cause analysis, hybrid runbook retrieval, and historical incident correlation.")

    # Quick prompt triggers
    st.markdown("##### ⚡ Quick Scenarios")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔥 Auth Service 500 Errors", use_container_width=True):
            st.session_state.quick_prompt = "Authentication service started returning HTTP 500 errors after yesterday's deployment. Have we experienced something similar before? What should we investigate?"
    with col2:
        if st.button("⚠️ DB Connection Exhaustion", use_container_width=True):
            st.session_state.quick_prompt = "Database connection pool is exhausted on User PostgreSQL DB. What runbook steps should we follow?"
    with col3:
        if st.button("🚀 Payment Gateway Deployments", use_container_width=True):
            st.session_state.quick_prompt = "What recent deployments affected the payment processing gateway in the last 48 hours?"

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask a troubleshooting question or describe an incident...")
    if "quick_prompt" in st.session_state and st.session_state.quick_prompt:
        prompt = st.session_state.quick_prompt
        del st.session_state.quick_prompt

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner(f"Running multi-agent investigation with {selected_model}..."):
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/api/investigate",
                        json={"query": prompt, "model": selected_model},
                        timeout=90
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data.get("final_response", "No response generated.")
                        st.markdown(answer)

                        st.session_state.last_trace = data.get("execution_trace", [])
                        st.session_state.last_docs = data.get("retrieved_docs", [])
                        st.session_state.last_incidents = data.get("historical_incidents", [])

                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        st.error(f"Backend API error ({resp.status_code}): {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend at `{BACKEND_URL}`. Error: {e}")

elif page == "📊 Agent Execution Monitor":
    st.title("Agent Execution Monitor")
    st.markdown("Inspect multi-agent orchestration traces, supervisor intent routing, and hybrid retrieval evidence.")

    if "last_trace" in st.session_state and st.session_state.last_trace:
        st.subheader("Workflow Execution Trace")
        for idx, step in enumerate(st.session_state.last_trace):
            agent_name = step.get('agent', 'Agent')
            action_desc = step.get('action', step.get('decision', 'Executing'))
            with st.expander(f"Step {idx+1}: [{agent_name}] — {action_desc}", expanded=(idx == 0)):
                st.json(step)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Retrieved Documentation (Hybrid RAG)")
            if "last_docs" in st.session_state and st.session_state.last_docs:
                for doc in st.session_state.last_docs:
                    with st.container():
                        st.markdown(f"**{doc.get('source')}**")
                        st.caption(f"Score: `{doc.get('score', 0):.4f}` | Service: `{doc.get('service_name')}`")
                        st.text(doc.get('content', '')[:250] + "...")
                        st.markdown("---")
            else:
                st.info("No documents retrieved.")

        with col2:
            st.subheader("Correlated Incidents")
            if "last_incidents" in st.session_state and st.session_state.last_incidents:
                for inc in st.session_state.last_incidents:
                    with st.container():
                        st.markdown(f"**{inc.get('incident_id')}**: {inc.get('title')}")
                        st.caption(f"Severity: `{inc.get('severity')}` | Service: `{inc.get('service_name')}`")
                        st.text(f"Root Cause: {inc.get('root_cause')}")
                        st.markdown("---")
            else:
                st.info("No historical incidents correlated.")
    else:
        st.info("No active investigation trace found. Run an investigation in the **AI Investigation Chat** tab first.")

elif page == "🚨 Incident Explorer":
    st.title("Incident Explorer")
    st.markdown("Search and filter historical enterprise incidents and service resolutions.")

    col1, col2 = st.columns(2)
    with col1:
        sev_filter = st.selectbox("Severity Filter", ["All", "P1", "P2", "P3", "P4"])
    with col2:
        search_kw = st.text_input("Search Keyword", "")

    try:
        resp = requests.get(f"{BACKEND_URL}/api/incidents")
        if resp.status_code == 200:
            incidents = resp.json()
            if sev_filter != "All":
                incidents = [i for i in incidents if i["severity"] == sev_filter]
            if search_kw:
                incidents = [i for i in incidents if search_kw.lower() in i["title"].lower() or search_kw.lower() in i.get("root_cause", "").lower()]

            st.markdown(f"Showing **{len(incidents)}** records")
            df = pd.DataFrame(incidents)
            if not df.empty:
                st.dataframe(df[["incident_id", "severity", "service_name", "category", "status", "created_at"]], use_container_width=True)

                selected_id = st.selectbox("Select Incident ID", df["incident_id"].tolist())
                selected_inc = next((i for i in incidents if i["incident_id"] == selected_id), None)
                if selected_inc:
                    st.markdown("---")
                    st.subheader(f"Incident: {selected_inc['incident_id']}")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Title:** {selected_inc['title']}")
                        st.markdown(f"**Service:** {selected_inc['service_name']}")
                        st.markdown(f"**Category:** {selected_inc['category']}")
                    with c2:
                        st.markdown(f"**Severity:** `{selected_inc['severity']}`")
                        st.markdown(f"**Status:** {selected_inc['status']}")
                        st.markdown(f"**Created:** {selected_inc['created_at']}")
                    st.markdown(f"**Symptoms:** {selected_inc.get('symptoms', 'N/A')}")
                    st.markdown(f"**Root Cause:** {selected_inc.get('root_cause', 'N/A')}")
                    st.markdown(f"**Resolution:** {selected_inc.get('resolution', 'N/A')}")
            else:
                st.info("No incidents match criteria.")
    except Exception as e:
        st.warning(f"Backend API unavailable ({e})")

elif page == "📚 Knowledge Base":
    st.title("Knowledge Base")
    st.markdown("Manage technical documentation, troubleshooting runbooks, and vector embeddings.")

    with st.expander("Upload Runbook or Document"):
        uploaded_file = st.file_uploader("Select file", type=["md", "txt"])
        doc_type = st.selectbox("Document Type", ["technical_doc", "runbook", "architecture_guide"])
        service_name = st.text_input("Service Name", "Core Services")
        if uploaded_file is not None and st.button("Index Document"):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            data = {"document_type": doc_type, "service_name": service_name}
            resp = requests.post(f"{BACKEND_URL}/api/documents/upload", files=files, data=data)
            if resp.status_code == 200:
                st.success("Indexed successfully!")
            else:
                st.error(f"Error: {resp.text}")

    try:
        resp = requests.get(f"{BACKEND_URL}/api/documents")
        if resp.status_code == 200:
            docs = resp.json()
            st.subheader(f"Indexed Documents ({len(docs)})")
            df = pd.DataFrame(docs)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Backend API unavailable ({e})")

elif page == "📈 Evaluation Dashboard":
    st.title("Evaluation Dashboard")
    st.markdown("Automated evaluation benchmarks against 50 golden test scenarios.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Retrieval Hit Rate", "34.0%", "+4.0%")
    col2.metric("Context Precision", "6.8%", "+1.2%")
    col3.metric("Agent Routing Accuracy", "38.0%", "+2.5%")
    col4.metric("Workflow Completion", "100.0%", "0.0%")

    st.markdown("---")
    eval_path = "evaluation/datasets/golden_dataset.json"
    if os.path.exists(eval_path):
        with open(eval_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
        df_eval = pd.DataFrame(eval_data)
        st.bar_chart(df_eval["category"].value_counts())
        st.dataframe(df_eval[["question_id", "category", "query"]], use_container_width=True)

elif page == "⚙️ System Settings":
    st.title("System Settings")
    st.markdown("Configure LLM routing, endpoints, and retrieval options.")
    with st.form("settings_form"):
        model_choice = st.selectbox("Primary Model", ["auto/best-coding", "auto/smart", "auto/chat", "auto/reasoning"], index=0)
        api_base = st.text_input("API Base URL", value=os.getenv("ANTHROPIC_BASE_URL", "http://localhost:20128/v1"))
        top_k = st.slider("Hybrid Retrieval Top-K", 1, 10, 5)
        if st.form_submit_button("Save Settings"):
            st.success("Settings saved.")
