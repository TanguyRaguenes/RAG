from app.dal.clients.embedding_client import embed as client_embed


async def embed(texts: list[str], config: dict) -> list[list[float]]:
    text_embeddings: list[list[float]] = await client_embed(texts, config, True)

    return text_embeddings
