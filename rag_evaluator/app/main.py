from fastapi import FastAPI

from app.api.routers.evaluate_router import router as evaluate_router
from app.api.lifespan import lifespan


app = FastAPI(
    title="RAG_EVALUATOR",
    description="",
    version="1.0.0",
    lifespan=lifespan
    )

app.include_router(evaluate_router)

@app.get("/")
def read_root():
    return {
            "status": "ok",
            "message": "API connection successful"
        }
