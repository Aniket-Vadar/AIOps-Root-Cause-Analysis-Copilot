"""
Gemini LLM Client Factory with Strict Rate-Limiting & Backoff Guardrails.
Enforces <= 10 RPM to prevent exceeding Google AI Studio Free Tier (15 RPM).
"""

import os
import time
import logging
from typing import Optional, Any
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

logger = logging.getLogger("copilot.llm")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class RateLimiter:
    """Enforces a sliding window or min-interval constraint to stay strictly under 15 RPM."""
    def __init__(self, max_rpm: int = 10):
        self.max_rpm = max_rpm
        self.min_interval = 60.0 / float(max_rpm) # e.g. 6 seconds minimum between calls
        self.last_call_timestamp = 0.0

    def wait_if_needed(self):
        elapsed = time.time() - self.last_call_timestamp
        if elapsed < self.min_interval:
            sleep_duration = self.min_interval - elapsed
            logger.info(f"RateLimiter: sleeping for {sleep_duration:.2f}s to preserve 15 RPM free-tier quota.")
            time.sleep(sleep_duration)
        self.last_call_timestamp = time.time()


# Global rate limiter instance
_global_rate_limiter = RateLimiter(max_rpm=int(os.getenv("MAX_RPM_CALLS", "10")))


def get_gemini_client(temperature: float = 0.1) -> Any:
    """
    Returns an initialized LangChain ChatGoogleGenerativeAI instance,
    or a Mock LLM if no API key is configured.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("No valid GEMINI_API_KEY found in .env. Initializing in Mock/Offline mode.")
        return MockGeminiClient()

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
            max_retries=3,
            timeout=30.0,
        )
        return llm
    except ImportError:
        logger.warning("langchain-google-genai not installed. Falling back to MockGeminiClient.")
        return MockGeminiClient()


class MockGeminiClient:
    """Offline mock client to allow development, unit testing, and graph validation without an active API key."""
    def __init__(self, model: str = "mock-gemini-flash"):
        self.model = model

    def invoke(self, prompt: Any) -> Any:
        _global_rate_limiter.wait_if_needed()
        prompt_text = str(prompt)
        logger.info(f"[MockGeminiClient] Received prompt ({len(prompt_text)} chars). Returning mock SRE assessment.")
        
        # Return a simulated response compatible with LangChain message format
        from dataclasses import dataclass
        @dataclass
        class MockAIMessage:
            content: str

        if "correlate" in prompt_text.lower() or "triage" in prompt_text.lower():
            mock_content = (
                "TRIAGE HYPOTHESIS: High latency in order-service is directly caused by a 5000ms delay in "
                "the downstream payment-service endpoint (/pay). Database connection pool saturation observed."
            )
        else:
            mock_content = """{
  "incident_id": "INC-MOCK-001",
  "title": "Downstream Payment Timeout Cascading to Order Service",
  "severity": "CRITICAL",
  "culprit_service": "payment-service",
  "root_cause_category": "DOWNSTREAM_LATENCY",
  "root_cause_explanation": "Order service experienced elevated 504 errors because downstream Payment service exceeded the 2000ms timeout threshold.",
  "evidence_chain": [
    {
      "source": "traces",
      "summary": "Tempo trace waterfall shows span payment-service:/pay consumed 5020ms",
      "raw_snippet": "span_id=a1b2c3d4, duration=5.02s",
      "grafana_url": "http://localhost:3000/explore"
    },
    {
      "source": "metrics",
      "summary": "Order service 5xx error rate breached 25%",
      "raw_snippet": "sum(rate(http_requests_total{status=~'5..'}[1m])) = 0.28",
      "grafana_url": "http://localhost:3000/d/microservices"
    }
  ],
  "confidence_score": 0.94,
  "immediate_mitigation": [
    "Increase client-side timeout in order-service to 6s temporarily",
    "Route checkout requests to payment-service fallback replica"
  ],
  "permanent_fix_recommendations": [
    "Implement circuit breaker pattern in order-service using resilience4j or tenacity",
    "Optimize payment-service database query execution and indexing"
  ]
}"""
        return MockAIMessage(content=mock_content)


def invoke_with_backoff(llm: Any, prompt: Any, max_retries: int = 3) -> str:
    """Wrapper that enforces RPM throttle and catches 429 with exponential backoff."""
    _global_rate_limiter.wait_if_needed()
    
    backoff = float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "5"))
    for attempt in range(1, max_retries + 1):
        try:
            response = llm.invoke(prompt)
            if hasattr(response, "content"):
                return response.content
            return str(response)
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "resourceexhausted" in err_msg or "quota" in err_msg:
                wait_time = backoff * (2 ** (attempt - 1))
                logger.warning(f"Gemini 429 quota hit (Attempt {attempt}/{max_retries}). Backing off for {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Error invoking Gemini LLM: {e}")
                raise e
    raise RuntimeError(f"Exceeded max retries ({max_retries}) due to Gemini rate limits.")
