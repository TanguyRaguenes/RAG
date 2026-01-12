import aiofiles
from pathlib import Path
from app.domain.models.document_model import DocumentBase, DocumentsBase

async def read_markdown_documents()->DocumentsBase:

    path:str = Path("./wikis")  # chemin vers la copie dans le container des wikis

    found_documents:list[DocumentBase]=[]
    root = Path(path).resolve()

    for path in root.rglob("*.md"):

        # Pour un chemin comme : /app/RAG.wiki/.git/objects/ab/cd
        # path.parts donne ("app", "RAG.wiki", ".git", "objects", "ab", "cd")
        # continue arrête l’itération courante passe directement au fichier suivant

        if ".git" in path.parts:
            continue

        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            content = await f.read()
        
        document:DocumentBase=DocumentBase(
            path= path.relative_to(root).as_posix(),
            content=content
        )

        found_documents.append(document)
    
    documents:DocumentsBase=DocumentsBase(
        documents=found_documents
    )
            
    return documents
