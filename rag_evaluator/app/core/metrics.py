from prometheus_client import Counter, Gauge, Histogram

SERVICE_NAME = "rag_evaluator"

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

evaluator_requests_total = Counter(
    "evaluator_requests_total",
    "Nombre total d'évaluations RAG lancées",
    ["operation", "status"],
)

evaluator_errors_total = Counter(
    "evaluator_errors_total",
    "Nombre total d'erreurs de l'evaluator",
    ["operation", "error_type"],
)

evaluator_duration_seconds = Histogram(
    "evaluator_duration_seconds",
    "Durée des opérations de l'evaluator en secondes",
    ["operation", "status"],
)

evaluator_external_call_duration_seconds = Histogram(
    "evaluator_external_call_duration_seconds",
    "Durée des appels externes de l'evaluator en secondes",
    ["dependency", "operation", "status"],
)

evaluator_questions_total = Counter(
    "evaluator_questions_total",
    "Nombre total de questions évaluées",
    ["status"],
)

evaluator_score = Gauge(
    "evaluator_score",
    "Dernier score moyen calculé par l'evaluator",
    ["metric"],
)
