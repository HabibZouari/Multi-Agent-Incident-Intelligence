from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from backend.agents.supervisor import SupervisorAgent
from backend.agents.knowledge_agent import KnowledgeAgent
from backend.agents.incident_agent import IncidentAgent
from backend.agents.diagnostic_agent import DiagnosticAgent
from backend.agents.action_agent import ActionPlanningAgent

class IncidentState(TypedDict):
    messages: List[BaseMessage]
    user_query: str
    classification: str
    retrieved_docs: List[Dict[str, Any]]
    historical_incidents: List[Dict[str, Any]]
    deployments: List[Dict[str, Any]]
    service_info: Dict[str, Any]
    diagnoses: List[str]
    action_plan: List[str]
    final_response: str
    execution_trace: List[Dict[str, Any]]
    model_override: Optional[str]

def run_investigation(query: str, model_override: Optional[str] = None) -> Dict[str, Any]:
    supervisor = SupervisorAgent(model_override=model_override)
    knowledge_agent = KnowledgeAgent()
    incident_agent = IncidentAgent()
    diagnostic_agent = DiagnosticAgent(model_override=model_override)
    action_agent = ActionPlanningAgent(model_override=model_override)

    def supervisor_node(state: IncidentState) -> IncidentState:
        trace = state.get("execution_trace", [])
        trace.append({"agent": "Supervisor", "action": "Analyzing intent & deciding collaboration scope", "query": query})

        category = supervisor.classify_intent(query)
        trace.append({"agent": "Supervisor", "decision": f"Routing to intent category: {category}"})
        return {**state, "classification": category, "execution_trace": trace}

    def knowledge_agent_node(state: IncidentState) -> IncidentState:
        trace = state.get("execution_trace", [])
        trace.append({"agent": "KnowledgeRetrievalAgent", "action": "Executing hybrid retrieval on documentation"})

        docs = knowledge_agent.search_docs(query, top_k=3)
        trace.append({"agent": "KnowledgeRetrievalAgent", "result": f"Retrieved {len(docs)} document chunks"})
        return {**state, "retrieved_docs": docs, "execution_trace": trace}

    def incident_agent_node(state: IncidentState) -> IncidentState:
        trace = state.get("execution_trace", [])
        trace.append({"agent": "IncidentInvestigationAgent", "action": "Querying historical incidents and deployments"})

        result = incident_agent.investigate(query)
        inc_list = result["historical_incidents"]
        dep_list = result["deployments"]

        trace.append({"agent": "IncidentInvestigationAgent", "result": f"Found {len(inc_list)} incidents, {len(dep_list)} deployments"})
        return {**state, "historical_incidents": inc_list, "deployments": dep_list, "execution_trace": trace}

    def diagnostic_agent_node(state: IncidentState) -> IncidentState:
        trace = state.get("execution_trace", [])
        trace.append({"agent": "DiagnosticAgent", "action": "Synthesizing multi-domain evidence & generating root-cause hypotheses"})

        diagnoses = diagnostic_agent.analyze(
            query=state["user_query"],
            docs=state.get("retrieved_docs", []),
            incidents=state.get("historical_incidents", []),
            deployments=state.get("deployments", [])
        )
        trace.append({"agent": "DiagnosticAgent", "result": "Generated grounded root-cause hypotheses"})
        return {**state, "diagnoses": diagnoses, "execution_trace": trace}

    def action_planning_agent_node(state: IncidentState) -> IncidentState:
        trace = state.get("execution_trace", [])
        trace.append({"agent": "ActionPlanningAgent", "action": "Generating actionable troubleshooting plan & report"})

        # Pass diagnoses or fallback to all retrieved evidence if diagnoses is empty
        diagnoses_input = state.get("diagnoses", [])
        if not diagnoses_input:
            diagnoses_input = [
                f"User Query: {query}",
                f"Retrieved Docs: {len(state.get('retrieved_docs', []))}",
                f"Historical Incidents: {len(state.get('historical_incidents', []))}",
                f"Deployments: {len(state.get('deployments', []))}"
            ]

        final_text = action_agent.plan(diagnoses_input)
        trace.append({"agent": "ActionPlanningAgent", "result": "Generated action plan and final report"})
        return {**state, "action_plan": [final_text], "final_response": final_text, "execution_trace": trace}

    def route_decision(state: IncidentState) -> str:
        cat = state.get("classification", "comprehensive")
        if cat == "knowledge":
            return "knowledge_only"
        elif cat == "incident":
            return "incident_only"
        else:
            return "comprehensive_collaboration"

    workflow = StateGraph(IncidentState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("knowledge_agent", knowledge_agent_node)
    workflow.add_node("incident_agent", incident_agent_node)
    workflow.add_node("diagnostic_agent", diagnostic_agent_node)
    workflow.add_node("action_agent", action_planning_agent_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
    route_decision,
        {
            "knowledge_only": "knowledge_agent",
            "incident_only": "incident_agent",
            "comprehensive_collaboration": "knowledge_agent"
        }
    )

    # Ensure every branch eventually flows into diagnostic_agent before action_agent
    workflow.add_edge("knowledge_agent", "incident_agent")
    workflow.add_edge("incident_agent", "diagnostic_agent")
    workflow.add_edge("diagnostic_agent", "action_agent")
    workflow.add_edge("action_agent", END)

    app_workflow = workflow.compile()

    initial_state = {
        "messages": [],
        "user_query": query,
        "classification": "",
        "retrieved_docs": [],
        "historical_incidents": [],
        "deployments": [],
        "service_info": {},
        "diagnoses": [],
        "action_plan": [],
        "final_response": "",
        "execution_trace": [],
        "model_override": model_override
    }
    return app_workflow.invoke(initial_state)
