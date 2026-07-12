from prometheus_client import Counter, Histogram

SERVICE_NAME = "rag_embedder"

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

embedding_requests_total = Counter(
    "embedding_requests_total",
    "Nombre total de requêtes d'embedding",
)

embedding_errors_total = Counter(
    "embedding_errors_total",
    "Nombre total d'erreurs lors de l'embedding",
)

embedding_duration_seconds = Histogram(
    "embedding_duration_seconds",
    "Durée des requêtes d'embedding en secondes",
)
