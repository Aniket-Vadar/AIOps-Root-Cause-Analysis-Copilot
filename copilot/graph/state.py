"""
Typed State and Structured Output Schemas for LangGraph RCA Pipeline.
"""

from typing import TypedDict, List, Dict, Any, Optional
try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self):
            res = {}
            for k, v in self.__dict__.items():
                if hasattr(v, "model_dump"):
                    res[k] = v.model_dump()
                elif isinstance(v, list):
                    res[k] = [x.model_dump() if hasattr(x, "model_dump") else x for x in v]
                else:
                    res[k] = v
            return res

    def Field(default=None, description=""):
        return default

class EvidenceItem(BaseModel):
    source: str = Field(description="Telemetry source: metrics, traces, or logs")
    summary: str = Field(description="Key finding or anomaly summary")
    raw_snippet: str = Field(description="Relevant raw metric, log line, or trace identifier")
    grafana_url: Optional[str] = Field(default=None, description="Pre-filtered deep link to Grafana")


class RCAReport(BaseModel):
    incident_id: str
    title: str
    severity: str # CRITICAL | WARNING | INFO
    culprit_service: str
    root_cause_category: str # DOWNSTREAM_LATENCY | UNHANDLED_EXCEPTION | RESOURCE_EXHAUSTION | CONFIGURATION_ERROR
    root_cause_explanation: str
    evidence_chain: List[EvidenceItem]
    confidence_score: float # 0.0 to 1.0
    immediate_mitigation: List[str]
    permanent_fix_recommendations: List[str]


class IncidentState(TypedDict):
    """Global state passed through the LangGraph StateGraph nodes."""
    incident_id: str
    alert_name: str
    target_service: str
    severity: str
    alert_summary: str
    starts_at: str
    
    # Telemetry data collected by deterministic Python tools (No LLM hallucinations)
    metrics_summary: Dict[str, Any]
    failing_traces: List[Dict[str, Any]]
    error_logs: List[str]
    
    # Reasoning steps
    triage_hypothesis: Optional[str]
    rca_report: Optional[Dict[str, Any]]
    
    # Audit metadata
    llm_call_count: int
    execution_status: str
    error_details: Optional[str]
