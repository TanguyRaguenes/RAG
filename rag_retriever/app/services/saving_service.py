from app.core.exceptions import VectorStoreException
from app.core.metrics import retriever_chunks_total, retriever_collection_size
from app.schemas.save_items_response_schema import SavedItemBase, SaveItemsResponseBase
from app.schemas.vector_db_items_schema import VectorStoreItemsBase


def save_items(
    items: VectorStoreItemsBase, vector_store_repository
) -> SaveItemsResponseBase:
    """Sauvegarde ou met à jour des items vectoriels dans la collection wiki.

    Args:
        items: Items vectoriels à persister.
        vector_store_repository: Repository ChromaDB utilisé pour écrire et relire les items.

    Returns:
        Résumé de sauvegarde contenant les compteurs et items relus.

    Raises:
        VectorStoreException: Si ChromaDB échoue pendant la sauvegarde ou la relecture.
    """
    try:
        wikis_collection = vector_store_repository.get_or_create_collection(
            "wiki_chunks"
        )

        collection_count_before = wikis_collection.count()

        vector_store_repository.insert_or_update_items_in_collection(
            wikis_collection, items
        )

        saved_items: list[SavedItemBase] = vector_store_repository.get_collection_items(
            collection=wikis_collection,
            ids=items.ids,
            columns=["documents", "metadatas"],
        )
        collection_count_after = wikis_collection.count()
    except Exception as exception:
        if isinstance(exception, VectorStoreException):
            raise
        raise VectorStoreException(
            message="Erreur lors de la sauvegarde des items vectoriels",
            details={"operation": "save_items", "item_count": len(items.ids)},
        ) from exception

    retriever_chunks_total.labels(operation="save_items").inc(len(items.ids))
    retriever_collection_size.labels(collection="wiki_chunks").set(
        collection_count_after
    )

    return SaveItemsResponseBase(
        collection_count_before=collection_count_before,
        collection_count_after=collection_count_after,
        saved_items=saved_items,
    )
