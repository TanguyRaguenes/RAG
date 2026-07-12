from opentelemetry import trace

# Permet de décrire l'application qui envoie les traces.
from opentelemetry.sdk.resources import Resource

# Fournit l'implémentation concrète du système de traces.
from opentelemetry.sdk.trace import TracerProvider

# Envoie les traces par lot (plus performant qu'un envoi immédiat).
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Exporteur OTLP vers Tempo.
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)


def configure_telemetry() -> None:
    """Configure OpenTelemetry pour l'application.
    Cette méthode doit être appelée une seule fois au démarrage.
    """

    resource = Resource.create(
        {
            "service.name": "rag_reranker",
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint="http://tempo:4318/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
