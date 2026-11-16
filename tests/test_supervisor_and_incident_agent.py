import pytest

from backend.agents.incident_agent import IncidentAgent, match_services
from backend.agents.supervisor import SupervisorAgent, heuristic_route
from backend.core.taxonomy import CATEGORY_KEYWORDS, match_categories
from backend.models.db import ServiceModel, SessionLocal


@pytest.mark.parametrize(
    ("query", "route"),
    [
        ("What is the runbook procedure for a kafka consumer lag spike?", "knowledge"),
        ("How do I troubleshoot connection pool exhaustion?", "knowledge"),
        ("Have we seen this before? Show similar past incidents.", "incident"),
        ("What recent deployments were made to Payment Processing Gateway?", "incident"),
        ("Which services does the Kong API Gateway depend on?", "incident"),
        ("Which runbook applies, and has it happened on Auth recently?", "comprehensive"),
        ("Something is wrong in production, can you help?", "comprehensive"),
    ],
)
def test_heuristic_routing(query, route):
    assert heuristic_route(query) == route


def test_supervisor_without_api_key_uses_heuristic():
    supervisor = SupervisorAgent()
    assert supervisor.classify_intent("What is the runbook for SSL renewal?") == "knowledge"
    assert supervisor.last_method == "heuristic"


def test_match_categories_ranks_by_keyword_hits():
    assert match_categories("kafka consumer lag backlog")[0] == "Kafka Consumer Lag Spike"
    assert match_categories("hello world") == []


def test_every_generator_category_has_keywords():
    from scripts.generate_dataset import INCIDENT_CATEGORIES

    assert set(INCIDENT_CATEGORIES) == set(CATEGORY_KEYWORDS)


def test_match_services_prefers_best_distinctive_match():
    with SessionLocal() as session:
        services = session.query(ServiceModel).all()
    assert match_services("errors on the Payment Processing Gateway", services) == ["Payment Processing Gateway"]
    assert match_services("user postgresql slow", services) == ["User PostgreSQL DB"]
    assert match_services("something unrelated entirely", services) == []


def test_incident_agent_finds_related_incidents_and_service_deployments():
    result = IncidentAgent().investigate("Authentication service login failures after deployment")
    assert result["historical_incidents"][0]["incident_id"] == "INC-0001"
    assert result["matched_services"] == ["Authentication Service"]
    assert all(d["service_name"] == "Authentication Service" for d in result["deployments"])


def test_incident_agent_without_anchor_returns_no_incidents():
    result = IncidentAgent().investigate("hello there")
    assert result["historical_incidents"] == []
