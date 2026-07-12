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

    # Déclare les métadonnées du service.
    #
    # Dans Grafana tu verras apparaître :
    #
    # service.name = rag_embedder
    #
    resource = Resource.create(
        {
            "service.name": "rag_embedder",
        }
    )

    # Création du fournisseur de traces.
    #
    # C'est lui qui va gérer toutes les traces générées
    # dans l'application.
    provider = TracerProvider(resource=resource)

    # Configuration de la destination.
    #
    # Toutes les traces seront envoyées vers Tempo.
    #
    # tempo = nom du service Docker Compose
    # 4318 = port OTLP HTTP
    #
    exporter = OTLPSpanExporter(endpoint="http://tempo:4318/v1/traces")

    # Ajoute un processeur chargé d'envoyer les traces.
    #
    # BatchSpanProcessor :
    # - regroupe plusieurs traces
    # - réduit le trafic réseau
    # - améliore les performances
    #
    provider.add_span_processor(BatchSpanProcessor(exporter))

    # Enregistre ce provider comme provider global.
    #
    # Toutes les traces OpenTelemetry de l'application
    # utiliseront désormais cette configuration.
    #
    trace.set_tracer_provider(provider)
