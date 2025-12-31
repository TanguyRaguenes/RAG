import httpx
from typing import Any
from src.app.domain.models.ask_question_response_model import AskQuestionResponseModel
from src.app.dal.clients.embedding_client import embed_text
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


    sources:list[str]=[]
    for chunck in retrieved_chunks:
        sources.append(chunck["metadata"]["path"])

    sources=list(set(sources))

    response:AskQuestionResponseModel ={
        "llm_answer":data["choices"][0]["message"]["content"],
        "sources": sources,
        "chuncks":retrieved_chunks
    }

    return response
