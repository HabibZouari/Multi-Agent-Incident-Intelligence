from typing import Optional
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from backend.core.config import settings
from backend.core.logger import logger

class SupervisorAgent:
    def __init__(self, model_override: Optional[str] = None):
        self.model = model_override or settings.default_model
        self.llm = ChatAnthropic(
            model=self.model,
            temperature=0.1,
            api_key=settings.anthropic_api_key or None,
            base_url=settings.anthropic_base_url or None
        )

    def classify_intent(self, query: str) -> str:
        logger.info(f"Supervisor classifying query with model {self.model}: {query}")
        prompt = f"""Classify the following incident inquiry into one of these categories:
1. 'knowledge': requires searching technical documentation or runbooks.
2. 'incident': requires searching historical incidents, deployments, or service dependencies.
3. 'comprehensive': requires both knowledge retrieval and incident/operational investigation.

User Query: "{query}"

Return ONLY the category name: knowledge, incident, or comprehensive."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        category = response.content.strip().lower()
        if category not in ["knowledge", "incident", "comprehensive"]:
            category = "comprehensive"
        logger.info(f"Classified category: {category}")
        return category
