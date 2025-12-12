from fastapi import FastAPI
from app.api.llm_routes import router as llm_router

app = FastAPI()
app.include_router(llm_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}
