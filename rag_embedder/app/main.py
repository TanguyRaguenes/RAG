from fastapi import FastAPI

from app.api.routers.embed_router import router as embed_router
from app.api.lifespan import lifespan

app = FastAPI(
    title="RAG_EMBEDDER",
    description="",
    version="1.0.0",
    lifespan=lifespan
    )

app.include_router(embed_router)

@app.get("/")
def read_root():
    return {
            "status": "ok",
            "message": "API connection successful"
        }
