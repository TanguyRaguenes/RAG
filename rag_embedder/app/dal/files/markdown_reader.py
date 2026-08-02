import os
from pathlib import Path

import aiofiles

from app.core.exceptions import MarkdownProcessingException
from app.domain.models.document_model import DocumentBase, DocumentsBase


async def read_markdown_documents(root: Path | None = None) -> DocumentsBase:
    """Lit les fichiers Markdown depuis le dossier configuré.

    Le dossier source est défini par `RAG_WIKIS_DIR`. Si la variable est absente,
    le service lit `./data/wikis` relativement à son dossier de travail.

    Args:
        root: Dossier source explicite, ou dossier configuré par défaut.

    Returns:
        Collection de documents Markdown avec leur chemin relatif et contenu.

    Raises:
        MarkdownProcessingException: Si un fichier Markdown ne peut pas être lu.
    """
    found_documents: list[DocumentBase] = []
    source_root = root or Path(os.getenv("RAG_WIKIS_DIR", "./data/wikis"))
    resolved_root = source_root.resolve()

    for path in resolved_root.rglob("*.md"):
        if ".git" in path.parts:
            continue
        relative_path = path.relative_to(resolved_root).as_posix()
        try:
            async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
                content = await f.read()

            document = DocumentBase(path=relative_path, content=content)

            found_documents.append(document)

        except (OSError, UnicodeError) as exception:
            raise MarkdownProcessingException(
                internal_details={
                    "operation": "read_markdown_document",
                    "relative_path": relative_path,
                },
            ) from exception

    return DocumentsBase(documents=found_documents)
