from prometheus_client import Counter, Histogram

SERVICE_NAME = "rag_reranker"

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

reranking_requests_total = Counter(
    "reranking_requests_total",
    "Nombre total de requêtes de reranking",
)

reranking_errors_total = Counter(
    "reranking_errors_total",
    "Nombre total d'erreurs lors du reranking",
)

reranking_duration_seconds = Histogram(
    "reranking_duration_seconds",
    "Durée des requêtes de reranking en secondes",
)
