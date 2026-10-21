"""
Node 2: Fetch Telemetry Matrix (Deterministic Python - 0 LLM Calls).
Collects pre-baked metrics, logs, and distributed traces without relying on LLM query generation.
"""

import logging
from typing import Dict, Any
from copilot.graph.state import IncidentState
from copilot.telemetry.prometheus_client import PrometheusClient
from copilot.telemetry.tempo_client import TempoClient
from copilot.telemetry.loki_client import LokiClient

logger = logging.getLogger("copilot.graph.node.fetch_telemetry")

prom_client = PrometheusClient()
tempo_client = TempoClient()
loki_client = LokiClient()

def fetch_telemetry_node(state: IncidentState) -> Dict[str, Any]:
    service = state.get("target_service", "order-service")
    incident_id = state.get("incident_id")
    logger.info(f"Node 2 [FetchTelemetry]: Gathering telemetry matrix for service='{service}'")

    # 1. Fetch Prometheus Metrics
    metrics_data = prom_client.get_comprehensive_metrics_summary(service)
    # Also fetch downstream service metrics if order-service is culprit
    if service == "order-service":
        metrics_data["downstream_payment_metrics"] = prom_client.get_comprehensive_metrics_summary("payment-service")

    # 2. Fetch Failing Traces from Tempo
    traces_data = tempo_client.search_failing_traces(service, limit=3)

    # 3. Fetch Error Logs from Loki
    logs_data = loki_client.get_service_error_logs(service, limit=8)
    if service == "order-service":
        payment_logs = loki_client.get_service_error_logs("payment-service", limit=8)
        logs_data.extend(payment_logs)

    logger.info(
        f"Node 2 [FetchTelemetry] Complete: Found error_rate={metrics_data.get('error_rate_5xx')}, "
        f"{len(traces_data)} traces, {len(logs_data)} error logs"
    )

    return {
        "metrics_summary": metrics_data,
        "failing_traces": traces_data,
        "error_logs": logs_data[:12], # bound context size
        "execution_status": "TELEMETRY_COLLECTED"
    }
