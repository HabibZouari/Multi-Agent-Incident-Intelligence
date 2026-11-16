import streamlit as st

result = st.session_state.get("last_result")

if not result:
    st.info("No investigation yet. Run one from the **Investigate** page first.", icon=":material/info:")
    st.stop()

st.caption(f"Query: _{result['query']}_")

st.subheader("Workflow trace")
for index, step in enumerate(result["execution_trace"], start=1):
    summary = step.get("action") or step.get("decision") or step.get("result") or "Step"
    with st.expander(f"{index}. {step['agent']} — {summary}"):
        st.json(step)

docs_col, incidents_col = st.columns(2)

with docs_col:
    st.subheader("Retrieved documentation")
    if not result["retrieved_docs"]:
        st.caption("No documents were retrieved for this route.")
    for doc in result["retrieved_docs"]:
        with st.container(border=True):
            st.markdown(f"**{doc['source']}**")
            st.caption(f"Fused score {doc['score']:.2f} · BM25 {doc['bm25_score']:.2f} · vector {doc['vector_score']:.2f} · {doc['service_name']}")
            st.text(doc["content"][:300])

with incidents_col:
    st.subheader("Correlated incidents")
    if not result["historical_incidents"]:
        st.caption("No historical incidents were correlated for this route.")
    for inc in result["historical_incidents"]:
        with st.container(border=True):
            st.markdown(f"**{inc['incident_id']}** · {inc['title']}")
            st.caption(f"Severity {inc['severity']} · {inc['service_name']}")
            st.write(f"**Root cause:** {inc['root_cause']}")
            st.write(f"**Resolution:** {inc['resolution']}")

if result["deployments"]:
    st.subheader("Recent deployments")
    st.dataframe(
        [{k: d[k] for k in ("service_name", "version", "status", "deployed_at")} for d in result["deployments"]],
        hide_index=True,
        alt="Recent deployments considered by the investigation",
    )
