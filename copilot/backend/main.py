"""
FastAPI Backend for Agentic AIOps RCA Copilot.
Handles Alertmanager webhooks, runs the LangGraph engine, and serves incident reports.
"""

import os
import uuid
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from copilot.graph.graph import get_rca_graph
from copilot.graph.state import IncidentState
from copilot.storage.incident_db import get_incident_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [copilot-backend] %(message)s")
logger = logging.getLogger("copilot-backend")

app = FastAPI(
    title="Agentic AIOps RCA Copilot Backend",
    version="1.0.0",
    description="Webhook receiver and LangGraph orchestration service for automated incident RCA"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = get_incident_db()

class AlertmanagerPayload(BaseModel):
    version: str = "4"
    groupKey: str = ""
    status: str = "firing"
    receiver: str = "copilot-webhook"
    alerts: List[Dict[str, Any]] = []

def process_alert_in_graph(alert_item: Dict[str, Any]):
    labels = alert_item.get("labels", {})
    annotations = alert_item.get("annotations", {})
    
    alert_name = labels.get("alertname", "UnknownAlert")
    service = labels.get("service") or labels.get("job") or "order-service"
    severity = labels.get("severity", "critical")
    summary = annotations.get("summary", "Prometheus alert triggered")
    starts_at = alert_item.get("startsAt", "")

    incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"

    initial_state: IncidentState = {
        "incident_id": incident_id,
        "alert_name": alert_name,
        "target_service": service,
        "severity": severity,
        "alert_summary": summary,
        "starts_at": starts_at,
        "metrics_summary": {},
        "failing_traces": [],
        "error_logs": [],
        "triage_hypothesis": None,
        "rca_report": None,
        "llm_call_count": 0,
        "execution_status": "PENDING",
        "error_details": None
    }

    logger.info(f"Triggering LangGraph RCA Pipeline for incident {incident_id} ({alert_name})...")
    graph = get_rca_graph()
    final_state = graph.invoke(initial_state)
    logger.info(f"LangGraph execution finished for {incident_id}. Status: {final_state.get('execution_status')}")
    return final_state

@app.get("/health")
def health():
    return {"status": "ok", "service": "copilot-backend"}

@app.post("/api/v1/alerts/webhook")
async def alertmanager_webhook(payload: AlertmanagerPayload, background_tasks: BackgroundTasks):
    """Receives Prometheus Alertmanager webhook payloads."""
    logger.info(f"Received Alertmanager webhook with {len(payload.alerts)} alerts. Status: {payload.status}")

    # We process firing alerts
    firing_alerts = [a for a in payload.alerts if a.get("status") != "resolved"]
    if not firing_alerts and payload.alerts:
        firing_alerts = payload.alerts

    results = []
    for alert in firing_alerts:
        # Run asynchronously in background or directly
        final_state = process_alert_in_graph(alert)
        results.append({
            "incident_id": final_state.get("incident_id"),
            "status": final_state.get("execution_status"),
            "rca_title": final_state.get("rca_report", {}).get("title") if final_state.get("rca_report") else "Analyzing"
        })

    return {"status": "processed", "incidents": results}

@app.get("/api/v1/incidents")
def list_incidents(limit: int = 20):
    """Returns list of past incidents and generated RCAs."""
    return db.list_incidents(limit=limit)

@app.get("/api/v1/incidents/{incident_id}")
def get_incident(incident_id: str):
    """Returns full details of an incident including the synthesized RCA report."""
    inc = db.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc

@app.post("/api/v1/trigger-drill")
def trigger_drill(service: str = "order-service", alert_name: str = "HighErrorRate", severity: str = "critical"):
    """Manual trigger endpoint for live demos and chaos drills."""
    mock_alert = {
        "labels": {"alertname": alert_name, "service": service, "severity": severity},
        "annotations": {"summary": f"Simulated {alert_name} on {service}"},
        "startsAt": "now"
    }
    final_state = process_alert_in_graph(mock_alert)
    return {
        "incident_id": final_state.get("incident_id"),
        "status": final_state.get("execution_status"),
        "report": final_state.get("rca_report")
    }
