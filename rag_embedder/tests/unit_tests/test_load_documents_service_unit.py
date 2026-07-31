import pytest

from app.domain.models.document_model import DocumentBase, DocumentsBase
from app.services import load_documents_service


@pytest.mark.asyncio
async def test_load_documents_returns_markdown_reader_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = DocumentsBase(documents=[DocumentBase(path="doc.md", content="content")])

    async def fake_read_markdown_documents() -> DocumentsBase:
        return expected

    monkeypatch.setattr(
        load_documents_service, "read_markdown_documents", fake_read_markdown_documents
    )

    assert await load_documents_service.load_documents() is expected
