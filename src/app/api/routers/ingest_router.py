import time

from fastapi import APIRouter, Request
from src.app.services.ingestion_service import ingest_pages
from src.app.dal.files.markdown_reader import read_markdown_pages
from src.app.schemas.ingest_request_schema import IngestRequestBase
from src.app.schemas.ingest_response_schema import IngestResponseBase
from pathlib import Path

router = APIRouter()

@router.post("/ingest/bulk", response_model=IngestResponseBase)
async def bulk_route(request: Request) -> IngestResponseBase:

    start:float = time.perf_counter()

    config = request.app.state.config
    vector_db_service  = request.app.state.vector_db_service 
    wikis_collection = request.app.state.wikis_collection

    WIKI_DIR = Path("./RAG.wiki")  # chemin vers le repo cloné

    pages:list[dict] = await read_markdown_pages(WIKI_DIR)

    print(f"{len(pages)} pages trouvées\n")

    ingested : dict = await ingest_pages(pages,config, wikis_collection, vector_db_service)


    elapsed:float = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration:str = f"{minutes:02d}:{seconds:02d}"
    
    return IngestResponseBase(
        answer="bulk successful",
        collection_count_before=ingested["collection_count_before"],
        collection_count_after=ingested["collection_count_after"],
        written_items=ingested["written_items"], 
        duration=duration)
