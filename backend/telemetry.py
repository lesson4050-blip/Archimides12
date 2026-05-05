import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
import os
 
logger = logging.getLogger(__name__)

tracer: Optional[trace.Tracer] = None

def init_telemetry(app=None):
    """Initialize OpenTelemetry with OTLP exporter (works with Grafana Tempo)."""
    global tracer
    
    # Only initialize if explicitly enabled via environment variable
    if not os.environ.get("ENABLE_TELEMETRY") and not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        logger.debug("Telemetry is disabled (ENABLE_TELEMETRY not set).")
        tracer = None
        return None

    # Try to load telemetry modules, fail gracefully if not installed
    try:
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317")
        
        provider = TracerProvider()
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        )
        trace.set_tracer_provider(provider)
        tracer = trace.get_tracer("archimedes.agent")
        
        if app:
            FastAPIInstrumentor.instrument_app(app)
            
    except ImportError:
        import logging
        logging.getLogger(__name__).warning("OpenTelemetry packages not installed. Tracing is disabled.")
        tracer = None
        
    return tracer

@asynccontextmanager
async def agent_span(
    operation: str,
    session_id: str,
    strategy: str = "unknown",
    **attributes: Any
):
    """
    Context manager for agent operation tracing.
    
    Usage in orchestrator:
        async with agent_span("planner.process", session_id, strategy="swarm_code"):
            state = await self.planner.process(state, websocket_send)
    """
    if tracer is None:
        yield  # No-op if telemetry not initialized
        return
    
    with tracer.start_as_current_span(operation) as span:
        span.set_attribute("session.id", session_id)
        span.set_attribute("agent.strategy", strategy)
        for k, v in attributes.items():
            span.set_attribute(k, str(v))
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise
