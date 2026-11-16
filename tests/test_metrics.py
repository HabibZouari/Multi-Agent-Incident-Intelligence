from evaluation.metrics.agent_metrics import path_adherence, routing_accuracy, workflow_completed
from evaluation.metrics.rag_metrics import context_precision, hit_rate, reciprocal_rank

RETRIEVED = [{"filename": "a.md"}, {"filename": "x.md"}, {"filename": "b.md"}]


def test_hit_rate():
    assert hit_rate(RETRIEVED, ["b.md"]) == 1.0
    assert hit_rate(RETRIEVED, ["zzz.md"]) == 0.0
    assert hit_rate([], ["a.md"]) == 0.0


def test_context_precision_uses_exact_filenames():
    assert context_precision(RETRIEVED, ["a.md", "b.md"]) == 2 / 3
    assert context_precision(RETRIEVED, ["a"]) == 0.0  # substring must not count
    assert context_precision([], ["a.md"]) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank(RETRIEVED, ["a.md"]) == 1.0
    assert reciprocal_rank(RETRIEVED, ["b.md"]) == 1 / 3
    assert reciprocal_rank(RETRIEVED, ["none.md"]) == 0.0


def test_routing_accuracy_is_case_insensitive():
    assert routing_accuracy("Knowledge", "knowledge") == 1.0
    assert routing_accuracy("incident", "knowledge") == 0.0


def _result(agents, final="text"):
    trace = [{"agent": "Supervisor", "action": "x"}] + [{"agent": a, "result": "ok"} for a in agents]
    return {"execution_trace": trace, "final_response": final}


def test_workflow_completed_requires_planner_and_answer():
    assert workflow_completed(_result(["KnowledgeRetrievalAgent", "ActionPlanningAgent"])) == 1.0
    assert workflow_completed(_result(["KnowledgeRetrievalAgent"])) == 0.0
    assert workflow_completed(_result(["ActionPlanningAgent"], final="")) == 0.0


def test_path_adherence_flags_unnecessary_and_missing_agents():
    assert path_adherence("knowledge", _result(["KnowledgeRetrievalAgent"])) == 1.0
    assert path_adherence("knowledge", _result(["KnowledgeRetrievalAgent", "IncidentInvestigationAgent"])) == 0.0
    assert path_adherence("comprehensive", _result(["KnowledgeRetrievalAgent"])) == 0.0
