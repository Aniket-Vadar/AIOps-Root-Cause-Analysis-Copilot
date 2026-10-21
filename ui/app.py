import os
import time
import requests
import streamlit as st

st.set_page_config(
    page_title="Agentic AIOps RCA Copilot",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration from environment or defaults
BACKEND_URL = os.getenv("COPILOT_BACKEND_URL", "http://localhost:8000")
ORDER_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8001")
PAYMENT_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8002")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #60a5fa;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1e293b;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
    }
    .evidence-box {
        background-color: #0f172a;
        padding: 0.8rem;
        border-radius: 6px;
        font-family: monospace;
        font-size: 0.85rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🛡️ Agentic AIOps Root Cause Analysis Copilot</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Autonomous incident triage and remediation engine powered by LangGraph & Gemini Flash</div>', unsafe_allow_html=True)

# --- Top Navigation / Health Bar ---
col_h1, col_h2, col_h3, col_h4 = st.columns(4)

def check_endpoint(url):
    try:
        r = requests.get(f"{url}/health", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False

with col_h1:
    order_ok = check_endpoint(ORDER_URL)
    st.metric("Order Service (8001)", "ONLINE" if order_ok else "OFFLINE", delta="Healthy" if order_ok else "Unreachable")

with col_h2:
    pay_ok = check_endpoint(PAYMENT_URL)
    st.metric("Payment Service (8002)", "ONLINE" if pay_ok else "OFFLINE", delta="Healthy" if pay_ok else "Unreachable")

with col_h3:
    backend_ok = check_endpoint(BACKEND_URL)
    st.metric("RCA Backend (8000)", "ONLINE" if backend_ok else "OFFLINE", delta="LangGraph Active" if backend_ok else "Unreachable")

with col_h4:
    st.metric("Quota Guardrail", "Active (10 RPM Max)", delta="2 LLM calls / incident")

st.divider()

# --- Sidebar: Chaos Engineering & Live Trigger ---
with st.sidebar:
    st.header("⚡ Chaos Engineering Lab")
    st.caption("Inject deterministic faults into microservices to trigger alerts and test the LangGraph RCA engine.")

    st.subheader("1. Inject Scenarios")
    if st.button("🔥 Scenario 1: Downstream Latency (5s)", use_container_width=True):
        with st.spinner("Injecting 5s delay on payment-service..."):
            try:
                requests.post(f"{PAYMENT_URL}/chaos/latency", params={"delay": 5.0}, timeout=3.0)
                st.success("Injected 5s delay! Order-service will encounter 504 timeouts.")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("💥 Scenario 2: Database Deadlock (500)", use_container_width=True):
        with st.spinner("Enabling 100% error rate..."):
            try:
                requests.post(f"{PAYMENT_URL}/chaos/error", params={"rate": 1.0}, timeout=3.0)
                st.success("Error rate set to 100%! Orders will fail with database lock errors.")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("🔥 Scenario 3: CPU Burn (10s)", use_container_width=True):
        with st.spinner("Burning CPU on payment-service..."):
            try:
                requests.post(f"{PAYMENT_URL}/chaos/resource", params={"duration": 10}, timeout=15.0)
                st.success("CPU saturation drill completed!")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("🔄 Reset to Healthy Baseline", use_container_width=True):
        try:
            requests.post(f"{PAYMENT_URL}/chaos/reset", timeout=3.0)
            st.info("Cleared all chaos states.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    st.subheader("2. Run Instant RCA Drill")
    st.caption("Directly trigger the 5-node LangGraph pipeline with simulated telemetry.")
    drill_service = st.selectbox("Culprit Service", ["order-service", "payment-service"])
    drill_alert = st.selectbox("Alert Name", ["HighErrorRate", "ServiceLatencyHigh", "DownstreamTimeout"])

    if st.button("🚀 Trigger Autonomous RCA", type="primary", use_container_width=True):
        with st.spinner("Executing LangGraph pipeline (Telemetries -> Correlation -> Synthesis)..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/api/v1/trigger-drill",
                    params={"service": drill_service, "alert_name": drill_alert},
                    timeout=35.0
                )
                if resp.status_code == 200:
                    st.success(f"Generated RCA {resp.json().get('incident_id')} successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Backend error: {resp.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    st.divider()
    st.markdown(f"[📊 Open Grafana Dashboards]({GRAFANA_URL})")

# --- Main Screen: Incident Viewer & RCA Reports ---
tab1, tab2 = st.tabs(["📋 Incident RCA Reports", "📊 Live Observability & Traffic"])

with tab1:
    # Fetch incidents from backend
    incidents = []
    try:
        r = requests.get(f"{BACKEND_URL}/api/v1/incidents", timeout=2.0)
        if r.status_code == 200:
            incidents = r.json()
    except Exception:
        pass

    if not incidents:
        st.info("No incidents recorded yet. Use the sidebar to trigger an **Instant RCA Drill** or inject chaos.")
    else:
        # Incident Selector
        incident_options = {f"{i['incident_id']} - {i['title']} ({i['created_at']})": i['incident_id'] for i in incidents}
        selected_label = st.selectbox("Select Incident to Inspect:", list(incident_options.keys()))
        selected_id = incident_options[selected_label]

        # Fetch detailed incident
        try:
            r_detail = requests.get(f"{BACKEND_URL}/api/v1/incidents/{selected_id}", timeout=2.0)
            if r_detail.status_code == 200:
                inc_data = r_detail.json()
                report = inc_data.get("report", {})

                # Severity & Title Banner
                col_t1, col_t2, col_t3 = st.columns([3, 1, 1])
                with col_t1:
                    st.subheader(f"🏷️ {report.get('title', 'Root Cause Analysis')}")
                with col_t2:
                    st.info(f"**Culprit:** `{report.get('culprit_service', 'Unknown')}`")
                with col_t3:
                    conf = report.get('confidence_score', 0.9) * 100
                    st.success(f"**Confidence:** `{conf:.0f}%`")

                st.markdown(f"**Category:** `{report.get('root_cause_category', 'ANOMALY')}` | **Severity:** `{report.get('severity', 'CRITICAL')}`")
                st.markdown("---")

                # Root Cause Narrative
                st.markdown("### 🔍 Root Cause Explanation")
                st.write(report.get("root_cause_explanation", "No explanation provided."))

                # Evidence Chain
                st.markdown("### 📑 Telemetry Evidence Chain")
                evidence_list = report.get("evidence_chain", [])
                if evidence_list:
                    for ev in evidence_list:
                        with st.expander(f"📌 {ev.get('source', 'Telemetry').upper()}: {ev.get('summary', 'Finding')}", expanded=True):
                            st.code(ev.get("raw_snippet", "N/A"), language="json" if "{" in ev.get("raw_snippet", "") else "text")
                            if ev.get("grafana_url"):
                                st.markdown(f"[🔗 View in Grafana Explore]({ev.get('grafana_url')})")
                else:
                    st.write("No granular evidence attached.")

                # Remediation Section
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    st.markdown("### 🚨 Immediate Mitigation")
                    for m in report.get("immediate_mitigation", []):
                        st.markdown(f"- ✅ {m}")

                with col_r2:
                    st.markdown("### 🛠️ Permanent Fix Recommendations")
                    for p in report.get("permanent_fix_recommendations", []):
                        st.markdown(f"- 🔧 {p}")

        except Exception as e:
            st.error(f"Failed to load incident details: {e}")

with tab2:
    st.subheader("Observability Quick-Access")
    st.markdown("""
    Your microservices stream metrics, logs, and distributed traces into the local observability fabric:
    - **Prometheus Metrics:** `http://localhost:9090` (Scraping every 5s)
    - **Grafana Dashboards:** `http://localhost:3000` (Pre-configured datasource & microservices dashboard)
    - **Loki Log Aggregator:** `http://localhost:3100` (LogQL)
    - **Tempo Trace Engine:** `http://localhost:3200` (OTLP spans)
    - **Alertmanager Webhook:** `http://localhost:9093` -> `copilot-backend:8000/api/v1/alerts/webhook`
    """)

    st.subheader("Test Traffic Trigger")
    col_tr1, col_tr2 = st.columns(2)
    with col_tr1:
        if st.button("Send Single Test Order Request (200 OK)"):
            try:
                r = requests.post(f"{ORDER_URL}/order", timeout=3.0)
                st.write(r.json())
            except Exception as e:
                st.error(f"Request failed: {e}")
    with col_tr2:
        if st.button("Send Fail-Fast Unhandled Exception Request (500)"):
            try:
                r = requests.post(f"{ORDER_URL}/order/fail-fast", timeout=3.0)
                st.write(f"Status: {r.status_code}")
            except Exception as e:
                st.warning(f"Observed expected 500 failure: {e}")
