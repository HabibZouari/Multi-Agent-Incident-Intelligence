"""LangGraph workflow wiring the Supervisor and the specialised agents together.

            +-> knowledge ----------------------------+
 supervisor |                                         +-> diagnostic -> action_planning -> END
            +-> incident -----------------------------+
            +-> knowledge -> incident (comprehensive) +
"""

from typing import Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph

from backend.agents.action_agent import ActionPlanningAgent
from backend.agents.diagnostic_agent import DiagnosticAgent
from backend.agents.incident_agent import IncidentAgent
from backend.agents.knowledge_agent import KnowledgeAgent
from backend.agents.supervisor import SupervisorAgent


class IncidentState(TypedDict):
    messages: list[BaseMessage]
    user_query: str
    service_filter: str | None
    classification: str
    retrieved_docs: list[dict[str, Any]]
    historical_incidents: list[dict[str, Any]]
    deployments: list[dict[str, Any]]
    matched_services: list[str]
    diagnoses: list[str]
    action_plan: list[str]
    final_response: str
    execution_trace: list[dict[str, Any]]
    model_override: str | None


def _trace(state: IncidentState, *entries: dict[str, Any]) -> list[dict[str, Any]]:
    return [*state.get("execution_trace", []), *entries]


def build_workflow(model_override: str | None = None):
    """Compile the investigation graph. Agents are created once per graph, not once per node call."""
    supervisor = SupervisorAgent(model_override)
    knowledge_agent = KnowledgeAgent()
    incident_agent = IncidentAgent()
    diagnostic_agent = DiagnosticAgent(model_override)
    action_agent = ActionPlanningAgent(model_override)

    def supervisor_node(state: IncidentState) -> dict[str, Any]:
        category = supervisor.classify_intent(state["user_query"])
        return {
            "classification": category,
            "execution_trace": _trace(
                state,
                {"agent": "Supervisor", "action": "Analysing intent and deciding collaboration scope", "query": state["user_query"]},
                {"agent": "Supervisor", "decision": f"Routing to intent category: {category}", "method": supervisor.last_method},
            ),
        }

    def knowledge_node(state: IncidentState) -> dict[str, Any]:
        docs = knowledge_agent.search_docs(state["user_query"], top_k=3, service_filter=state.get("service_filter"))
        return {
            "retrieved_docs": docs,
            "execution_trace": _trace(
                state,
                {"agent": "KnowledgeRetrievalAgent", "action": "Hybrid retrieval (vector + BM25) over runbooks and documentation"},
                {"agent": "KnowledgeRetrievalAgent", "result": f"Retrieved {len(docs)} document chunks", "sources": [d["source"] for d in docs]},
            ),
        }

    def incident_node(state: IncidentState) -> dict[str, Any]:
        result = incident_agent.investigate(state["user_query"])
        return {
            "historical_incidents": result["historical_incidents"],
            "deployments": result["deployments"],
            "matched_services": result["matched_services"],
            "execution_trace": _trace(
                state,
                {"agent": "IncidentInvestigationAgent", "action": "Querying historical incidents and deployments"},
                {
                    "agent": "IncidentInvestigationAgent",
                    "result": f"Found {len(result['historical_incidents'])} incidents, {len(result['deployments'])} deployments",
                    "matched_services": result["matched_services"],
                },
            ),
        }

    def diagnostic_node(state: IncidentState) -> dict[str, Any]:
        diagnoses = diagnostic_agent.analyze(
            query=state["user_query"],
            docs=state.get("retrieved_docs", []),
            incidents=state.get("historical_incidents", []),
            deployments=state.get("deployments", []),
        )
        return {
            "diagnoses": diagnoses,
            "execution_trace": _trace(
                state,
                {"agent": "DiagnosticAgent", "action": "Synthesising evidence into root-cause hypotheses"},
                {"agent": "DiagnosticAgent", "result": "Generated root-cause hypotheses"},
            ),
        }

    def action_node(state: IncidentState) -> dict[str, Any]:
        plan = action_agent.plan(state.get("diagnoses", []), query=state["user_query"])
        return {
            "action_plan": [plan],
            "final_response": plan,
            "execution_trace": _trace(
                state,
                {"agent": "ActionPlanningAgent", "action": "Generating troubleshooting plan"},
                {"agent": "ActionPlanningAgent", "result": "Generated action plan and final report"},
            ),
        }

    def route_from_supervisor(state: IncidentState) -> str:
        return "incident_agent" if state["classification"] == "incident" else "knowledge_agent"

    def route_from_knowledge(state: IncidentState) -> str:
        return "incident_agent" if state["classification"] == "comprehensive" else "diagnostic_agent"

    graph = StateGraph(IncidentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("knowledge_agent", knowledge_node)
    graph.add_node("incident_agent", incident_node)
    graph.add_node("diagnostic_agent", diagnostic_node)
    graph.add_node("action_agent", action_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor", route_from_supervisor, {"knowledge_agent": "knowledge_agent", "incident_agent": "incident_agent"}
    )
    graph.add_conditional_edges(
        "knowledge_agent", route_from_knowledge, {"incident_agent": "incident_agent", "diagnostic_agent": "diagnostic_agent"}
    )
    graph.add_edge("incident_agent", "diagnostic_agent")
    graph.add_edge("diagnostic_agent", "action_agent")
    graph.add_edge("action_agent", END)
    return graph.compile()


def run_investigation(query: str, model_override: str | None = None, service_filter: str | None = None) -> dict[str, Any]:
    initial_state: IncidentState = {
        "messages": [],
        "user_query": query,
        "service_filter": service_filter,
        "classification": "",
        "retrieved_docs": [],
        "historical_incidents": [],
        "deployments": [],
        "matched_services": [],
        "diagnoses": [],
        "action_plan": [],
        "final_response": "",
        "execution_trace": [],
        "model_override": model_override,
    }
    return build_workflow(model_override).invoke(initial_state)
