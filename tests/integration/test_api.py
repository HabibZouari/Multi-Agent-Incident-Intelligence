import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_services():
    response = client.get("/api/services")
    assert response.status_code == 200
    services = response.json()
    assert isinstance(services, list)
    assert len(services) > 0

def test_get_incidents():
    response = client.get("/api/incidents?limit=5")
    assert response.status_code == 200
    incidents = response.json()
    assert isinstance(incidents, list)

def test_get_documents():
    response = client.get("/api/documents")
    assert response.status_code == 200
    docs = response.json()
    assert isinstance(docs, list)
