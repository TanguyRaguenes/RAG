from pathlib import Path

import aiofiles

from app.core.exceptions import MarkdownProcessingException
from app.domain.models.document_model import DocumentBase, DocumentsBase


async def read_markdown_documents() -> DocumentsBase:
    """Lit les fichiers Markdown et construit les modèles de documents à ingérer.

    Returns:
        Collection de documents Markdown avec leur chemin et contenu.

    Raises:
        MarkdownProcessingException: Si le traitement rencontre une erreur applicative explicitement propagée.
    """
    found_documents: list[DocumentBase] = []
    root: Path = Path("./wikis").resolve()

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
