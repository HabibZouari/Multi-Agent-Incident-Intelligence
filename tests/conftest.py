"""Test configuration.

Environment is pinned *before* any backend module is imported so that tests are hermetic: an isolated
SQLite database, no LLM calls (empty API key) and no dependency on a developer's local `.env`.
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="resolveai-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP, 'test.db').as_posix()}"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["ANTHROPIC_BASE_URL"] = ""

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))  # the Streamlit app imports `api_client` as a sibling module

import pytest  # noqa: E402

from backend.models.db import DeploymentModel, IncidentModel, ServiceModel, SessionLocal, create_schema  # noqa: E402
from backend.rag.ingest import index_document  # noqa: E402
from backend.rag.retrieval import get_retriever  # noqa: E402


def make_doc(title: str, service: str, doc_type: str, topic: str, symptom: str, resolution: str) -> str:
    return f"""# {title}

> **Service:** {service} | **Type:** {doc_type} | **Topic:** {topic}

## Overview
Procedures for {topic.lower()} incidents affecting {service}.

## Common Symptoms & Indicators
- {symptom}

## Resolution & Mitigation
- {resolution}
"""


DOCS = {
    "auth-runbook-01.md": make_doc(
        "Authentication Troubleshooting Runbook", "Authentication Service", "runbook", "Authentication Failure",
        "Users see HTTP 401/500 errors when logging in and token validation fails.", "Synchronise the JWT signing secret and roll back the deployment."),
    "kafka-guide-02.md": make_doc(
        "Kafka Consumer Lag Troubleshooting Guide", "Kafka Event Bus", "runbook", "Kafka Consumer Lag Spike",
        "Event processing backlog increasing rapidly on a topic.", "Scale consumer pods and increase consumer group concurrency."),
    "redis-tuning-03.md": make_doc(
        "Redis Cache Eviction & Memory Tuning", "Redis Cache Cluster", "technical_doc", "Redis Cache Eviction Storm",
        "Cache misses and database CPU spikes under memory pressure.", "Set maxmemory-policy to allkeys-lru."),
    "dbpool-04.md": make_doc(
        "PostgreSQL Connection Pool Management", "User PostgreSQL DB", "technical_doc", "Database Connection Exhaustion",
        "Connection pool exhausted and queries time out.", "Restart pods to clear stale connections and fix the connection leak."),
    "general-05.md": make_doc(
        "Deployment & Rollback Procedures", "All Services", "runbook", "Deployment Regression",
        "Error rate spikes right after a release.", "Roll back to the previous stable version."),
}


@pytest.fixture(scope="session", autouse=True)
def seeded_database():
    create_schema()
    now = datetime.now()
    with SessionLocal() as session:
        session.add_all(
            [
                ServiceModel(service_id="srv-auth", name="Authentication Service", tier="Tier-1", owner="sec@example.com", dependencies=["srv-db-users"]),
                ServiceModel(service_id="srv-db-users", name="User PostgreSQL DB", tier="Tier-1", owner="dba@example.com", dependencies=[]),
                ServiceModel(service_id="srv-payment", name="Payment Processing Gateway", tier="Tier-1", owner="pay@example.com", dependencies=["srv-auth"]),
            ]
        )
        session.add_all(
            [
                IncidentModel(incident_id="INC-0001", title="[P1] Authentication Failure in Authentication Service", severity="P1",
                              service_name="Authentication Service", status="resolved", category="Authentication Failure",
                              symptoms="Users cannot log in.", root_cause="JWT secret mismatch.", resolution="Rolled back.", created_at=now - timedelta(days=3), resolved_at=now),
                IncidentModel(incident_id="INC-0002", title="[P2] Database Connection Exhaustion in User PostgreSQL DB", severity="P2",
                              service_name="User PostgreSQL DB", status="resolved", category="Database Connection Exhaustion",
                              symptoms="Pool exhausted.", root_cause="Connection leak.", resolution="Restarted pods.", created_at=now - timedelta(days=2), resolved_at=now),
                IncidentModel(incident_id="INC-0003", title="[P3] Deployment Regression in Payment Processing Gateway", severity="P3",
                              service_name="Payment Processing Gateway", status="resolved", category="Deployment Regression",
                              symptoms="500s after release.", root_cause="Missing migration.", resolution="Rolled back.", created_at=now - timedelta(days=1), resolved_at=now),
            ]
        )
        session.add_all(
            [
                DeploymentModel(deployment_id="dep-001", service_name="Payment Processing Gateway", service_id="srv-payment", version="v1.2.3",
                                deployed_at=now - timedelta(hours=5), author="dev@example.com", status="rollback", changes_summary="Refactor"),
                DeploymentModel(deployment_id="dep-002", service_name="Authentication Service", service_id="srv-auth", version="v1.0.1",
                                deployed_at=now - timedelta(hours=30), author="dev@example.com", status="success", changes_summary="Bump deps"),
            ]
        )
        for filename, text in DOCS.items():
            index_document(session, text, filename)
        session.commit()
    get_retriever().refresh()
    yield
