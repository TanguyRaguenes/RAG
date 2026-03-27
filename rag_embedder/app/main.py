import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.lifespan import lifespan
from app.api.routers.embed_router import router as embed_router
from app.core.exceptions import EmbedderContainerCustomException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG_EMBEDDER",
    description="",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(embed_router)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "API connection successful"}


@app.exception_handler(EmbedderContainerCustomException)
async def embedder_exception_handler(
    request: Request, exception: EmbedderContainerCustomException
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
