from typing import Any

from sqlalchemy import or_

from backend.core.logger import logger
from backend.core.taxonomy import match_categories
from backend.models.db import DeploymentModel, IncidentModel, ServiceModel, SessionLocal
from backend.rag.embeddings import tokenize

# Words that appear in most service names and therefore say nothing about *which* service is meant.
GENERIC_SERVICE_WORDS = frozenset({"service", "api", "cluster", "db", "engine", "pipeline", "microservice", "management", "model", "system"})


def _distinctive_tokens(name: str) -> set[str]:
    return {t for t in tokenize(name) if t not in GENERIC_SERVICE_WORDS}


def match_services(query: str, services: list[ServiceModel]) -> list[str]:
    """Service names best matching the query: the full name, or the highest share of distinctive tokens (>= 50%)."""
    lowered, query_tokens = query.lower(), set(tokenize(query))
    exact = [s.name for s in services if s.name.lower() in lowered]
    if exact:
        return exact
    scored = []
    for service in services:
        tokens = _distinctive_tokens(service.name)
        if tokens:
            scored.append((len(tokens & query_tokens) / len(tokens), service.name))
    best = max((score for score, _ in scored), default=0.0)
    return [name for score, name in scored if score == best] if best >= 0.5 else []


class IncidentAgent:
    """Finds related historical incidents and recent deployments for the services / failure modes in a query."""

    def anchors(self, query: str) -> tuple[list[str], list[str]]:
        """Known failure categories and services the query refers to; empty lists mean it is not anchored."""
        with SessionLocal() as session:
            return match_categories(query), match_services(query, session.query(ServiceModel).all())

    def investigate(self, query: str, limit: int = 5) -> dict[str, list[dict[str, Any]]]:
        logger.info("IncidentAgent querying historical incidents and deployments for: %s", query)
        categories = match_categories(query)
        terms = {t for t in tokenize(query) if len(t) > 3}

        with SessionLocal() as session:
            services = session.query(ServiceModel).all()
            matched_services = match_services(query, services)

            rows: list[IncidentModel] = []
            if categories or matched_services:  # without an anchor there is nothing meaningful to match
                rows = (
                    session.query(IncidentModel)
                    .filter(or_(IncidentModel.category.in_(categories), IncidentModel.service_name.in_(matched_services)))
                    .all()
                )
            scored = []
            for inc in rows:
                haystack = f"{inc.title} {inc.symptoms} {inc.root_cause}".lower()
                score = (
                    (3 if inc.category in categories[:1] else 1 if inc.category in categories else 0)
                    + (2 if inc.service_name in matched_services else 0)
                    + sum(1 for t in terms if t in haystack)
                )
                scored.append((score, inc.created_at, inc))
            scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

            incidents = [
                {
                    "incident_id": inc.incident_id,
                    "title": inc.title,
                    "severity": inc.severity,
                    "service_name": inc.service_name,
                    "category": inc.category,
                    "symptoms": inc.symptoms,
                    "root_cause": inc.root_cause,
                    "resolution": inc.resolution,
                    "created_at": inc.created_at.isoformat() if inc.created_at else None,
                }
                for _, _, inc in scored[:limit]
            ]

            deployments_q = session.query(DeploymentModel)
            if matched_services:
                deployments_q = deployments_q.filter(DeploymentModel.service_name.in_(matched_services))
            deployments = [
                {
                    "deployment_id": d.deployment_id,
                    "service_name": d.service_name,
                    "version": d.version,
                    "status": d.status,
                    "author": d.author,
                    "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None,
                    "changes_summary": d.changes_summary,
                }
                for d in deployments_q.order_by(DeploymentModel.deployed_at.desc()).limit(limit).all()
            ]

        return {"historical_incidents": incidents, "deployments": deployments, "matched_services": matched_services}
