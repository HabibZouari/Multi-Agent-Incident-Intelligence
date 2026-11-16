import api_client
import pandas as pd
import streamlit as st

DOCUMENT_TYPES = ["runbook", "technical_doc", "architecture_guide"]

search_tab, documents_tab, upload_tab = st.tabs(["Search", "Indexed documents", "Upload"], on_change="rerun")

with search_tab:
    if search_tab.open:
        st.caption("Hybrid retrieval: BM25 keyword ranking and vector similarity fused with Reciprocal Rank Fusion.")
        query = st.text_input("Search runbooks and documentation", key="kb_query", placeholder="e.g. kafka consumer lag")
        if query:
            try:
                hits = api_client.get_json("/api/search", {"q": query, "top_k": 5})
            except api_client.BackendError as exc:
                st.error(str(exc), icon=":material/error:")
            else:
                if not hits:
                    st.info("No matching documentation found.", icon=":material/search_off:")
                for hit in hits:
                    with st.container(border=True):
                        st.markdown(f"**{hit['source']}** · {hit['document_type']} · {hit['service_name']}")
                        st.caption(f"Fused score {hit['score']:.2f} · BM25 {hit['bm25_score']:.2f} · vector {hit['vector_score']:.2f}")
                        st.text(hit["content"][:400])

with documents_tab:
    if documents_tab.open:
        try:
            documents = api_client.get_json("/api/documents")
        except api_client.BackendError as exc:
            st.error(str(exc), icon=":material/error:")
        else:
            st.markdown(f"**{len(documents)}** documents indexed")
            st.dataframe(pd.DataFrame(documents), hide_index=True, alt="Indexed documents and their chunk counts")

with upload_tab:
    if upload_tab.open:
        with st.form("upload_form", clear_on_submit=True):
            uploaded = st.file_uploader("Markdown or text file", type=["md", "txt"])
            doc_type = st.selectbox("Document type", DOCUMENT_TYPES)
            service_name = st.text_input("Service name", "All Services")
            submitted = st.form_submit_button("Index document", icon=":material/upload:")
        if submitted:
            if uploaded is None:
                st.warning("Choose a file first.", icon=":material/warning:")
            else:
                try:
                    result = api_client.upload_document(uploaded.name, uploaded.getvalue(), doc_type, service_name)
                except api_client.BackendError as exc:
                    st.error(str(exc), icon=":material/error:")
                else:
                    api_client.get_json.clear()
                    st.success(f"Indexed {result['filename']} as {result['chunks']} chunks.", icon=":material/check_circle:")
