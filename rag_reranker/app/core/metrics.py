from prometheus_client import Counter, Histogram

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
