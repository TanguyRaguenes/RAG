from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app

from app.api.lifespan import lifespan
from app.api.routers.rerank_router import router as rerank_router
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_json_logging
from app.core.telemetry import configure_telemetry

configure_json_logging("rag_reranker")

app = FastAPI(
    title="RAG_RERANKER",
    description="",
    version="1.0.0",
    lifespan=lifespan,
)

configure_telemetry()
FastAPIInstrumentor.instrument_app(app)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(rerank_router)
register_exception_handlers(app)


@app.get("/")
def read_root() -> dict[str, str]:
    """Retourne l'état de santé minimal du microservice.

    Returns:
        Payload de healthcheck indiquant que l'API est joignable.
    """
    return {"status": "ok", "message": "API connection successful"}
