from backend.core.llm import build_llm, complete
from backend.core.logger import logger

PROMPT = """You are an Incident Response Lead. Using the diagnosis below, write a concise troubleshooting plan:
numbered, actionable steps in the order they should be executed, each with a verification check, followed by an
escalation path. Do not invent evidence that is not in the diagnosis. Any step that changes production (rollbacks,
restarts, config changes) must be flagged as REQUIRES HUMAN APPROVAL.

User Query: {query}

Diagnosis:
{diagnosis}
"""

FALLBACK_STEPS = """
### Recommended next steps
1. Confirm scope: check error rates and latency dashboards for the affected service and its dependencies.
2. Review recent deployments and configuration changes in the incident window.
3. Follow the referenced runbook(s) step by step; verify each step against live metrics.
4. **REQUIRES HUMAN APPROVAL** before any rollback, restart or configuration change in production.
5. Escalate to the service owner if the issue is unresolved after 30 minutes."""


class ActionPlanningAgent:
    """Turns diagnoses into an ordered, verifiable troubleshooting plan."""

    def __init__(self, model_override: str | None = None):
        self.llm = build_llm(model_override)

    def plan(self, diagnoses: list[str], query: str = "") -> str:
        logger.info("ActionPlanningAgent generating troubleshooting plan")
        diagnosis = "\n".join(diagnoses)
        answer = complete(self.llm, PROMPT.format(query=query, diagnosis=diagnosis))
        return answer if answer else f"{diagnosis}\n{FALLBACK_STEPS}"
