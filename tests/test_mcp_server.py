import pytest

pytest.importorskip("mcp.server.fastmcp", reason="requires mcp 1.x (see requirements.txt)")

from mcp_server import server  # noqa: E402


def test_dependencies_include_reverse_edges():
    result = server.get_service_dependencies("Authentication")
    assert result["depends_on"] == ["User PostgreSQL DB"]
    assert result["depended_on_by"] == ["Payment Processing Gateway"]


def test_unknown_service_and_incident_are_reported_not_raised():
    assert "error" in server.get_service_dependencies("Nope")
    assert "error" in server.get_incident_details("INC-9999")


def test_statistics_and_search():
    stats = server.get_incident_statistics()
    assert stats["total"] == 3
    assert stats["by_severity"]["P1"] == 1
    assert [i["incident_id"] for i in server.search_incidents(keyword="leak")] == ["INC-0002"]


def test_checklist_requires_approval_and_cites_runbook():
    checklist = server.generate_troubleshooting_checklist("Kafka Consumer Lag Spike", "Kafka Event Bus")
    assert checklist["approval_required"] is True
    assert checklist["runbook"].startswith("kafka-guide-02.md")
