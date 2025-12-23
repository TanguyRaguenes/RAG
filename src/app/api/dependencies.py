
from fastapi import Request
from chromadb.api.models.Collection import Collection
from src.app.dal.repositories.vector_store_repository import VectorStoreRepository

def get_config(request: Request) -> dict:
    return request.app.state.config

def get_vector_store_repository(request: Request) -> VectorStoreRepository:
    return request.app.state.vector_store_repository

def get_wikis_collection(request: Request) -> Collection:
    return request.app.state.wikis_collection