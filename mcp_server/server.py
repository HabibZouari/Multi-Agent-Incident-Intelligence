#!/usr/bin/env python3
"""
ResolveAI Model Context Protocol (MCP) Server
Exposes operational, knowledge, incident, and action tools via MCP protocol.
"""

import os
import json
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from backend.models.db import SessionLocal, IncidentModel, ServiceModel, DeploymentModel, DocumentModel
from backend.rag.retrieval import HybridRetriever

mcp = FastMCP("ResolveAI Incident Intelligence MCP Server")
retriever = HybridRetriever()

@mcp.tool()
def search_knowledge_base(query: str, top_k: int = 5, service_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search technical documentation and runbooks using hybrid semantic and keyword search."""
    return retriever.search(query=query, top_k=top_k, service_filter=service_filter)

@mcp.tool()
def search_incidents(keyword: str, severity: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Search historical incident records by keyword or severity."""
    session = SessionLocal()
    try:
        query = session.query(IncidentModel)
        if severity:
            query = query.filter(IncidentModel.severity == severity.upper())
        if keyword:
            query = query.filter(
                (IncidentModel.title.ilike(f"%{keyword}%")) |
                (IncidentModel.symptoms.ilike(f"%{keyword}%")) |
                (IncidentModel.root_cause.ilike(f"%{keyword}%"))
            )
        incidents = query.limit(limit).all()
        return [{
            "incident_id": inc.incident_id,
            "title": inc.title,
            "severity": inc.severity,
            "service_name": inc.service_name,
            "category": inc.category,
            "root_cause": inc.root_cause,
            "resolution": inc.resolution,
            "created_at": inc.created_at.isoformat() if inc.created_at else None
        } for inc in incidents]
    finally:
        session.close()

@mcp.tool()
def get_service_dependencies(service_name: str) -> Dict[str, Any]:
    """Get service details and its dependency tree from the service catalog."""
    session = SessionLocal()
    try:
        svc = session.query(ServiceModel).filter(ServiceModel.name.ilike(f"%{service_name}%")).first()
        if not svc:
            return {"error": f"Service '{service_name}' not found in catalog."}
        return {
            "service_id": svc.service_id,
            "name": svc.name,
            "tier": svc.tier,
            "owner": svc.owner,
            "dependencies": svc.dependencies
        }
    finally:
        session.close()

@mcp.tool()
def get_recent_deployments(service_name: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Get recent deployment and change records for a service."""
    session = SessionLocal()
    try:
        query = session.query(DeploymentModel)
        if service_name:
            query = query.filter(DeploymentModel.service_name.ilike(f"%{service_name}%"))
        deployments = query.order_by(DeploymentModel.deployed_at.desc()).limit(limit).all()
        return [{
            "deployment_id": d.deployment_id,
            "service_name": d.service_name,
            "version": d.version,
            "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None,
            "author": d.author,
            "status": d.status,
            "changes_summary": d.changes_summary
        } for d in deployments]
    finally:
        session.close()

@mcp.tool()
def generate_troubleshooting_checklist(incident_type: str, service_name: str) -> Dict[str, Any]:
    """Generate a step-by-step troubleshooting checklist for an incident."""
    return {
        "incident_type": incident_type,
        "service_name": service_name,
        "steps": [
            f"1. Check health metrics and error logs for {service_name}.",
            f"2. Inspect recent deployments and change records within the last 24 hours.",
            f"3. Verify downstream dependencies and database connection pool health.",
            f"4. Consult relevant runbooks for {incident_type} mitigation.",
            f"5. Escalate to service owner if error rate exceeds SLA thresholds."
        ],
        "approval_required": False
    }

if __name__ == "__main__":
    print("Starting ResolveAI MCP Server...")
    mcp.run()
