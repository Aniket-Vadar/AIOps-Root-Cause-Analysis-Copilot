"""
Node 3: Correlate & Triage (Gemini Flash - Call 1 of 2).
Analyzes metrics, trace waterfall, and logs to formulate the causal incident hypothesis.
"""

import json
import logging
from typing import Dict, Any
from copilot.graph.state import IncidentState
from copilot.llm.client import get_gemini_client, invoke_with_backoff

logger = logging.getLogger("copilot.graph.node.correlate")

TRIAGE_PROMPT_TEMPLATE = """You are a Principal Site Reliability Engineer (SRE).
Analyze the following telemetry package for an active incident and determine the causal chain of failure.

INCIDENT METADATA:
- Incident ID: {incident_id}
- Firing Alert: {alert_name} ({severity})
- Target Service: {target_service}

TELEMETRY EVIDENCE:
1. Metrics Summary:
{metrics_json}

2. Failing Distributed Traces:
{traces_json}

3. Recent Error Logs:
{logs_text}

TASK:
1. Identify the culprit service (is it {target_service} or a downstream dependency?).
2. Classify the failure mode (e.g., DOWNSTREAM_LATENCY, UNHANDLED_EXCEPTION, RESOURCE_EXHAUSTION).
3. State the exact mechanism of failure in 2-3 concise sentences.

Provide your reasoning clearly.
"""

def correlate_node(state: IncidentState) -> Dict[str, Any]:
    incident_id = state.get("incident_id")
    logger.info(f"Node 3 [Correlate]: Invoking Gemini Flash (LLM Call 1) for incident {incident_id}")

    metrics_json = json.dumps(state.get("metrics_summary", {}), indent=2)
    traces_json = json.dumps(state.get("failing_traces", []), indent=2)
    logs_text = "\n".join(state.get("error_logs", [])) or "No explicit error logs found."

    prompt = TRIAGE_PROMPT_TEMPLATE.format(
        incident_id=incident_id,
        alert_name=state.get("alert_name"),
        severity=state.get("severity"),
        target_service=state.get("target_service"),
        metrics_json=metrics_json,
        traces_json=traces_json,
        logs_text=logs_text
    )

    llm = get_gemini_client(temperature=0.1)
    hypothesis = invoke_with_backoff(llm, prompt)

    logger.info(f"Node 3 [Correlate] Completed: Generated causal hypothesis ({len(hypothesis)} chars)")

    return {
        "triage_hypothesis": hypothesis,
        "llm_call_count": state.get("llm_call_count", 0) + 1,
        "execution_status": "TRIAGED"
    }
