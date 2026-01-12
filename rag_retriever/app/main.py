from fastapi import FastAPI

from app.api.routers.collections_router import router as collections_router
from app.api.lifespan import lifespan

app = FastAPI(
    title="RAG_RETRIEVER",
    description="",
    version="1.0.0",
    lifespan=lifespan
    )

app.include_router(collections_router)

@app.get("/")
def read_root():
    return {
            "status": "ok",
            "message": "API connection successful"
        }
