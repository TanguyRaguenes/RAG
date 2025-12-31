import time

from fastapi import APIRouter, Depends
from app.services.ingestion_service import ingest_pages
from app.dal.files.markdown_reader import read_markdown_pages
from app.schemas.ingest_request_schema import IngestRequestBase
from app.schemas.ingest_response_schema import IngestResponseBase
from pathlib import Path
from app.api.dependencies import get_config, get_wikis_collection, get_vector_store_repository

router = APIRouter()

@router.post("/ingest/bulk", response_model=IngestResponseBase)
async def bulk_route(
        config = Depends(get_config),
        vector_store_repository  = Depends(get_vector_store_repository),
    ) -> IngestResponseBase:

    start:float = time.perf_counter()

    WIKI_DIR = Path("./RAG.wiki")  # chemin vers le repo cloné

    pages:list[dict] = await read_markdown_pages(WIKI_DIR)

    print(f"{len(pages)} pages trouvées\n")

    ingested : dict = await ingest_pages(pages,config, vector_store_repository)


    elapsed:float = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration:str = f"{minutes:02d}:{seconds:02d}"
    
    return IngestResponseBase(
        answer="bulk successful",
        collection_count_before=ingested["collection_count_before"],
        collection_count_after=ingested["collection_count_after"],
        written_items=ingested["written_items"], 
        duration=duration)


@router.post("/ingest/delete_collection", response_model=str)
async def clear_collection_route(
    vector_store_repository  = Depends(get_vector_store_repository),
    wikis_collection = Depends(get_wikis_collection)
    )->str:

    vector_store_repository.delete_collection_by_name(wikis_collection.name)
    vector_store_repository.get_or_create_collection("wiki_chunks")

    return f"Collection : {wikis_collection.name} bien supprimée."