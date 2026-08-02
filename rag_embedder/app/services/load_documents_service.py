from pathlib import Path

from app.dal.files.markdown_reader import read_markdown_documents
from app.domain.models.document_model import DocumentsBase


async def load_documents(root: Path | None = None) -> DocumentsBase:
    """Charge les documents Markdown disponibles dans le dossier configuré.

    Args:
        root: Dossier source explicite, ou dossier de wikis par défaut.

    Returns:
        Documents Markdown chargés depuis le dossier des wikis.
    """
    documents: DocumentsBase = await read_markdown_documents(root)
    return documents
