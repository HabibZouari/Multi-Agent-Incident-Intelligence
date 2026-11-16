#!/usr/bin/env python3
"""
Database Initialization & Seeding Script for ResolveAI
Loads generated JSON datasets and markdown files into PostgreSQL or SQLite fallback.
"""

import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import text
from backend.models.db import engine, SessionLocal, Base, ServiceModel, IncidentModel, DeploymentModel, EvalDatasetModel, DocumentModel
from backend.rag.retrieval import HybridRetriever

def init_database():
    print("Dropping and recreating database tables...")
    Base.metadata.drop_all(bind=engine)
    if "postgresql" in str(engine.url):
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception:
            pass
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    generated_dir = Path("data/generated")
    retriever = HybridRetriever()

    # 1. Seed Services
    print("Seeding services...")
    with open(generated_dir / "services.json", "r") as f:
        services_data = json.load(f)
    for s in services_data:
        session.add(ServiceModel(
            service_id=s["service_id"],
            name=s["name"],
            tier=s["tier"],
            owner=s["owner"],
            dependencies=s["dependencies"]
        ))

    # 2. Seed Deployments
    print("Seeding deployments...")
    with open(generated_dir / "deployments.json", "r") as f:
        deployments_data = json.load(f)
    for d in deployments_data:
        session.add(DeploymentModel(
            deployment_id=d["deployment_id"],
            service_name=d["service_name"],
            service_id=d["service_id"],
            version=d["version"],
            deployed_at=datetime.fromisoformat(d["deployed_at"]),
            author=d["author"],
            status=d["status"],
            changes_summary=d["changes_summary"]
        ))

    # 3. Seed Incidents
    print("Seeding incidents...")
    with open(generated_dir / "incidents.json", "r") as f:
        incidents_data = json.load(f)
    for inc in incidents_data:
        session.add(IncidentModel(
            incident_id=inc["incident_id"],
            title=inc["title"],
            severity=inc["severity"],
            service_name=inc["service_name"],
            status=inc["status"],
            category=inc["category"],
            symptoms=inc["symptoms"],
            root_cause=inc["root_cause"],
            resolution=inc["resolution"],
            created_at=datetime.fromisoformat(inc["created_at"]),
            resolved_at=datetime.fromisoformat(inc["resolved_at"])
        ))

    # 4. Seed Eval Dataset
    print("Seeding evaluation dataset...")
    eval_path = Path("evaluation/datasets/golden_dataset.json")
    if eval_path.exists():
        with open(eval_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
        for eq in eval_data:
            session.add(EvalDatasetModel(
                question_id=eq["question_id"],
                category=eq["category"],
                query=eq["query"],
                expected_answer=eq["expected_answer"],
                ground_truth_docs=eq["ground_truth_docs"],
                expected_tools=eq["expected_tools"]
            ))

    # 5. Seed Documents & Runbooks with consistent embeddings
    print("Seeding documents and runbooks...")
    doc_dirs = [Path("data/documents"), Path("data/runbooks")]
    for d_dir in doc_dirs:
        if d_dir.exists():
            for file_path in d_dir.glob("*.md"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                chunks = content.split("\n\n")
                for idx, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    vec = retriever.get_embedding(chunk)
                    doc_id = file_path.stem
                    session.add(DocumentModel(
                        document_id=doc_id,
                        filename=file_path.name,
                        document_type="runbook" if "runbooks" in str(d_dir) else "technical_doc",
                        service_name="Core Services",
                        chunk_id=idx,
                        content=chunk,
                        embedding=vec,
                        metadata_json={"source": str(file_path)}
                    ))

    session.commit()
    session.close()
    print("Database initialization and seeding completed successfully.")

if __name__ == "__main__":
    init_database()
