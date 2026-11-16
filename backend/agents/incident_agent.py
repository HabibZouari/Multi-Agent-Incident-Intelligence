from typing import List, Dict, Any
from backend.models.db import SessionLocal, IncidentModel, DeploymentModel
from backend.core.logger import logger

class IncidentAgent:
    def __init__(self):
        pass

    def investigate(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        logger.info(f"IncidentAgent querying historical incidents and deployments for: {query}")
        session = SessionLocal()
        try:
            incidents = session.query(IncidentModel).filter(
                (IncidentModel.title.ilike(f"%{query[:15]}%")) |
                (IncidentModel.category.ilike("%Auth%") | IncidentModel.category.ilike("%Database%"))
            ).limit(3).all()

            inc_list = [{
                "incident_id": inc.incident_id,
                "title": inc.title,
                "severity": inc.severity,
                "service_name": inc.service_name,
                "root_cause": inc.root_cause,
                "resolution": inc.resolution
            } for inc in incidents]

            deps = session.query(DeploymentModel).order_by(DeploymentModel.deployed_at.desc()).limit(3).all()
            dep_list = [{
                "service_name": d.service_name,
                "version": d.version,
                "status": d.status,
                "deployed_at": str(d.deployed_at)
            } for d in deps]

            return {"historical_incidents": inc_list, "deployments": dep_list}
        finally:
            session.close()
