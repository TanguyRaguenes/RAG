import time

from fastapi import APIRouter, Depends

from app.api.dependencies import get_config
from app.domain.models.document_model import DocumentsBase
from app.domain.models.embed_text_request_model import EmbedTextRequestBase
from app.schemas.embed_text_response_schema import EmbedTextResponseBase
from app.schemas.ingest_bulk_response_schema import IngestBulkResponseBase
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.services.embed_text_service import embed_text as service_embed_text
from app.services.ingest_documents_service import ingest_documents
from app.services.load_documents_service import load_documents

router = APIRouter()


@router.post("/embed_text", response_model=EmbedTextResponseBase)
async def embed_text_route(
    payload: EmbedTextRequestBase,
    config=Depends(get_config),
) -> EmbedTextResponseBase:
    embeded_text: list[float] = await service_embed_text(payload.text, config)

    response: EmbedTextResponseBase = EmbedTextResponseBase(embeded_text=embeded_text)

    return response


@router.post("/ingest/bulk", response_model=IngestBulkResponseBase)
async def ingest_bulk_route(config=Depends(get_config)) -> IngestBulkResponseBase:
    start: float = time.perf_counter()

    documents: DocumentsBase = await load_documents()

    ingested_documents: SaveItemsResponseBase = await ingest_documents(
        documents, config
    )

    elapsed: float = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration: str = f"{minutes:02d}:{seconds:02d}"

    return IngestBulkResponseBase(duration=duration, savedItems=ingested_documents)
