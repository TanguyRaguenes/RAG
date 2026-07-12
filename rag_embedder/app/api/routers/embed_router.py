import time
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_config
from app.domain.models.document_model import DocumentsBase
from app.domain.models.embed_request_model import EmbedRequestBase
from app.schemas.embed_text_response_schema import EmbedTextResponseBase
from app.schemas.ingest_bulk_response_schema import IngestBulkResponseBase
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.services.embed_service import embed as service_embed
from app.services.ingest_documents_service import ingest_documents
from app.services.load_documents_service import load_documents

router = APIRouter()

ConfigDep = Annotated[dict, Depends(get_config)]


@router.post("/embed")
async def embed_route(
    payload: EmbedRequestBase,
    config: ConfigDep,
) -> EmbedTextResponseBase:

    start: float = time.perf_counter()

    embeded_texts: list[list[float]] = await service_embed(payload.texts, config)

    elapsed: float = time.perf_counter() - start

    duration_ms = round(elapsed * 1000, 2)

    minutes, seconds = divmod(int(elapsed), 60)
    duration_human: str = f"{minutes:02d}:{seconds:02d}"

    response: EmbedTextResponseBase = EmbedTextResponseBase(
        duration_ms=duration_ms,
        duration_human=duration_human,
        embeded_texts=embeded_texts,
    )

    return response


@router.post("/ingest/bulk")
async def ingest_bulk_route(config: ConfigDep) -> IngestBulkResponseBase:
    start: float = time.perf_counter()

    documents: DocumentsBase = await load_documents()

    ingested_documents: SaveItemsResponseBase = await ingest_documents(
        documents, config
    )

    elapsed: float = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration: str = f"{minutes:02d}:{seconds:02d}"

    return IngestBulkResponseBase(duration=duration, savedItems=ingested_documents)
