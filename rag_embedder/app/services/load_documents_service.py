from app.domain.models.document_model import DocumentsBase
from app.dal.files.markdown_reader import read_markdown_documents

async def load_documents() -> DocumentsBase:
    documents:DocumentsBase = await read_markdown_documents()
    return documents