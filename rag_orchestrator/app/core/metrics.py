from prometheus_client import Counter, Histogram

SERVICE_NAME = "rag_orchestrator"

rag_requests_total = Counter(
    "rag_requests_total",
    "Nombre total de requêtes métier RAG traitées",
    ["service", "operation", "status"],
)

rag_errors_total = Counter(
    "rag_errors_total",
    "Nombre total d'erreurs métier RAG",
    ["service", "operation", "error_type"],
)

rag_request_duration_seconds = Histogram(
    "rag_request_duration_seconds",
    "Durée des requêtes métier RAG en secondes",
    ["service", "operation", "status"],
)

rag_tokens_total = Counter(
    "rag_tokens_total",
    "Nombre total de tokens consommés par les requêtes RAG",
    ["service", "provider", "model", "token_type"],
)

rag_cost_usd_total = Counter(
    "rag_cost_usd_total",
    "Coût estimé cumulé des requêtes RAG en dollars US",
    ["service", "provider", "model"],
)

rag_cost_eur_total = Counter(
    "rag_cost_eur_total",
    "Coût estimé cumulé des questions RAG en euros",
    ["service", "provider", "model"],
)

orchestrator_requests_total = Counter(
    "orchestrator_requests_total",
    "Nombre total de requêtes traitées par l'orchestrator",
    ["operation", "status"],
)

orchestrator_errors_total = Counter(
    "orchestrator_errors_total",
    "Nombre total d'erreurs de l'orchestrator",
    ["operation", "error_type"],
)

orchestrator_duration_seconds = Histogram(
    "orchestrator_duration_seconds",
    "Durée des opérations de l'orchestrator en secondes",
    ["operation", "status"],
)

orchestrator_external_call_duration_seconds = Histogram(
    "orchestrator_external_call_duration_seconds",
    "Durée des appels externes de l'orchestrator en secondes",
    ["dependency", "operation", "status"],
)

orchestrator_external_call_errors_total = Counter(
    "orchestrator_external_call_errors_total",
    "Nombre total d'erreurs des appels externes de l'orchestrator",
    ["dependency", "operation", "error_type"],
)

orchestrator_tokens_total = Counter(
    "orchestrator_tokens_total",
    "Nombre total de tokens consommés par provider et modèle",
    ["provider", "model", "token_type"],
)

orchestrator_cost_total = Counter(
    "orchestrator_cost_total",
    "Coût estimé cumulé des appels LLM",
    ["provider", "model"],
)

orchestrator_chunks_total = Counter(
    "orchestrator_chunks_total",
    "Nombre total de chunks récupérés par l'orchestrator",
    ["operation"],
)


def initialize_question_metrics(provider: str, model: str) -> None:
    """Crée les séries Prometheus liées aux questions avant la première requête.

    Sans cette initialisation, Prometheus découvre une série directement à 1 et
    `increase(...)` ne compte pas cette première question dans les dashboards.
    """
    operation = "ask_question"

    for status in ("success", "error"):
        rag_requests_total.labels(
            service=SERVICE_NAME,
            operation=operation,
            status=status,
        ).inc(0)
        rag_request_duration_seconds.labels(
            service=SERVICE_NAME,
            operation=operation,
            status=status,
        )

    for token_type in ("input", "output", "total"):
        rag_tokens_total.labels(
            service=SERVICE_NAME,
            provider=provider,
            model=model,
            token_type=token_type,
        ).inc(0)

    rag_cost_usd_total.labels(
        service=SERVICE_NAME,
        provider=provider,
        model=model,
    ).inc(0)
    rag_cost_eur_total.labels(
        service=SERVICE_NAME,
        provider=provider,
        model=model,
    ).inc(0)
