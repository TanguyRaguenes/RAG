from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app

from app.api.lifespan import lifespan
from app.api.routers.evaluate_router import router as evaluate_router
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_json_logging
from app.core.telemetry import configure_telemetry

configure_json_logging("rag_evaluator")

app = FastAPI(title="RAG_EVALUATOR", description="", version="1.0.0", lifespan=lifespan)

configure_telemetry()
FastAPIInstrumentor.instrument_app(app)
app.mount("/metrics", make_asgi_app())

app.include_router(evaluate_router)
register_exception_handlers(app)


@app.get("/")
def read_root() -> dict[str, str]:
    """Retourne l'état de santé minimal de l'API.

    Returns:
        Dictionnaire indiquant que l'API répond correctement.
    """
    return {"status": "ok", "message": "API connection successful"}
