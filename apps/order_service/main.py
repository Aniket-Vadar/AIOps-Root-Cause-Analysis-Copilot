import os
import time
import uuid
import logging
from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.responses import PlainTextResponse
import httpx
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# OpenTelemetry Setup
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [order-service] %(message)s')
logger = logging.getLogger("order-service")

# Initialize OpenTelemetry Tracer
resource = Resource.create({"service.name": "order-service"})
provider = TracerProvider(resource=resource)
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317")
try:
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
except Exception as e:
    logger.warning(f"Could not connect to OTLP exporter at {otlp_endpoint}: {e}")

tracer = trace.get_tracer("order-service")

app = FastAPI(title="Order Service", version="1.0.0")
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

PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8002")

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
        logger.error(f"Unhandled exception in request processing: {e}", exc_info=True)
        raise
    finally:
        duration = time.time() - start_time
        endpoint = request.url.path
        if endpoint != "/metrics":
            REQUESTS_TOTAL.labels(
                service="order-service",
                method=request.method,
                endpoint=endpoint,
                status=str(status_code)
            ).inc()
            REQUEST_DURATION.labels(
                service="order-service",
                endpoint=endpoint
            ).observe(duration)
    return response

@app.get("/health")
def health():
    return {"status": "ok", "service": "order-service"}

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/order")
async def create_order(request: Request):
    order_id = str(uuid.uuid4())[:8]
    amount = 49.99
    
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.amount", amount)
        logger.info(f"Received new order request. order_id={order_id}, amount=${amount}")

        # Call downstream payment service
        async with httpx.AsyncClient(timeout=3.5) as client:
            try:
                logger.info(f"Dispatching charge to payment-service: {PAYMENT_SERVICE_URL}/pay")
                pay_resp = await client.post(
                    f"{PAYMENT_SERVICE_URL}/pay",
                    json={"order_id": order_id, "amount": amount}
                )
                if pay_resp.status_code != 200:
                    logger.error(f"Payment failed for order_id={order_id}. Downstream status: {pay_resp.status_code}, Body: {pay_resp.text}")
                    span.set_attribute("order.status", "FAILED")
                    span.set_status(trace.StatusCode.ERROR, f"Payment service returned {pay_resp.status_code}")
                    raise HTTPException(status_code=502, detail=f"Downstream payment failure: {pay_resp.text}")

                logger.info(f"Payment successful for order_id={order_id}")
                span.set_attribute("order.status", "CONFIRMED")
                return {"status": "CONFIRMED", "order_id": order_id, "amount": amount}

            except httpx.TimeoutException:
                logger.error(f"TIMEOUT: Payment service timed out (>3.5s) for order_id={order_id}", exc_info=True)
                span.set_status(trace.StatusCode.ERROR, "Downstream payment timeout")
                raise HTTPException(status_code=504, detail="Downstream payment gateway timeout")
            except httpx.RequestError as exc:
                logger.error(f"COMMUNICATION ERROR: Unable to reach payment service: {exc}", exc_info=True)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                raise HTTPException(status_code=503, detail="Payment service unreachable")

@app.post("/order/fail-fast")
def fail_fast():
    """Chaos endpoint: Immediately raises an unhandled ValueError to test log correlation."""
    logger.error("FATAL: Corrupted transaction payload received. Invalid payment routing pointer: NULL_REF_PTR")
    raise ValueError("Internal state corruption: missing required ledger transaction key")
