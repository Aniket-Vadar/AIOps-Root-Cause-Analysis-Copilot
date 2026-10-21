"""
LangGraph StateGraph Builder for Agentic AIOps RCA Copilot.
Wires deterministic nodes and bounded LLM reasoning steps into an executable pipeline.
"""

import logging
from typing import Dict, Any
from copilot.graph.state import IncidentState
from copilot.graph.nodes.scope_alert import scope_alert_node
from copilot.graph.nodes.fetch_telemetry import fetch_telemetry_node
from copilot.graph.nodes.correlate import correlate_node
from copilot.graph.nodes.synthesize import synthesize_node
from copilot.graph.nodes.persist import persist_node

logger = logging.getLogger("copilot.graph")

def build_rca_graph():
    """Builds and compiles the LangGraph StateGraph, with fallback if langgraph isn't installed."""
    try:
        from langgraph.graph import StateGraph, START, END

        builder = StateGraph(IncidentState)

        # Register nodes
        builder.add_node("scope_alert", scope_alert_node)
        builder.add_node("fetch_telemetry", fetch_telemetry_node)
        builder.add_node("correlate", correlate_node)
        builder.add_node("synthesize", synthesize_node)
        builder.add_node("persist", persist_node)

        # Connect sequential edges
        builder.add_edge(START, "scope_alert")
        builder.add_edge("scope_alert", "fetch_telemetry")
        builder.add_edge("fetch_telemetry", "correlate")
        builder.add_edge("correlate", "synthesize")
        builder.add_edge("synthesize", "persist")
        builder.add_edge("persist", END)

        compiled_graph = builder.compile()
        logger.info("Compiled LangGraph StateGraph successfully.")
        return compiled_graph

    except ImportError:
        logger.warning("langgraph package not found. Using native Python sequential graph runner.")
        return NativeSequentialRunner()


class NativeSequentialRunner:
    """Pure Python runner mimicking StateGraph execution when langgraph package is absent."""
    def invoke(self, initial_state: IncidentState) -> IncidentState:
        state = dict(initial_state)
        
        # 1. Scope
        update_1 = scope_alert_node(state)
        state.update(update_1)
        
        # 2. Fetch Telemetry
        update_2 = fetch_telemetry_node(state)
        state.update(update_2)
        
        # 3. Correlate
        update_3 = correlate_node(state)
        state.update(update_3)
        
        # 4. Synthesize
        update_4 = synthesize_node(state)
        state.update(update_4)
        
        # 5. Persist
        update_5 = persist_node(state)
        state.update(update_5)
        
        return state


# Singleton graph instance
_graph_instance = None

def get_rca_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_rca_graph()
    return _graph_instance
