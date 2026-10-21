"""
Parameterized Prometheus Telemetry Client.
Constructs deterministic PromQL queries for error rates, latency histograms, and request volume.
Zero query hallucination risk.
"""

import os
import logging
from typing import Dict, Any, Optional
import json
import urllib.request
import urllib.parse
try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger("copilot.telemetry.prometheus")

class PrometheusClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("PROMETHEUS_URL") or os.getenv("HOST_PROMETHEUS_URL", "http://localhost:9090")).rstrip("/")

    def query_instant(self, query: str) -> Dict[str, Any]:
        """Executes an instant PromQL query against /api/v1/query."""
        url = f"{self.base_url}/api/v1/query"
        try:
            if httpx is not None:
                with httpx.Client(timeout=4.0) as client:
                    resp = client.get(url, params={"query": query})
                    if resp.status_code == 200:
                        return resp.json().get("data", {}).get("result", [])
            else:
                encoded_params = urllib.parse.urlencode({"query": query})
                req = urllib.request.Request(f"{url}?{encoded_params}")
                with urllib.request.urlopen(req, timeout=4) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        return data.get("data", {}).get("result", [])
        except Exception as e:
            logger.debug(f"Prometheus query {url} skipped/offline: {e}")
        return []

    def get_service_error_rate(self, service_name: str, lookback: str = "2m") -> float:
        """
        Calculates ratio of 5xx errors to total requests:
        sum(rate(http_requests_total{service='$service',status=~'5..'}[$lookback])) 
        / sum(rate(http_requests_total{service='$service'}[$lookback]))
        """
        query = (
            f"sum(rate(http_requests_total{{service='{service_name}',status=~'5..' }}[{lookback}])) "
            f"/ sum(rate(http_requests_total{{service='{service_name}'}}[{lookback}]))"
        )
        results = self.query_instant(query)
        if results and len(results) > 0:
            try:
                val = float(results[0].get("value", [0, 0])[1])
                return round(val, 4)
            except (ValueError, IndexError):
                pass
        return 0.0

    def get_service_latency_p95(self, service_name: str, lookback: str = "2m") -> float:
        """
        Calculates P95 latency in seconds:
        histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service='$service'}[$lookback])) by (le))
        """
        query = (
            f"histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket"
            f"{{service='{service_name}'}}[{lookback}])) by (le))"
        )
        results = self.query_instant(query)
        if results and len(results) > 0:
            try:
                val = float(results[0].get("value", [0, 0])[1])
                return round(val, 3)
            except (ValueError, IndexError):
                pass
        return 0.0

    def get_service_request_rate(self, service_name: str, lookback: str = "2m") -> float:
        """Calculates requests per second."""
        query = f"sum(rate(http_requests_total{{service='{service_name}'}}[{lookback}]))"
        results = self.query_instant(query)
        if results and len(results) > 0:
            try:
                val = float(results[0].get("value", [0, 0])[1])
                return round(val, 2)
            except (ValueError, IndexError):
                pass
        return 0.0

    def get_comprehensive_metrics_summary(self, service_name: str) -> Dict[str, Any]:
        """Collects error rate, p95 latency, and throughput in a single telemetry package."""
        return {
            "service": service_name,
            "error_rate_5xx": self.get_service_error_rate(service_name),
            "latency_p95_seconds": self.get_service_latency_p95(service_name),
            "requests_per_second": self.get_service_request_rate(service_name)
        }
