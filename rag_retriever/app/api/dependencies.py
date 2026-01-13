from chromadb.api.models.Collection import Collection
from fastapi import Request

from app.dal.repositories.vector_store_repository import VectorStoreRepository


def get_config(request: Request) -> dict:
    return request.app.state.config


def get_vector_store_repository(request: Request) -> VectorStoreRepository:
    return request.app.state.vector_store_repository


def get_wikis_collection(request: Request) -> Collection:
    repository = request.app.state.vector_store_repository
    config = request.app.state.config
    collection_name: str = config["collection"]["name"]
    return repository.get_or_create_collection(collection_name)
