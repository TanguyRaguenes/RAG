import logging
import sys

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.core.telemetry import configure_telemetry

from pythonjsonlogger.json import JsonFormatter

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.lifespan import lifespan
from app.api.routers.rerank_router import router as rerank_router
from app.core.exceptions import RerankerContainerCustomException
from prometheus_client import make_asgi_app


# Handler chargé d'écrire les logs sur la sortie standard (stdout).
# Dans Docker, c'est ce flux que récupère Alloy.
handler = logging.StreamHandler(sys.stdout)

# Format JSON des logs.
handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

# Récupération du logger racine de l'application.
root_logger = logging.getLogger()

# Suppression des handlers éventuellement configurés auparavant
# (par exemple via basicConfig()) afin d'éviter les doublons.
root_logger.handlers.clear()

# Ajout de notre handler JSON personnalisé.
root_logger.addHandler(handler)

# Niveau minimal des logs à enregistrer.
root_logger.setLevel(logging.INFO)


logger = logging.getLogger(__name__)

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


@app.get("/")
def read_root():
    return {"status": "ok", "message": "API connection successful"}


@app.exception_handler(RerankerContainerCustomException)
async def reranker_exception_handler(
    request: Request, exception: RerankerContainerCustomException
):
    """Handler centralisé pour les exceptions métier"""
    logger.exception(
        exception.message,
        extra={
            "group": "reranking",
            "event": "business_exception",
            "slug": exception.SLUG,
            "path": request.url.path,
            "details": exception.details,
            "status_code": exception.STATUS_CODE,
        },
    )

    return JSONResponse(
        status_code=exception.STATUS_CODE,
        content=exception.to_dict(),
    )
