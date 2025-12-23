from src.app.services.chuncking_service import chunk_text
from src.app.dal.clients.embedding_client import embed_text
from src.app.schemas.vector_db_items_schema import VectorStoreItemsBase


async def ingest_pages(pages: list[dict], config: dict, wikis_collection, vector_db_service) -> dict:

    collection_count_before = wikis_collection.count()

    items = VectorStoreItemsBase(
        ids=[],
        documents=[],
        embeddings=[],
        metadatas=[],
    )

    for page in pages:
        chunks = chunk_text(page["content"], config)

        for i, chunk in enumerate(chunks):
            emb = await embed_text(chunk, config) 

            items.ids.append(f"{page['page_path']}#chunk_{i}")
            items.documents.append(chunk)
            items.embeddings.append(emb) 
            items.metadatas.append({"path": page["page_path"], "chunk": i})

    vector_db_service.insert_or_update_items_in_collection(wikis_collection, items)

    written_items = vector_db_service.get_collection_items(
        collection=wikis_collection,
        ids=items.ids,
        columns=["documents", "metadatas"],
    )

    return {
        "collection_count_before": collection_count_before,
        "collection_count_after": wikis_collection.count(),
        "written_items": written_items,
    }
