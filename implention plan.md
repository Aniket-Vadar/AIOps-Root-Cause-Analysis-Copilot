# Agentic AIOps Root Cause Analysis (RCA) Copilot - Blueprint Overview

> **Notice:** The finalized, production-grade master implementation plan has been established in **[real-implmention-plan.md](file:///b:/Agentic%20AIOps%20Root%20Cause%20Analysis%20(RCA)%20Copilot/real-implmention-plan.md)**.

## Core Architecture Decisions
- **Framework:** **LangGraph** (StateGraph with typed Pydantic state, deterministic telemetry tools, and bounded LLM calls).
- **Runtime:** **Local Docker Compose** (Microservices + Prometheus + Tempo + Loki + Alertmanager + Grafana + RCA Copilot + Streamlit UI).
- **Memory Ceiling:** Capped at **< 2.6 GB RAM** total for all containers (preserving laptop performance on 16 GB machines).
- **Quota Safety:** Strictly **2 LLM calls per incident**, preventing Gemini free-tier 15 RPM throttling.
- **Incident Validation:** One-click deterministic chaos engine (`scripts/chaos.py`).

Refer to **[real-implmention-plan.md](file:///b:/Agentic%20AIOps%20Root%20Cause%20Analysis%20(RCA)%20Copilot/real-implmention-plan.md)** for the complete node specifications, Pydantic schemas, telemetry query contracts, and 6-phase roadmap.