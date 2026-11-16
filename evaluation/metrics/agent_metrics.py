"""Agent / workflow metrics computed from real workflow executions."""

from typing import Any

# Agents that must (and must not) run for each supervisor route.
EXPECTED_AGENTS: dict[str, tuple[set[str], set[str]]] = {
    "knowledge": ({"KnowledgeRetrievalAgent"}, {"IncidentInvestigationAgent"}),
    "incident": ({"IncidentInvestigationAgent"}, {"KnowledgeRetrievalAgent"}),
    "comprehensive": ({"KnowledgeRetrievalAgent", "IncidentInvestigationAgent"}, set()),
}


def routing_accuracy(predicted: str, expected: str) -> float:
    return 1.0 if predicted.strip().lower() == expected.strip().lower() else 0.0


def _agents_run(trace: list[dict[str, Any]]) -> set[str]:
    return {step["agent"] for step in trace if "result" in step}


def workflow_completed(result: dict[str, Any]) -> float:
    """1.0 when the supervisor ran, the action planner finished and a final answer was produced."""
    agents = _agents_run(result.get("execution_trace", []))
    supervisor_ran = any(s.get("agent") == "Supervisor" for s in result.get("execution_trace", []))
    return 1.0 if supervisor_ran and "ActionPlanningAgent" in agents and result.get("final_response") else 0.0


def path_adherence(route: str, result: dict[str, Any]) -> float:
    """1.0 when exactly the agents required by `route` ran (no missing and no unnecessary agent calls)."""
    required, forbidden = EXPECTED_AGENTS[route]
    agents = _agents_run(result.get("execution_trace", []))
    return 1.0 if required <= agents and not (forbidden & agents) else 0.0
