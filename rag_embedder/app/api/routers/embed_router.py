from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_config
from app.core.config import EmbedderConfig
from app.schemas.embed_request_schema import EmbedRequestBase
from app.schemas.embed_text_response_schema import EmbedTextResponseBase
from app.schemas.ingest_bulk_response_schema import IngestBulkResponseBase
from app.schemas.vector_store_items_schema import CollectionProfile
from app.services.embed_service import create_embeddings_response
from app.services.ingest_documents_service import ingest_all_documents

router = APIRouter()

ConfigDep = Annotated[EmbedderConfig, Depends(get_config)]


@router.post("/embed")
async def embed_route(
    payload: EmbedRequestBase,
    config: ConfigDep,
) -> EmbedTextResponseBase:
    """Expose l'endpoint HTTP de génération d'embeddings.

    Args:
        payload: Corps JSON transmis à une API externe ou persisté en base.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.

    Returns:
        Réponse HTTP contenant les embeddings et la durée de génération.
    """
    return await create_embeddings_response(payload.texts, config)


@router.post("/ingest/bulk")
async def ingest_bulk_route(
    config: ConfigDep,
    profile: CollectionProfile = "default",
) -> IngestBulkResponseBase:
    """Expose l'endpoint HTTP d'ingestion complète des documents Markdown.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        profile: Profil fixe déterminant le dossier source et la collection cible.

    Returns:
        Réponse HTTP contenant la durée et le résultat de sauvegarde.
    """
    return await ingest_all_documents(config, profile)
