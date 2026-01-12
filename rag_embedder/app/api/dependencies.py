
from fastapi import Request
from chromadb.api.models.Collection import Collection

def get_config(request: Request) -> dict:
    return request.app.state.config
