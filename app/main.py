from fastapi import FastAPI
from app.api.llm_routes import router as llm_router
from app.bl.bulk import read_markdown_files
from pathlib import Path

app = FastAPI()
app.include_router(llm_router)

@app.get("/")
def read_root():
    WIKI_DIR = Path("./RAG.wiki")  # chemin vers le repo cloné

    pages = read_markdown_files(WIKI_DIR)

    print(f"{len(pages)} pages trouvées\n")
    for p in pages:
        print("----", p["page_path"])
        print(p["content"][:200], "...\n")
    return {"Hello": "World"}
