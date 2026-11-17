import pytest
from fastapi.testclient import TestClient

import backend.api.main as api
from backend.api.main import app
from backend.rag.retrieval import get_retriever

client = TestClient(app)


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "UPLOAD_DIR", tmp_path / "uploads")
    return tmp_path / "uploads"


def test_health():
    body = client.get("/health").json()
    assert body["status"] == "healthy"
    assert body["llm_enabled"] is False
    assert body["database"] == "sqlite"


def test_services_and_deployments():
    services = client.get("/api/services").json()
    assert {s["name"] for s in services} >= {"Authentication Service", "Payment Processing Gateway"}
    deployments = client.get("/api/deployments", params={"service_name": "Payment"}).json()
    assert [d["deployment_id"] for d in deployments] == ["dep-001"]


def test_incidents_filters_and_includes_symptoms():
    everything = client.get("/api/incidents").json()
    assert len(everything) == 3
    assert "symptoms" in everything[0]
    assert [i["incident_id"] for i in client.get("/api/incidents", params={"severity": "p1"}).json()] == ["INC-0001"]
    assert [i["incident_id"] for i in client.get("/api/incidents", params={"q": "leak"}).json()] == ["INC-0002"]


@pytest.mark.parametrize("params", [{"severity": "P9"}, {"limit": 0}, {"limit": 9999}])
def test_incidents_rejects_invalid_params(params):
    assert client.get("/api/incidents", params=params).status_code == 422


def test_documents_report_chunk_counts():
    docs = client.get("/api/documents").json()
    assert len(docs) >= 5
    assert all(d["chunks"] >= 2 for d in docs)


def test_search_endpoint():
    hits = client.get("/api/search", params={"q": "kafka consumer lag"}).json()
    assert hits[0]["filename"] == "kafka-guide-02.md"
    assert client.get("/api/search", params={"q": "x"}).status_code == 422


def test_investigate_returns_full_payload_without_llm():
    response = client.post("/api/investigate", json={"query": "What is the runbook procedure for kafka consumer lag?"})
    assert response.status_code == 200
    body = response.json()
    assert body["classification"] == "knowledge"
    assert body["retrieved_docs"]
    assert body["final_response"]
    assert body["execution_trace"]


@pytest.mark.parametrize("payload", [{"query": "ab"}, {}, {"query": "x" * 2001}])
def test_investigate_validates_input(payload):
    assert client.post("/api/investigate", json=payload).status_code == 422


def test_investigate_hides_internal_errors(monkeypatch):
    def boom(**_):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(api, "run_investigation", boom)
    response = client.post("/api/investigate", json={"query": "anything goes here"})
    assert response.status_code == 500
    assert "secret" not in response.text


def test_upload_indexes_and_makes_document_searchable(upload_dir):
    content = "# Zebra Cache Runbook\n\n## Overview\nHandling zebrafish telemetry outages.\n"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("zebra.md", content.encode())},
        data={"document_type": "runbook", "service_name": "Zebra Service"},
    )
    assert response.status_code == 200
    assert response.json()["chunks"] >= 1
    assert (upload_dir / "zebra.md").exists()
    assert get_retriever().search("zebrafish telemetry")[0]["filename"] == "zebra.md"


def test_upload_blocks_path_traversal(upload_dir):
    response = client.post("/api/documents/upload", files={"file": ("../../evil.md", b"# Evil\n\n## A\nbody")})
    assert response.status_code == 200
    assert response.json()["filename"] == "evil.md"
    assert (upload_dir / "evil.md").exists()
    assert not (upload_dir.parent / "evil.md").exists()


@pytest.mark.parametrize(
    ("filename", "data", "form", "status"),
    [
        ("malware.exe", b"MZ", {}, 400),
        ("notes.md", b"\xff\xfe\x00bad", {}, 400),
        ("notes.md", b"# ok", {"document_type": "weird"}, 400),
        ("big.md", b"a" * 1_000_001, {}, 413),
    ],
)
def test_upload_rejects_bad_files(upload_dir, filename, data, form, status):
    assert client.post("/api/documents/upload", files={"file": (filename, data)}, data=form).status_code == status


def test_api_key_protects_api_routes_but_not_health(monkeypatch):
    monkeypatch.setattr(api.settings, "api_key", "test-secret")
    assert client.get("/health").status_code == 200
    assert client.get("/health").json()["api_auth"] is True
    assert client.get("/api/services").status_code == 401
    assert client.get("/api/services", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/api/services", headers={"X-API-Key": "test-secret"}).status_code == 200


def test_api_is_open_when_no_key_is_configured():
    assert client.get("/api/services").status_code == 200
    assert client.get("/health").json()["api_auth"] is False
