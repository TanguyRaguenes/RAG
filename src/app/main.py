from fastapi import FastAPI
from src.app.api.routers.llm_router import router as llm_router
from src.app.api.routers.embedding_router import router as embedding_router

from src.app.core.config import load_config

app = FastAPI()
app.state.config = load_config()
app.include_router(llm_router)
app.include_router(embedding_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}
