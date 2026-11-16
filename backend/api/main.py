from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, or_

from backend.core.config import settings
from backend.core.logger import logger
from backend.models.db import (
    IS_POSTGRES,
    DeploymentModel,
    DocumentModel,
    IncidentModel,
    ServiceModel,
    SessionLocal,
)
from backend.orchestration.workflow import run_investigation
from backend.rag.ingest import DOCUMENT_TYPES, index_document
from backend.rag.retrieval import get_retriever

VERSION = "1.1.0"
UPLOAD_DIR = Path("data/documents")
ALLOWED_UPLOAD_SUFFIXES = {".md", ".txt"}
MAX_UPLOAD_BYTES = 1_000_000

app = FastAPI(
    title="ResolveAI API",
    description="Multi-Agent Incident Intelligence & Troubleshooting Platform API",
    version=VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class InvestigationRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    service_filter: str | None = None
    model: str | None = None


class InvestigationResponse(BaseModel):
    query: str
    classification: str
    final_response: str
    retrieved_docs: list[dict[str, Any]]
    historical_incidents: list[dict[str, Any]]
    deployments: list[dict[str, Any]]
    execution_trace: list[dict[str, Any]]


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ResolveAI Backend",
        "version": VERSION,
        "database": "postgresql" if IS_POSTGRES else "sqlite",
        "llm_enabled": settings.llm_enabled,
    }


@app.post("/api/investigate", response_model=InvestigationResponse)
def investigate_incident(req: InvestigationRequest):
    try:
        result = run_investigation(query=req.query, model_override=req.model, service_filter=req.service_filter)
    except Exception:
        logger.exception("Investigation failed")
        raise HTTPException(status_code=500, detail="Investigation failed. Check the server logs for details.") from None
    return InvestigationResponse(
        query=req.query,
        classification=result.get("classification", "comprehensive"),
        final_response=result.get("final_response", ""),
        retrieved_docs=result.get("retrieved_docs", []),
        historical_incidents=result.get("historical_incidents", []),
        deployments=result.get("deployments", []),
        execution_trace=result.get("execution_trace", []),
    )


@app.get("/api/incidents")
def get_incidents(
    severity: str | None = Query(None, pattern="^(?i:P[1-4])$"),
    q: str | None = Query(None, max_length=100, description="Keyword matched against title, symptoms and root cause"),
    limit: int = Query(50, ge=1, le=500),
):
    with SessionLocal() as session:
        query = session.query(IncidentModel)
        if severity:
            query = query.filter(IncidentModel.severity == severity.upper())
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(IncidentModel.title.ilike(like), IncidentModel.symptoms.ilike(like), IncidentModel.root_cause.ilike(like))
            )
        incidents = query.order_by(IncidentModel.created_at.desc()).limit(limit).all()
        return [
            {
                "incident_id": inc.incident_id,
                "title": inc.title,
                "severity": inc.severity,
                "service_name": inc.service_name,
                "category": inc.category,
                "status": inc.status,
                "symptoms": inc.symptoms,
                "root_cause": inc.root_cause,
                "resolution": inc.resolution,
                "created_at": inc.created_at.isoformat() if inc.created_at else None,
            }
            for inc in incidents
        ]


@app.get("/api/services")
def get_services():
    with SessionLocal() as session:
        return [
            {"service_id": s.service_id, "name": s.name, "tier": s.tier, "owner": s.owner, "dependencies": s.dependencies}
            for s in session.query(ServiceModel).order_by(ServiceModel.name).all()
        ]


@app.get("/api/deployments")
def get_deployments(service_name: str | None = None, limit: int = Query(20, ge=1, le=200)):
    with SessionLocal() as session:
        query = session.query(DeploymentModel)
        if service_name:
            query = query.filter(DeploymentModel.service_name.ilike(f"%{service_name}%"))
        return [
            {
                "deployment_id": d.deployment_id,
                "service_name": d.service_name,
                "version": d.version,
                "status": d.status,
                "author": d.author,
                "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None,
            }
            for d in query.order_by(DeploymentModel.deployed_at.desc()).limit(limit).all()
        ]


@app.get("/api/documents")
def get_documents():
    with SessionLocal() as session:
        rows = (
            session.query(
                DocumentModel.document_id,
                DocumentModel.filename,
                DocumentModel.document_type,
                DocumentModel.service_name,
                func.count(DocumentModel.chunk_id).label("chunks"),
            )
            .group_by(
                DocumentModel.document_id, DocumentModel.filename, DocumentModel.document_type, DocumentModel.service_name
            )
            .order_by(DocumentModel.filename)
            .all()
        )
        return [
            {"document_id": r.document_id, "filename": r.filename, "document_type": r.document_type, "service_name": r.service_name, "chunks": r.chunks}
            for r in rows
        ]


@app.get("/api/search")
def search_knowledge_base(
    q: str = Query(..., min_length=2, max_length=500),
    top_k: int = Query(5, ge=1, le=20),
    service: str | None = None,
):
    """Hybrid (vector + BM25) search over the indexed runbooks and documentation."""
    return get_retriever().search(q, top_k=top_k, service_filter=service)


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("technical_doc"),
    service_name: str = Form("All Services"),
):
    # Never trust the client-supplied name: keep only the final path component (blocks ../ traversal).
    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only .md and .txt files are supported.")
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail=f"document_type must be one of {', '.join(DOCUMENT_TYPES)}.")

    payload = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (limit 1 MB).")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 text.") from None

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / filename).write_text(text, encoding="utf-8")

    with SessionLocal() as session:
        chunks = index_document(session, text, filename, document_type=document_type, service_name=service_name)
        session.commit()
    get_retriever().refresh()
    return {"filename": filename, "status": "indexed", "chunks": chunks}
