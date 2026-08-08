from contextlib import nullcontext
from threading import Lock

from app.core.config import RetrieverConfig, get_collection_name
from app.core.metrics import retriever_chunks_total, retriever_collection_size
from app.domain.vector_store_repository import VectorStoreRepositoryProtocol
from app.schemas.save_items_response_schema import SavedItemBase, SaveItemsResponseBase
from app.schemas.vector_db_items_schema import VectorMetadataBase, VectorStoreItemsBase

_DELETE_OBSOLETE_LOCK = Lock()


def save_items(
    items: VectorStoreItemsBase,
    config: RetrieverConfig,
    vector_store_repository: VectorStoreRepositoryProtocol,
) -> SaveItemsResponseBase:
    """Sauvegarde un lot et supprime ses obsolètes en mode synchronisation.

    Les anciens items ne sont supprimés qu'après la réussite de l'upsert. Une
    panne d'écriture ne détruit donc pas la dernière version exploitable. Le
    verrou sérialise les snapshots dans ce processus uniquement ; plusieurs
    replicas nécessiteraient un verrou distribué pour offrir la même garantie.

    Args:
        items: DTO vectoriel validé reçu depuis l'embedder.
        config: Configuration contenant le nom de la collection d'écriture.
        vector_store_repository: Port de stockage vectoriel injecté.

    Returns:
        Résumé compatible avec le contrat HTTP historique.

    Raises:
        VectorStoreException: Si une opération de persistance échoue.
        KeyError: Si le nom de collection manque dans la configuration.
    """
    collection_name = get_collection_name(config, items.collection_profile)
    synchronization_lock = (
        _DELETE_OBSOLETE_LOCK
        if items.delete_obsolete or items.replace_collection
        else nullcontext()
    )
    with synchronization_lock:
        collection_count_before = vector_store_repository.count_items(collection_name)
        if items.replace_collection:
            vector_store_repository.reset_collection(collection_name)
            existing_ids: set[str] = set()
        else:
            existing_ids = (
                set(vector_store_repository.list_item_ids(collection_name))
                if items.delete_obsolete
                else set()
            )

        vector_store_repository.upsert_items(collection_name, items.to_domain())

        if items.delete_obsolete and not items.replace_collection:
            obsolete_ids = sorted(existing_ids.difference(items.ids))
            vector_store_repository.delete_items(collection_name, obsolete_ids)

        stored_items = (
            vector_store_repository.get_items(collection_name, items.ids)
            if items.include_saved_items
            else []
        )
        collection_count_after = vector_store_repository.count_items(collection_name)

    retriever_chunks_total.labels(operation="save_items").inc(len(items.ids))
    retriever_collection_size.labels(collection=collection_name).set(
        collection_count_after
    )

    return SaveItemsResponseBase(
        collection_count_before=collection_count_before,
        collection_count_after=collection_count_after,
        saved_items=[
            SavedItemBase(
                id=item.id,
                chunk=item.document,
                metadatas=VectorMetadataBase(**item.metadata.to_storage_dict()),
            )
            for item in stored_items
        ],
    )
