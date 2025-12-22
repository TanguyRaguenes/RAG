from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.app.api.routers.query_router import router as llm_router
from src.app.api.routers.ingest_router import router as ingest_router

from src.app.core.config import load_config
from src.app.dal.repositories.vector_store_repository import VectorStoreRepository


@asynccontextmanager
async def lifespan(app: FastAPI):

    # startup
    app.state.config = load_config()
    app.state.vector_db_service = VectorStoreRepository(app.state.config)
    app.state.wikis_collection = app.state.vector_db_service.get_or_create_collection("wiki_chunks")

    yield

app = FastAPI(lifespan=lifespan)



app.include_router(llm_router)
app.include_router(ingest_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}
