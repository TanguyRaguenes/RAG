from prometheus_client import Counter, Gauge, Histogram

SERVICE_NAME = "rag_retriever"

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

retriever_requests_total = Counter(
    "retriever_requests_total",
    "Nombre total de requêtes traitées par le retriever",
    ["operation", "status"],
)

retriever_errors_total = Counter(
    "retriever_errors_total",
    "Nombre total d'erreurs du retriever",
    ["operation", "error_type"],
)

retriever_duration_seconds = Histogram(
    "retriever_duration_seconds",
    "Durée des opérations du retriever en secondes",
    ["operation", "status"],
)

retriever_chroma_duration_seconds = Histogram(
    "retriever_chroma_duration_seconds",
    "Durée des opérations ChromaDB en secondes",
    ["operation", "status"],
)

retriever_chunks_total = Counter(
    "retriever_chunks_total",
    "Nombre total de chunks lus ou écrits par le retriever",
    ["operation"],
)

retriever_collection_size = Gauge(
    "retriever_collection_size",
    "Nombre courant d'items dans la collection ChromaDB",
    ["collection"],
)
