from fastapi import FastAPI

from src.app.api.routers.query_router import router as llm_router
from src.app.api.routers.ingest_router import router as ingest_router
from src.app.api.lifespan import lifespan


app = FastAPI(lifespan=lifespan)

app.include_router(llm_router)
app.include_router(ingest_router)

@app.get("/")
def read_root():
    return {
            "status": "ok",
            "message": "API connection successful"
        }
