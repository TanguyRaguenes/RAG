import aiofiles
from pathlib import Path

async def read_markdown_pages(path: Path)->list[dict]:
    pages = []
    root = Path(path).resolve()

    for path in root.rglob("*.md"):

        # Pour un chemin comme : /app/RAG.wiki/.git/objects/ab/cd
        # path.parts donne ("app", "RAG.wiki", ".git", "objects", "ab", "cd")
        # continue arrête l’itération courante passe directement au fichier suivant

        if ".git" in path.parts:
            continue

        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            content = await f.read()

        pages.append({
            "page_path": path.relative_to(root).as_posix(),
            "content": content
        })
    
    return pages
