from app.dal.clients.embedding_client import embed_text as client_embed_text

async def embed_text(text:str, config:dict)->list[float]:

    text_embedding:list[float] = await client_embed_text(text, config)

    return text_embedding