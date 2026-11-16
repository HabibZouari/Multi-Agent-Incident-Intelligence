import api_client
import streamlit as st

SCENARIOS = {
    "Auth service 500 errors": "Authentication service started returning HTTP 500 errors after yesterday's deployment. Have we experienced something similar before? What should we investigate?",
    "DB connection exhaustion": "Database connection pool is exhausted on User PostgreSQL DB. What runbook steps should we follow?",
    "Payment gateway deployments": "What recent deployments affected the Payment Processing Gateway?",
}

st.caption("Describe an incident or ask a troubleshooting question. A supervisor routes it to the agents that are needed.")

with st.container(horizontal=True):
    for label, scenario in SCENARIOS.items():
        if st.button(label, icon=":material/bolt:", key=f"scenario_{label}"):
            st.session_state["pending_prompt"] = scenario

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("route"):
            st.caption(f"Routed as **{message['route']}** · see *Agent monitor* for the full trace")

prompt = st.chat_input("Ask a troubleshooting question or describe an incident...", submit_mode="disable")
prompt = st.session_state.pop("pending_prompt", None) or prompt

if prompt:
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Agents are investigating..."):
                result = api_client.investigate(prompt, st.session_state.get("model"))
        except api_client.BackendError as exc:
            st.error(str(exc), icon=":material/error:")
        else:
            st.markdown(result["final_response"])
            st.caption(f"Routed as **{result['classification']}** · see *Agent monitor* for the full trace")
            st.session_state["last_result"] = result
            st.session_state["messages"].append(
                {"role": "assistant", "content": result["final_response"], "route": result["classification"]}
            )

if st.session_state["messages"] and st.button("Clear conversation", icon=":material/delete:"):
    st.session_state["messages"] = []
    st.session_state["last_result"] = None
    st.rerun()
