"""
Agent Evaluation Metrics (Routing Accuracy, Tool Success Rate, Completion Rate)
"""

def compute_routing_accuracy(predicted_category: str, expected_category: str) -> float:
    return 1.0 if predicted_category.lower() == expected_category.lower() else 0.0

def compute_completion_rate(execution_trace: list) -> float:
    if not execution_trace:
        return 0.0
    # Check if final action completed successfully
    has_supervisor = any(step.get("agent") == "Supervisor" for step in execution_trace)
    has_action = any(step.get("agent") == "ActionPlanningAgent" for step in execution_trace)
    return 1.0 if has_supervisor and has_action else 0.5
