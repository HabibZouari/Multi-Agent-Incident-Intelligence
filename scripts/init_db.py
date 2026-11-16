#!/usr/bin/env python3
"""Database initialisation & seeding for ResolveAI.

Loads the generated JSON datasets and the markdown knowledge base into PostgreSQL (or the SQLite
fallback). It is idempotent: if the database is already seeded it does nothing, unless --reset is given,
which drops and recreates every table.

Usage:  PYTHONPATH=. python scripts/init_db.py [--reset]
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from backend.models.db import (
    Base,
    DeploymentModel,
    EvalDatasetModel,
    IncidentModel,
    ServiceModel,
    SessionLocal,
    create_schema,
    engine,
)
from backend.rag.ingest import index_document
from backend.rag.retrieval import get_retriever

GENERATED_DIR = Path("data/generated")
EVAL_PATH = Path("evaluation/datasets/golden_dataset.json")
KNOWLEDGE_DIRS = {Path("data/documents"): "technical_doc", Path("data/runbooks"): "runbook"}


def _load(name: str) -> list[dict]:
    path = GENERATED_DIR / name
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run `python scripts/generate_dataset.py` first.")
    return json.loads(path.read_text(encoding="utf-8"))


def _is_seeded() -> bool:
    try:
        with SessionLocal() as session:
            return session.query(ServiceModel).count() > 0
    except Exception:  # noqa: BLE001 - tables do not exist yet
        return False


def init_database(reset: bool = False) -> None:
    target = engine.url.render_as_string(hide_password=True)
    if not reset and _is_seeded():
        print(f"{target} is already seeded; nothing to do (use --reset to rebuild).")
        return
    print(f"Recreating schema on {target} ...")
    Base.metadata.drop_all(bind=engine)
    create_schema()

    retriever = get_retriever()
    with SessionLocal() as session:
        print("Seeding services, deployments and incidents...")
        session.add_all(ServiceModel(**s) for s in _load("services.json"))
        session.add_all(
            DeploymentModel(**{**d, "deployed_at": datetime.fromisoformat(d["deployed_at"])}) for d in _load("deployments.json")
        )
        session.add_all(
            IncidentModel(
                **{
                    **{k: v for k, v in inc.items() if k != "service_id"},
                    "created_at": datetime.fromisoformat(inc["created_at"]),
                    "resolved_at": datetime.fromisoformat(inc["resolved_at"]),
                }
            )
            for inc in _load("incidents.json")
        )

        if EVAL_PATH.exists():
            print("Seeding golden evaluation dataset...")
            session.add_all(EvalDatasetModel(**eq) for eq in json.loads(EVAL_PATH.read_text(encoding="utf-8")))

        print("Indexing knowledge base (chunk + embed)...")
        docs = chunks = 0
        for directory, default_type in KNOWLEDGE_DIRS.items():
            for path in sorted(directory.glob("*.md")):
                chunks += index_document(
                    session, path.read_text(encoding="utf-8"), path.name, document_type=default_type, retriever=retriever
                )
                docs += 1
        session.commit()

    retriever.refresh()
    print(f"Done: {docs} documents / {chunks} chunks indexed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the ResolveAI database.")
    parser.add_argument("--reset", action="store_true", help="drop and recreate all tables before seeding")
    init_database(reset=parser.parse_args().reset)
