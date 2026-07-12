from app.dal.clients.embedding_client import embed as client_embed


async def embed(texts: list[str], config: dict) -> list[list[float]]:
    """Génère des embeddings pour une liste de textes via le client configuré.

    Args:
        texts: Textes à vectoriser ou normaliser.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.

    Returns:
        Liste d'embeddings alignée avec les textes d'entrée.
    """
    text_embeddings: list[list[float]] = await client_embed(texts, config, True)

    return text_embeddings
