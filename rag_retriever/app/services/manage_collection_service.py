from app.core.exceptions import CollectionException
from app.core.metrics import retriever_collection_size


def delete_collection(config: dict, vector_store_repository) -> None:
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
        vector_store_repository.delete_collection_by_name(collection_name)
        vector_store_repository.get_or_create_collection(collection_name)
    except Exception as exception:
        raise CollectionException(
            message="Erreur lors de la réinitialisation de la collection",
            details={"collection": collection_name},
        ) from exception

    retriever_collection_size.labels(collection=collection_name).set(0)
