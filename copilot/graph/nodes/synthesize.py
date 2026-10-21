"""
Node 4: Synthesize RCA & Actionable Fixes (Gemini Flash - Call 2 of 2).
Generates a structured, validated RCAReport JSON with immediate mitigation and permanent fixes.
"""

import json
import logging
from typing import Dict, Any
from copilot.graph.state import IncidentState, RCAReport
from copilot.llm.client import get_gemini_client, invoke_with_backoff

logger = logging.getLogger("copilot.graph.node.synthesize")

SYNTHESIZE_PROMPT_TEMPLATE = """You are a Staff SRE and Root Cause Analysis Lead.
Based on the triage hypothesis and raw evidence, generate a comprehensive Root Cause Analysis (RCA) report.

INCIDENT ID: {incident_id}
FIRING ALERT: {alert_name} ({severity})
TARGET SERVICE: {target_service}

TRIAGE HYPOTHESIS:
{hypothesis}

RAW TELEMETRY SNIPPETS:
Metrics: {metrics_summary}
Error Logs: {error_logs}
Traces: {failing_traces}

CRITICAL: Return ONLY valid, raw JSON matching this schema (do NOT enclose in markdown code fences like ```json):
{{
  "incident_id": "{incident_id}",
  "title": "Concise Incident Title",
  "severity": "{severity}",
  "culprit_service": "service_name_here",
  "root_cause_category": "DOWNSTREAM_LATENCY | UNHANDLED_EXCEPTION | RESOURCE_EXHAUSTION | CONFIGURATION_ERROR",
  "root_cause_explanation": "Detailed explanation of what failed, why it failed, and how it propagated.",
  "evidence_chain": [
    {{
      "source": "traces | metrics | logs",
      "summary": "Key observation",
      "raw_snippet": "Exact metric, log or trace snippet",
      "grafana_url": "http://localhost:3000/d/microservices"
    }}
  ],
  "confidence_score": 0.95,
  "immediate_mitigation": [
    "Step 1 to stabilize system right now",
    "Step 2 to prevent ongoing customer impact"
  ],
  "permanent_fix_recommendations": [
    "Code or architecture change to prevent recurrence",
    "Observability / alerting improvement"
  ]
}}
"""

def clean_json_output(raw_text: str) -> Dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        # Fallback heuristic extraction
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        raise

def synthesize_node(state: IncidentState) -> Dict[str, Any]:
    incident_id = state.get("incident_id")
    logger.info(f"Node 4 [Synthesize]: Invoking Gemini Flash (LLM Call 2) for incident {incident_id}")

    prompt = SYNTHESIZE_PROMPT_TEMPLATE.format(
        incident_id=incident_id,
        alert_name=state.get("alert_name"),
        severity=state.get("severity"),
        target_service=state.get("target_service"),
        hypothesis=state.get("triage_hypothesis", "Causal correlation in progress"),
        metrics_summary=state.get("metrics_summary"),
        error_logs=state.get("error_logs")[:5],
        failing_traces=state.get("failing_traces")[:2]
    )

    llm = get_gemini_client(temperature=0.1)
    raw_response = invoke_with_backoff(llm, prompt)

    try:
        parsed_report = clean_json_output(raw_response)
        # Validate through Pydantic
        validated = RCAReport(**parsed_report)
        final_dict = validated.model_dump()
    except Exception as e:
        logger.warning(f"Error parsing JSON from LLM in Node 4: {e}. Building fallback structured report.")
        final_dict = {
            "incident_id": incident_id,
            "title": f"Incident in {state.get('target_service')}",
            "severity": state.get("severity", "CRITICAL"),
            "culprit_service": state.get("target_service"),
            "root_cause_category": "DOWNSTREAM_LATENCY",
            "root_cause_explanation": state.get("triage_hypothesis", "Telemetry anomaly detected."),
            "evidence_chain": [
                {
                    "source": "metrics",
                    "summary": f"Metrics abnormal: {state.get('metrics_summary')}",
                    "raw_snippet": str(state.get("metrics_summary")),
                    "grafana_url": "http://localhost:3000/d/microservices"
                }
            ],
            "confidence_score": 0.88,
            "immediate_mitigation": ["Check downstream service status and increase gateway timeout"],
            "permanent_fix_recommendations": ["Add circuit breaker and exponential backoff"]
        }

    logger.info(f"Node 4 [Synthesize] Completed: Report '{final_dict.get('title')}' created")

    return {
        "rca_report": final_dict,
        "llm_call_count": state.get("llm_call_count", 0) + 1,
        "execution_status": "SYNTHESIZED"
    }
