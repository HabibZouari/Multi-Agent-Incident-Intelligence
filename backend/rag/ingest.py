"""Document ingestion: chunk -> embed -> store. Shared by the seeding script and the upload endpoint."""

from pathlib import Path

from sqlalchemy.orm import Session

from backend.models.db import DocumentModel
from backend.rag.chunking import chunk_markdown, parse_doc_metadata
from backend.rag.retrieval import HybridRetriever, get_retriever

DOCUMENT_TYPES = ("runbook", "technical_doc", "architecture_guide")
DEFAULT_SERVICE = "All Services"


def index_document(
    session: Session,
    text: str,
    filename: str,
    document_type: str | None = None,
    service_name: str | None = None,
    retriever: HybridRetriever | None = None,
) -> int:
    """Index one markdown document, replacing any previous version. Returns the number of chunks stored.

    Metadata found in the document header (``**Service:** ... | **Type:** ...``) wins over the
    arguments, so generated runbooks keep their own service and type.
    """
    retriever = retriever or get_retriever()
    header = parse_doc_metadata(text)
    document_type = header.get("type") or document_type or "technical_doc"
    service_name = header.get("service") or service_name or DEFAULT_SERVICE
    document_id = Path(filename).stem

    session.query(DocumentModel).filter(DocumentModel.document_id == document_id).delete()
    chunks = chunk_markdown(text)
    for idx, chunk in enumerate(chunks):
        session.add(
            DocumentModel(
                document_id=document_id,
                filename=filename,
                document_type=document_type,
                service_name=service_name,
                chunk_id=idx,
                content=chunk,
                embedding=retriever.get_embedding(chunk),
                metadata_json={"source": filename},
            )
        )
    session.flush()
    return len(chunks)
