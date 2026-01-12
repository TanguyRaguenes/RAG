from fastapi import FastAPI

from app.api.routers.query_router import router as query_router
from app.api.lifespan import lifespan


app = FastAPI(
    title="RAG_API",
    description="",
    version="1.0.0",
    lifespan=lifespan
    )

app.include_router(query_router)

@app.get("/")
def read_root():
    return {
            "status": "ok",
            "message": "API connection successful"
        }
