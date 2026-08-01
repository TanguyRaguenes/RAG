import time

from app.core.config import EmbedderConfig
from app.dal.clients.embedding_client import embed as client_embed
from app.schemas.embed_text_response_schema import EmbedTextResponseBase


async def embed(texts: list[str], config: EmbedderConfig) -> list[list[float]]:
    """Génère des embeddings pour une liste de textes via le client configuré.

    Args:
        texts: Textes à vectoriser ou normaliser.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.

    Returns:
        Liste d'embeddings alignée avec les textes d'entrée.
    """
    text_embeddings: list[list[float]] = await client_embed(texts, config, True)

    return text_embeddings


async def create_embeddings_response(
    texts: list[str], config: EmbedderConfig
) -> EmbedTextResponseBase:
    """Génère les embeddings et construit la réponse HTTP chronométrée.

    Args:
        texts: Textes validés reçus par l'API.
        config: Configuration du fournisseur d'embeddings.

    Returns:
        Embeddings accompagnés des durées historique et millisecondes.
    """
    start = time.perf_counter()
    embedded_texts = await embed(texts, config)
    elapsed = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    return EmbedTextResponseBase(
        duration_ms=round(elapsed * 1000, 2),
        duration_human=f"{minutes:02d}:{seconds:02d}",
        embeded_texts=embedded_texts,
    )
