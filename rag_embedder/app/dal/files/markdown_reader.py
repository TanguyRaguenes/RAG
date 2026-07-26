import os
from pathlib import Path

import aiofiles

from app.core.exceptions import MarkdownProcessingException
from app.domain.models.document_model import DocumentBase, DocumentsBase


async def read_markdown_documents() -> DocumentsBase:
    """Lit les fichiers Markdown depuis le dossier configuré.

    Le dossier source est défini par `RAG_WIKIS_DIR`. Si la variable est absente,
    le service lit `./data/wikis` relativement à son dossier de travail.

    Returns:
        Collection de documents Markdown avec leur chemin relatif et contenu.

    Raises:
        MarkdownProcessingException: Si un fichier Markdown ne peut pas être lu.
    """
    found_documents: list[DocumentBase] = []
    root: Path = Path(os.getenv("RAG_WIKIS_DIR", "./data/wikis")).resolve()

    for path in root.rglob("*.md"):
        if ".git" in path.parts:
            continue
        try:
            async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
                content = await f.read()

            document: DocumentBase = DocumentBase(
                path=path.relative_to(root).as_posix(), content=content
            )

            found_documents.append(document)

        except Exception as e:
            raise MarkdownProcessingException(
                message="Failed to read markdown document",
                details={"file": str(path)},
            ) from e

    return DocumentsBase(documents=found_documents)
