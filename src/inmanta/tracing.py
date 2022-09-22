# Setup tracing
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.tornado import TornadoInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
if "OTEL_EXPORTER_OTLP_ENDPOINT=" in os.environ:
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)

trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

TornadoInstrumentor().instrument()
AsyncPGInstrumentor().instrument()
