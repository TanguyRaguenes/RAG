from app.core.config import RetrieverConfig
from app.core.exceptions import CollectionException, VectorStoreException
from app.core.metrics import retriever_collection_size
from app.domain.vector_store_repository import VectorStoreRepositoryProtocol


def delete_collection(
    config: RetrieverConfig,
    vector_store_repository: VectorStoreRepositoryProtocol,
) -> None:
    """Supprime puis recrée la collection configurée.

    Args:
        config: Configuration contenant `collection.name`.
        vector_store_repository: Repository ChromaDB utilisé pour supprimer et recréer la collection.

    Returns:
        Aucune valeur.

    Raises:
        CollectionException: Si ChromaDB échoue pendant l'opération.
        KeyError: Si `collection.name` est absent de la configuration.
    """
    collection_name: str = config["collection"]["name"]
    try:
        vector_store_repository.reset_collection(collection_name)
    except VectorStoreException as exception:
        raise CollectionException(
            internal_details={"operation": "reset_collection"},
        ) from exception

    retriever_collection_size.labels(collection=collection_name).set(0)
