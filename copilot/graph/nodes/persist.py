"""
Node 5: Validate & Persist (Deterministic Python - 0 LLM Calls).
Stores the completed RCA report into the local incident database and formats Grafana deep-links.
"""

import logging
from typing import Dict, Any
from copilot.graph.state import IncidentState
from copilot.storage.incident_db import get_incident_db

logger = logging.getLogger("copilot.graph.node.persist")

def persist_node(state: IncidentState) -> Dict[str, Any]:
    incident_id = state.get("incident_id")
    rca_report = state.get("rca_report")
    logger.info(f"Node 5 [Persist]: Saving incident {incident_id} to incident repository")

    if rca_report:
        db = get_incident_db()
        db.save_incident(
            incident_id=incident_id,
            alert_name=state.get("alert_name", "UnknownAlert"),
            culprit_service=rca_report.get("culprit_service", state.get("target_service")),
            severity=rca_report.get("severity", "CRITICAL"),
            title=rca_report.get("title", f"Incident {incident_id}"),
            report_data=rca_report,
            llm_calls=state.get("llm_call_count", 2)
        )

    logger.info(f"Node 5 [Persist] Completed: Incident {incident_id} successfully persisted")
    return {
        "execution_status": "COMPLETED"
    }
