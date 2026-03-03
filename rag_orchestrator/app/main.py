from fastapi import FastAPI

from app.api.lifespan import lifespan
from app.api.routers.query_router import router as query_router

app = FastAPI(
    title="RAG_ORCHESTRATOR", description="", version="1.0.0", lifespan=lifespan
)

app.include_router(query_router)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "API connection successful"}
