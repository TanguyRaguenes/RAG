from prometheus_client import Counter, Histogram

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
