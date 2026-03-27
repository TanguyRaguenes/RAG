import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.lifespan import lifespan
from app.api.routers.query_router import router as query_router
from app.core.exceptions import OrchestratorContainerCustomException

app = FastAPI(
    title="RAG_ORCHESTRATOR", description="", version="1.0.0", lifespan=lifespan
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

app.include_router(query_router)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "API connection successful"}


@app.exception_handler(OrchestratorContainerCustomException)
async def embedder_exception_handler(
    request: Request, exception: OrchestratorContainerCustomException
):
    """Handler centralisé pour les exceptions métier"""

    "Ici on génère les log qui seront affiché dans la console "
    logger.error(
        f"[{exception.SLUG}] {exception.message} | path={request.url.path} | details={exception.details}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=exception.STATUS_CODE,
        content=exception.to_dict(),
    )
