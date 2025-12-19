import time

from fastapi import APIRouter, Request
from src.app.services.embedding_service import read_markdown_files, embed_text
from src.app.schemas.embedding_request_schema import embeddingRequestBase
from src.app.schemas.embedding_response_schema import embeddingResponseBase
from pathlib import Path

router = APIRouter()

@router.post("/embedBulk", response_model=embeddingResponseBase)
async def ask_question_route(request: Request) -> embeddingResponseBase:

    start:float = time.perf_counter()

    config:any = request.app.state.config
    WIKI_DIR = Path("./RAG.wiki")  # chemin vers le repo cloné

    pages:list[dict] = await read_markdown_files(WIKI_DIR)

    print(f"{len(pages)} pages trouvées\n")
    for p in pages:
        print("----", p["page_path"])
        print(p["content"][:200], "...\n")

    vectors=[]
    for p in pages:
        answer = await embed_text(p["content"], config)
        vectors.append({
            "page_path": p["page_path"],
            "embedding": answer
        })

    elapsed:float = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration:str = f"{minutes:02d}:{seconds:02d}"
    
    return embeddingResponseBase(answer=vectors, duration=duration)
