import os
import time
import logging
from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# OpenTelemetry Setup
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [payment-service] %(message)s')
logger = logging.getLogger("payment-service")

# Initialize OpenTelemetry Tracer
resource = Resource.create({"service.name": "payment-service"})
provider = TracerProvider(resource=resource)
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317")
try:
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
except Exception as e:
    logger.warning(f"Could not connect to OTLP exporter at {otlp_endpoint}: {e}")

tracer = trace.get_tracer("payment-service")

app = FastAPI(title="Payment Service", version="1.0.0")
FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

# Prometheus Metrics
REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["service", "endpoint"]
)

# Dynamic Chaos State
CHAOS_STATE = {
    "latency_seconds": 0.0,
    "error_rate": 0.0,
    "is_corrupt": False
}

class PaymentRequest(BaseModel):
    order_id: str
    amount: float

@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = None
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        logger.error(f"Unhandled exception in payment processing: {e}", exc_info=True)
        raise
    finally:
        duration = time.time() - start_time
        endpoint = request.url.path
        if endpoint != "/metrics":
            REQUESTS_TOTAL.labels(
                service="payment-service",
                method=request.method,
                endpoint=endpoint,
                status=str(status_code)
            ).inc()
            REQUEST_DURATION.labels(
                service="payment-service",
                endpoint=endpoint
            ).observe(duration)
    return response

@app.get("/health")
def health():
    return {"status": "ok", "service": "payment-service", "chaos": CHAOS_STATE}

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/pay")
async def process_payment(payload: PaymentRequest):
    with tracer.start_as_current_span("execute_payment") as span:
        span.set_attribute("payment.order_id", payload.order_id)
        span.set_attribute("payment.amount", payload.amount)

        # 1. Check for injected latency fault
        if CHAOS_STATE["latency_seconds"] > 0:
            delay = CHAOS_STATE["latency_seconds"]
            logger.warning(f"CHAOS ACTIVE: Injecting artificial delay of {delay}s on order {payload.order_id}")
            span.set_attribute("chaos.injected_latency_seconds", delay)
            time.sleep(delay)

        # 2. Check for injected error fault
        if CHAOS_STATE["error_rate"] > 0:
            logger.error(f"CHAOS ACTIVE: Simulated database transaction lock / connection failure for order {payload.order_id}")
            span.set_status(trace.StatusCode.ERROR, "Simulated database connection lock timeout")
            raise HTTPException(
                status_code=500,
                detail="DatabaseDeadlockException: Transaction lock timeout on payment ledger table"
            )

        logger.info(f"Payment processed successfully for order {payload.order_id}. Amount=${payload.amount}")
        return {
            "status": "APPROVED",
            "transaction_id": f"TXN-{payload.order_id}",
            "amount": payload.amount
        }

# --- Chaos Injection Control Endpoints ---

@app.post("/chaos/latency")
def set_chaos_latency(delay: float = 5.0):
    CHAOS_STATE["latency_seconds"] = delay
    logger.warning(f"Configured chaos latency: {delay}s")
    return {"status": "ok", "chaos": CHAOS_STATE}

@app.post("/chaos/error")
def set_chaos_error(rate: float = 1.0):
    CHAOS_STATE["error_rate"] = rate
    logger.warning(f"Configured chaos error rate: {rate}")
    return {"status": "ok", "chaos": CHAOS_STATE}

@app.post("/chaos/resource")
def trigger_resource_exhaustion(duration: int = 8):
    """Burns CPU cycles for specified duration to trigger CPU saturation metrics."""
    logger.warning(f"CHAOS ACTIVE: Initiating CPU burn for {duration} seconds")
    start = time.time()
    while time.time() - start < duration:
        _ = [x * x for x in range(10000)]
    return {"status": "ok", "message": f"Resource burn completed ({duration}s)"}

@app.post("/chaos/reset")
def reset_chaos():
    CHAOS_STATE["latency_seconds"] = 0.0
    CHAOS_STATE["error_rate"] = 0.0
    CHAOS_STATE["is_corrupt"] = False
    logger.info("All chaos faults reset to healthy baseline")
    return {"status": "ok", "chaos": CHAOS_STATE}
