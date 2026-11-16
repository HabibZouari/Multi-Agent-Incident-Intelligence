from backend.core.llm import build_llm, complete
from backend.core.logger import logger
from backend.core.taxonomy import INCIDENT_SIGNALS, KNOWLEDGE_SIGNALS, has_signal

ROUTES = ("knowledge", "incident", "comprehensive")

CLASSIFY_PROMPT = """Classify the following incident inquiry into exactly one category:
- knowledge: needs documentation or runbooks only (procedures, how-tos, troubleshooting steps).
- incident: needs historical incidents, deployments or service dependencies only.
- comprehensive: needs both, or the request is vague / cannot be answered from a single source.

User Query: "{query}"

Return ONLY the category name: knowledge, incident, or comprehensive."""


def heuristic_route(query: str) -> str:
    """Keyword-based routing used when no LLM is available (and as a safety net for invalid LLM output)."""
    wants_docs = has_signal(query, KNOWLEDGE_SIGNALS)
    wants_records = has_signal(query, INCIDENT_SIGNALS)
    if wants_docs and not wants_records:
        return "knowledge"
    if wants_records and not wants_docs:
        return "incident"
    return "comprehensive"


class SupervisorAgent:
    """Classifies the user's intent so the workflow only invokes the agents that are needed."""

    def __init__(self, model_override: str | None = None):
        self.llm = build_llm(model_override)
        self.last_method = "heuristic"

    def classify_intent(self, query: str) -> str:
        logger.info("Supervisor classifying query: %s", query)
        answer = complete(self.llm, CLASSIFY_PROMPT.format(query=query))
        category = (answer or "").strip().strip("'\".").lower()
        if category in ROUTES:
            self.last_method = "llm"
        else:
            category, self.last_method = heuristic_route(query), "heuristic"
        logger.info("Classified as '%s' (%s)", category, self.last_method)
        return category
