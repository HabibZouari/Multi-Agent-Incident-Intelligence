import pytest

from backend.orchestration.workflow import run_investigation
from evaluation.metrics.agent_metrics import path_adherence, workflow_completed


def _agents(result):
    return [s["agent"] for s in result["execution_trace"] if "result" in s]


@pytest.mark.parametrize(
    ("query", "route", "expected_agents", "absent_agents"),
    [
        (
            "What is the runbook procedure for a kafka consumer lag spike?",
            "knowledge", {"KnowledgeRetrievalAgent"}, {"IncidentInvestigationAgent"},
        ),
        (
            "What recent deployments were made to Payment Processing Gateway?",
            "incident", {"IncidentInvestigationAgent"}, {"KnowledgeRetrievalAgent"},
        ),
        (
            "Which runbook applies to authentication failures and has it happened recently?",
            "comprehensive", {"KnowledgeRetrievalAgent", "IncidentInvestigationAgent"}, set(),
        ),
    ],
)
def test_each_route_runs_only_the_needed_agents(query, route, expected_agents, absent_agents):
    result = run_investigation(query)
    agents = set(_agents(result))
    assert result["classification"] == route
    assert expected_agents <= agents
    assert not (absent_agents & agents)
    assert {"DiagnosticAgent", "ActionPlanningAgent"} <= agents
    assert result["final_response"]
    assert workflow_completed(result) == 1.0
    assert path_adherence(route, result) == 1.0


def test_offline_report_cites_retrieved_sources():
    result = run_investigation("What is the runbook procedure for a kafka consumer lag spike?")
    assert any("kafka-guide-02.md" in doc["source"] for doc in result["retrieved_docs"])
    assert "REQUIRES HUMAN APPROVAL" in result["final_response"]


def test_vague_query_asks_for_details_instead_of_guessing():
    result = run_investigation("Something is wrong in production, can you help?")
    assert "provide the affected service" in result["final_response"].lower()


def test_service_filter_is_applied_to_retrieval():
    result = run_investigation("runbook procedure for kafka consumer lag", service_filter="Kafka Event Bus")
    assert result["retrieved_docs"]
    assert {d["service_name"] for d in result["retrieved_docs"]} <= {"Kafka Event Bus", "All Services"}


def test_trace_is_ordered_and_supervisor_first():
    trace = run_investigation("kafka runbook steps")["execution_trace"]
    assert trace[0]["agent"] == "Supervisor"
    assert trace[-1]["agent"] == "ActionPlanningAgent"


def test_unknown_service_yields_no_evidence_instead_of_noise():
    result = run_investigation("What was the root cause of last week's outage of Holographic Billing Engine?")
    assert result["retrieved_docs"] == []
    assert result["historical_incidents"] == []
    assert "provide the affected service" in result["final_response"].lower()
