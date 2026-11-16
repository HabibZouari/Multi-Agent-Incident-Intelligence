from typing import Any

from backend.core.llm import build_llm, complete
from backend.core.logger import logger

PROMPT = """You are a Senior Site Reliability Engineer. Analyse the user's query using ONLY the evidence below and
produce ranked root-cause hypotheses. For each hypothesis cite the supporting evidence (document source or incident ID)
and state your confidence. If the evidence does not cover the query (e.g. the service or incident is not mentioned),
say so explicitly and ask for the missing details instead of speculating.

User Query: {query}

Retrieved Documentation:
{docs}

Historical Incidents:
{incidents}

Recent Deployments:
{deployments}
"""


def _format_docs(docs: list[dict[str, Any]]) -> str:
    return "\n".join(f"- [{d.get('source', 'doc')}] {d.get('content', '')[:600]}" for d in docs) or "No relevant documents retrieved."


def _format_incidents(incidents: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- {i.get('incident_id')} ({i.get('service_name')}): {i.get('title')} | Root cause: {i.get('root_cause')} | Resolution: {i.get('resolution')}"
        for i in incidents
    ) or "No related historical incidents found."


def _format_deployments(deployments: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- {d.get('service_name')} {d.get('version')} - {d.get('status')} at {d.get('deployed_at')}" for d in deployments
    ) or "No recent deployments found."


class DiagnosticAgent:
    """Synthesises retrieved evidence into root-cause hypotheses (LLM-backed, with a deterministic fallback)."""

    def __init__(self, model_override: str | None = None):
        self.llm = build_llm(model_override)

    def analyze(self, query: str, docs: list[dict[str, Any]], incidents: list[dict[str, Any]], deployments: list[dict[str, Any]]) -> list[str]:
        logger.info("DiagnosticAgent analysing %d docs, %d incidents, %d deployments", len(docs), len(incidents), len(deployments))
        prompt = PROMPT.format(
            query=query, docs=_format_docs(docs), incidents=_format_incidents(incidents), deployments=_format_deployments(deployments)
        )
        answer = complete(self.llm, prompt)
        return [answer if answer else self._fallback(query, docs, incidents, deployments)]

    @staticmethod
    def _fallback(query: str, docs: list[dict[str, Any]], incidents: list[dict[str, Any]], deployments: list[dict[str, Any]]) -> str:
        """Evidence digest used when no LLM is configured (or the call failed)."""
        if not (docs or incidents):
            return "No matching runbooks or historical incidents were found. Please provide the affected service, symptoms and time window."
        lines = ["_Evidence summary (generated without an LLM)._", ""]
        if incidents:
            lines.append("**Probable root causes seen in similar historical incidents:**")
            seen = set()
            for inc in incidents:
                if inc["root_cause"] not in seen:
                    seen.add(inc["root_cause"])
                    lines.append(f"- {inc['root_cause']} (e.g. {inc['incident_id']} on {inc['service_name']})")
        flagged = [d for d in deployments if d.get("status") in ("rollback", "failed")]
        if flagged:
            lines += ["", "**Deployments worth checking:**"] + [
                f"- {d['service_name']} {d['version']} ended in `{d['status']}` at {d['deployed_at']}" for d in flagged
            ]
        if docs:
            lines += ["", "**Relevant documentation:**"] + [f"- {d['source']}" for d in docs]
        return "\n".join(lines)
