from app.schemas.save_items_response_schema import SavedItemBase, SaveItemsResponseBase


def save_items(items, vector_store_repository) -> SaveItemsResponseBase:
    wikis_collection = vector_store_repository.get_or_create_collection("wiki_chunks")

    collection_count_before = wikis_collection.count()

    vector_store_repository.insert_or_update_items_in_collection(
        wikis_collection, items
    )

    saved_items: list[SavedItemBase] = vector_store_repository.get_collection_items(
        collection=wikis_collection,
        ids=items.ids,
        columns=["documents", "metadatas"],
    )

    return SaveItemsResponseBase(
        collection_count_before=collection_count_before,
        collection_count_after=wikis_collection.count(),
        saved_items=saved_items,
    )
