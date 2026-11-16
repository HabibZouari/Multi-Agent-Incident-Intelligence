import api_client
import pandas as pd
import streamlit as st

st.caption("Search and filter historical incidents. Select a row to read the full record.")

filter_col, search_col = st.columns([1, 2], vertical_alignment="bottom")
severity = filter_col.segmented_control("Severity", ["P1", "P2", "P3", "P4"], default=None, key="incident_severity")
keyword = search_col.text_input("Search title, symptoms or root cause", key="incident_keyword")

try:
    incidents = api_client.get_json("/api/incidents", {"severity": severity, "q": keyword or None, "limit": 200})
except api_client.BackendError as exc:
    st.error(str(exc), icon=":material/error:")
    st.stop()

st.markdown(f"Showing **{len(incidents)}** incidents")
if not incidents:
    st.info("No incidents match the current filters.", icon=":material/search_off:")
    st.stop()

frame = pd.DataFrame(incidents)
event = st.dataframe(
    frame[["incident_id", "severity", "service_name", "category", "status", "created_at"]],
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="incident_table",
    alt="Table of historical incidents",
)

selected_rows = event.selection.rows
if selected_rows:
    incident = incidents[selected_rows[0]]
    with st.container(border=True):
        st.subheader(f"{incident['incident_id']} · {incident['title']}")
        left, right = st.columns(2)
        left.write(f"**Service:** {incident['service_name']}")
        left.write(f"**Category:** {incident['category']}")
        right.write(f"**Severity:** {incident['severity']}")
        right.write(f"**Status:** {incident['status']} · opened {incident['created_at']}")
        st.write(f"**Symptoms:** {incident['symptoms']}")
        st.write(f"**Root cause:** {incident['root_cause']}")
        st.write(f"**Resolution:** {incident['resolution']}")
