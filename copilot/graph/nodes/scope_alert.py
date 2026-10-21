"""
Node 1: Scope & Parse Alert (Deterministic Python - 0 LLM Calls).
Extracts service identifiers, severity, and temporal windows from the alert.
"""

import uuid
import logging
from typing import Dict, Any
from copilot.graph.state import IncidentState

logger = logging.getLogger("copilot.graph.node.scope_alert")

def scope_alert_node(state: IncidentState) -> Dict[str, Any]:
    incident_id = state.get("incident_id") or f"INC-{uuid.uuid4().hex[:6].upper()}"
    alert_name = state.get("alert_name", "UnknownAlert")
    service = state.get("target_service") or "order-service"
    severity = state.get("severity", "critical")

    logger.info(f"Node 1 [ScopeAlert]: Scoping incident {incident_id} for service='{service}', alert='{alert_name}'")

    return {
        "incident_id": incident_id,
        "alert_name": alert_name,
        "target_service": service,
        "severity": severity,
        "execution_status": "SCOPED"
    }
