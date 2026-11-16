from typing import List, Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from backend.core.config import settings
from backend.core.logger import logger

class DiagnosticAgent:
    def __init__(self, model_override: Optional[str] = None):
        self.model = model_override or settings.default_model
        self.llm = ChatAnthropic(
            model=self.model,
            temperature=0.1,
            api_key=settings.anthropic_api_key or None,
            base_url=settings.anthropic_base_url or None
        )

    def analyze(self, query: str, docs: List[Dict[str, Any]], incidents: List[Dict[str, Any]], deployments: List[Dict[str, Any]]) -> List[str]:
        logger.info(f"DiagnosticAgent analyzing evidence with model {self.model}")
        docs_text = "\n".join([f"- {d.get('source', 'doc')}: {d.get('content', '')}" for d in docs]) if docs else "No specific documents retrieved."
        incs_text = "\n".join([f"- {i.get('incident_id', 'INC')}: {i.get('title', '')} | Root Cause: {i.get('root_cause', '')}" for i in incidents]) if incidents else "No historical incidents found."
        deps_text = "\n".join([f"- {d.get('service_name', 'service')} ({d.get('version', '')}): {d.get('status', '')}" for d in deployments]) if deployments else "No recent deployments found."

        prompt = f"""You are a Senior Diagnostic AI Engineer. Based on the retrieved evidence below, analyze the user query and generate structured root-cause hypotheses, insights, or findings based strictly on the provided evidence.

User Query: {query}

Retrieved Documentation:
{docs_text}

Historical Incidents:
{incs_text}

Recent Deployments:
{deps_text}

Provide clear, professional diagnostic reasoning."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return [response.content]
