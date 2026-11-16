#!/usr/bin/env python3
"""ResolveAI Model Context Protocol (MCP) server.

Exposes the platform's knowledge, incident and operational capabilities as typed MCP tools so that any
MCP client (Claude Desktop, IDE agents, custom agents) can query the same data the built-in agents use.

Transports (MCP_TRANSPORT): ``stdio`` (default, for local clients), ``streamable-http`` or ``sse``.

Usage:  PYTHONPATH=. python mcp_server/server.py
"""

from collections import Counter
from typing import Any

from mcp.server.fastmcp import FastMCP
from sqlalchemy import or_

from backend.core.config import settings
from backend.models.db import DeploymentModel, IncidentModel, ServiceModel, SessionLocal
from backend.rag.retrieval import get_retriever

mcp = FastMCP("ResolveAI Incident Intelligence", host=settings.mcp_server_host, port=settings.mcp_server_port)


def _incident_dict(inc: IncidentModel, full: bool = False) -> dict[str, Any]:
    data = {
        "incident_id": inc.incident_id,
        "title": inc.title,
        "severity": inc.severity,
        "service_name": inc.service_name,
        "category": inc.category,
        "root_cause": inc.root_cause,
        "resolution": inc.resolution,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
    }
    if full:
        data |= {"symptoms": inc.symptoms, "status": inc.status, "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None}
    return data


@mcp.tool()
def search_knowledge_base(query: str, top_k: int = 5, service_filter: str | None = None) -> list[dict[str, Any]]:
    """Search runbooks and technical documentation using hybrid (vector + BM25) retrieval."""
    return get_retriever().search(query=query, top_k=max(1, min(top_k, 20)), service_filter=service_filter)


@mcp.tool()
def search_incidents(keyword: str = "", severity: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """Search historical incidents by keyword (title, symptoms, root cause) and/or severity (P1-P4)."""
    with SessionLocal() as session:
        query = session.query(IncidentModel)
        if severity:
            query = query.filter(IncidentModel.severity == severity.upper())
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(IncidentModel.title.ilike(like), IncidentModel.symptoms.ilike(like), IncidentModel.root_cause.ilike(like)))
        rows = query.order_by(IncidentModel.created_at.desc()).limit(max(1, min(limit, 50))).all()
        return [_incident_dict(inc) for inc in rows]


@mcp.tool()
def get_incident_details(incident_id: str) -> dict[str, Any]:
    """Return the full record of one incident, including symptoms and resolution."""
    with SessionLocal() as session:
        inc = session.get(IncidentModel, incident_id)
        return _incident_dict(inc, full=True) if inc else {"error": f"Incident '{incident_id}' not found."}


@mcp.tool()
def get_incident_statistics() -> dict[str, Any]:
    """Aggregate incident counts by severity, category and service."""
    with SessionLocal() as session:
        rows = session.query(IncidentModel.severity, IncidentModel.category, IncidentModel.service_name).all()
    return {
        "total": len(rows),
        "by_severity": dict(Counter(r.severity for r in rows)),
        "by_category": dict(Counter(r.category for r in rows).most_common()),
        "top_services": dict(Counter(r.service_name for r in rows).most_common(5)),
    }


@mcp.tool()
def get_service_dependencies(service_name: str) -> dict[str, Any]:
    """Return a service's catalog entry with the services it depends on and the services that depend on it."""
    with SessionLocal() as session:
        svc = session.query(ServiceModel).filter(ServiceModel.name.ilike(f"%{service_name}%")).first()
        if not svc:
            return {"error": f"Service '{service_name}' not found in catalog."}
        catalog = session.query(ServiceModel).all()
        names = {s.service_id: s.name for s in catalog}
        return {
            "service_id": svc.service_id,
            "name": svc.name,
            "tier": svc.tier,
            "owner": svc.owner,
            "depends_on": [names.get(dep, dep) for dep in svc.dependencies or []],
            "depended_on_by": [s.name for s in catalog if svc.service_id in (s.dependencies or [])],
        }


@mcp.tool()
def get_recent_deployments(service_name: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """Return recent deployment / change records, optionally filtered by service name."""
    with SessionLocal() as session:
        query = session.query(DeploymentModel)
        if service_name:
            query = query.filter(DeploymentModel.service_name.ilike(f"%{service_name}%"))
        rows = query.order_by(DeploymentModel.deployed_at.desc()).limit(max(1, min(limit, 50))).all()
        return [
            {
                "deployment_id": d.deployment_id,
                "service_name": d.service_name,
                "version": d.version,
                "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None,
                "author": d.author,
                "status": d.status,
                "changes_summary": d.changes_summary,
            }
            for d in rows
        ]


@mcp.tool()
def generate_troubleshooting_checklist(incident_type: str, service_name: str) -> dict[str, Any]:
    """Build a troubleshooting checklist; the mitigation step is taken from the best-matching runbook."""
    hits = get_retriever().search(f"{incident_type} {service_name}", top_k=1)
    steps = [
        f"Check health metrics and error logs for {service_name}.",
        f"Inspect deployments and configuration changes affecting {service_name} in the last 24 hours.",
        "Verify downstream dependencies and connection-pool health.",
    ]
    runbook = hits[0]["source"] if hits else None
    if hits:
        steps.append(f"Consult runbook {runbook} for {incident_type} mitigation.")
    steps.append(f"Escalate to the {service_name} owner if the error rate stays above SLA after 30 minutes.")
    return {
        "incident_type": incident_type,
        "service_name": service_name,
        "runbook": runbook,
        "steps": [f"{i}. {step}" for i, step in enumerate(steps, start=1)],
        "approval_required": True,  # any production change (rollback, restart, config) needs human sign-off
    }


if __name__ == "__main__":
    mcp.run(transport=settings.mcp_transport)  # type: ignore[arg-type]
