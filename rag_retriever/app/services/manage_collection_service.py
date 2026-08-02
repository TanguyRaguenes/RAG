from app.core.config import CollectionProfile, RetrieverConfig, get_collection_name
from app.core.exceptions import CollectionException, VectorStoreException
from app.core.metrics import retriever_collection_size
from app.domain.vector_store_repository import VectorStoreRepositoryProtocol


def delete_collection(
    config: RetrieverConfig,
    vector_store_repository: VectorStoreRepositoryProtocol,
    collection_profile: CollectionProfile = "default",
) -> None:
    """Supprime puis recrée la collection configurée.

    Args:
        config: Configuration contenant les collections autorisées.
        vector_store_repository: Repository ChromaDB utilisé pour supprimer et recréer la collection.
        collection_profile: Profil fixe de la collection à réinitialiser.

    Returns:
        Aucune valeur.

    Raises:
        CollectionException: Si ChromaDB échoue pendant l'opération.
        KeyError: Si le profil demandé est absent de la configuration.
    """
    collection_name = get_collection_name(config, collection_profile)
    try:
        vector_store_repository.reset_collection(collection_name)
    except VectorStoreException as exception:
        raise CollectionException(
            internal_details={"operation": "reset_collection"},
        ) from exception

    retriever_collection_size.labels(collection=collection_name).set(0)
