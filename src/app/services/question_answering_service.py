import httpx
from typing import Any
from src.app.services.embedding_service import embed_text
from src.app.services.prompt_builder_service import build_message



async def ask_question(question: str, config:dict, wikis_collection, vector_db_service) -> str:

    base_url = config["llm"]["url_provider"]
    model = config["llm"]["model"]
    timeout_seconds = config["llm"]["timeout_seconds"]
    temperature = config["llm"]["temperature"]
    stream = config["llm"]["stream"]
    max_tokens = config["llm"]["max_tokens"]

    top_k = config["retriever"]["top_k"]
    max_chars = config["context_builder"]["max_chars"]

    query_embedding:list[float]=await embed_text(question,config)
    retrieved_chunks:list[dict[str, Any]]  = vector_db_service.retrieve_chunks(wikis_collection,query_embedding,top_k)

    if not retrieved_chunks:
        return "Je ne sais pas."

    message:list[dict[str, str]]=build_message(question,retrieved_chunks,max_chars)

    payload: dict[str, Any] = {
        "model": model,
        "messages": message,
        "temperature": temperature,
        "stream": stream,
        "max_tokens":max_tokens
    }

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        r = await client.post(f"{base_url}/v1/chat/completions", json=payload)
        r.raise_for_status()
        data = r.json()

    return data["choices"][0]["message"]["content"]
