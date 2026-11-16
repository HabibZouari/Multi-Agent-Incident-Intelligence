import os
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.models.db import SessionLocal, IncidentModel, ServiceModel, DocumentModel, DeploymentModel
from backend.orchestration.workflow import run_investigation
from backend.rag.retrieval import HybridRetriever
import shutil
from pathlib import Path

app = FastAPI(
    title="ResolveAI API",
    description="Multi-Agent Incident Intelligence & Troubleshooting Platform API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

retriever = HybridRetriever()

class InvestigationRequest(BaseModel):
    query: str
    service_filter: Optional[str] = None
    model: Optional[str] = None

class InvestigationResponse(BaseModel):
    query: str
    classification: str
    final_response: str
    retrieved_docs: List[Dict[str, Any]]
    historical_incidents: List[Dict[str, Any]]
    deployments: List[Dict[str, Any]]
    execution_trace: List[Dict[str, Any]]

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ResolveAI Backend", "version": "1.0.0"}

@app.post("/api/investigate", response_model=InvestigationResponse)
def investigate_incident(req: InvestigationRequest):
    try:
        result = run_investigation(query=req.query, model_override=req.model)
        return InvestigationResponse(
            query=req.query,
            classification=result.get("classification", "comprehensive"),
            final_response=result.get("final_response", "Investigation completed."),
            retrieved_docs=result.get("retrieved_docs", []),
            historical_incidents=result.get("historical_incidents", []),
            deployments=result.get("deployments", []),
            execution_trace=result.get("execution_trace", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incidents")
def get_incidents(severity: Optional[str] = None, limit: int = 50):
    session = SessionLocal()
    try:
        query = session.query(IncidentModel)
        if severity:
            query = query.filter(IncidentModel.severity == severity.upper())
        incidents = query.order_by(IncidentModel.created_at.desc()).limit(limit).all()
        return [{
            "incident_id": inc.incident_id,
            "title": inc.title,
            "severity": inc.severity,
            "service_name": inc.service_name,
            "category": inc.category,
            "status": inc.status,
            "root_cause": inc.root_cause,
            "resolution": inc.resolution,
            "created_at": inc.created_at.isoformat() if inc.created_at else None
        } for inc in incidents]
    finally:
        session.close()

@app.get("/api/services")
def get_services():
    session = SessionLocal()
    try:
        services = session.query(ServiceModel).all()
        return [{
            "service_id": s.service_id,
            "name": s.name,
            "tier": s.tier,
            "owner": s.owner,
            "dependencies": s.dependencies
        } for s in services]
    finally:
        session.close()

@app.get("/api/documents")
def get_documents():
    session = SessionLocal()
    try:
        docs = session.query(DocumentModel.document_id, DocumentModel.filename, DocumentModel.document_type, DocumentModel.service_name).distinct().all()
        return [{
            "document_id": d.document_id,
            "filename": d.filename,
            "document_type": d.document_type,
            "service_name": d.service_name
        } for d in docs]
    finally:
        session.close()

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), document_type: str = Form("technical_doc"), service_name: str = Form("Core Services")):
    upload_dir = Path("data/documents")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": file.filename, "status": "uploaded", "message": "Document uploaded successfully. Run ingestion to index."}
