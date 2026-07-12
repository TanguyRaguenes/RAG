import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_telemetry() -> None:
    """Configure l'export OpenTelemetry vers Tempo.

    Returns:
        Aucune valeur. Le fournisseur de traces global est configuré.
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318/v1/traces")
    resource = Resource.create(
        {
            "service.name": "rag_evaluator",
            "service.version": "1.0.0",
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
