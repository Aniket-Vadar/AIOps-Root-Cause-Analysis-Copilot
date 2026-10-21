import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import pytest
except ImportError:
    pytest = None
from copilot.graph.graph import get_rca_graph
from copilot.graph.state import IncidentState
from copilot.storage.incident_db import get_incident_db

def test_rca_graph_end_to_end_execution():
    initial_state: IncidentState = {
        "incident_id": "TEST-INC-101",
        "alert_name": "HighErrorRate",
        "target_service": "order-service",
        "severity": "critical",
        "alert_summary": "High 5xx error rate detected on order-service",
        "starts_at": "2026-10-21T15:00:00Z",
        "metrics_summary": {},
        "failing_traces": [],
        "error_logs": [],
        "triage_hypothesis": None,
        "rca_report": None,
        "llm_call_count": 0,
        "execution_status": "PENDING",
        "error_details": None
    }

    graph = get_rca_graph()
    final_state = graph.invoke(initial_state)

    # 1. Verify execution reached final state
    assert final_state["execution_status"] == "COMPLETED"
    assert final_state["incident_id"] == "TEST-INC-101"

    # 2. Verify telemetry collection node ran
    assert "metrics_summary" in final_state
    assert len(final_state["failing_traces"]) > 0
    assert len(final_state["error_logs"]) > 0

    # 3. Verify correlation node ran
    assert final_state["triage_hypothesis"] is not None
    assert len(final_state["triage_hypothesis"]) > 10

    # 4. Verify synthesis node generated valid RCA report
    report = final_state["rca_report"]
    assert report is not None
    assert "title" in report
    assert "culprit_service" in report
    assert "evidence_chain" in report
    assert "immediate_mitigation" in report
    assert "permanent_fix_recommendations" in report

    # 5. Verify database persistence
    db = get_incident_db()
    saved = db.get_incident("TEST-INC-101")
    assert saved is not None
    assert saved["incident_id"] == "TEST-INC-101"
    assert saved["report"]["culprit_service"] == report["culprit_service"]

if __name__ == "__main__":
    test_rca_graph_end_to_end_execution()
    print("✅ All LangGraph StateGraph end-to-end tests passed successfully!")
