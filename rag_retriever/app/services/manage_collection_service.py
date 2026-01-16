def delete_collection(config, vector_store_repository):
    collection_name: str = config["collection"]["name"]
    vector_store_repository.delete_collection_by_name(collection_name)
    vector_store_repository.get_or_create_collection(collection_name)
