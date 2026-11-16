from typing import List, Optional
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from backend.core.config import settings
from backend.core.logger import logger

class ActionPlanningAgent:
    def __init__(self, model_override: Optional[str] = None):
        self.model = model_override or settings.default_model
        self.llm = ChatAnthropic(
            model=self.model,
            temperature=0.1,
            api_key=settings.anthropic_api_key or None,
            base_url=settings.anthropic_base_url or None
        )

    def plan(self, diagnoses: List[str]) -> str:
        logger.info(f"ActionPlanningAgent generating troubleshooting plan with model {self.model}")
        diagnoses_text = "\n".join(diagnoses)
        prompt = f"""You are an Incident Response Lead. Based on the diagnosis and evidence, generate an actionable step-by-step troubleshooting plan and incident report.

Diagnoses:
{diagnoses_text}

Provide a structured, professional troubleshooting plan with clear verification steps."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content
