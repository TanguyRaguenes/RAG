from app.domain.models.document_model import DocumentsBase
from app.dal.files.markdown_reader import read_markdown_documents


async def load_documents() -> DocumentsBase:
    """Charge les documents Markdown disponibles dans le dossier configuré.

    Returns:
        Documents Markdown chargés depuis le dossier des wikis.
    """
    documents: DocumentsBase = await read_markdown_documents()
    return documents
