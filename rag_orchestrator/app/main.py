from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app

from app.api.exception_handlers import (
    application_exception_handler,
    unexpected_exception_handler,
)
from app.api.lifespan import lifespan
from app.api.routers.auth_router import router as auth_router
from app.api.routers.query_router import router as query_router
from app.api.routers.usage_router import router as usage_router
from app.core.exceptions import ApplicationError
from app.core.logging import configure_json_logging
from app.core.telemetry import configure_telemetry

configure_json_logging("rag_orchestrator")

app = FastAPI(
    title="RAG_ORCHESTRATOR", description="", version="1.0.0", lifespan=lifespan
)

configure_telemetry()
FastAPIInstrumentor.instrument_app(app)
app.mount("/metrics", make_asgi_app())

app.include_router(query_router)
app.include_router(auth_router)
app.include_router(usage_router)
app.add_exception_handler(ApplicationError, application_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)


@app.get("/")
def read_root() -> dict[str, str]:
    """Retourne l'état de santé minimal de l'API.

    Returns:
        Dictionnaire indiquant que l'API répond correctement.
    """
    return {"status": "ok", "message": "API connection successful"}
