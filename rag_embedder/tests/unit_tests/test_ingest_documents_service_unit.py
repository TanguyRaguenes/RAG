import pytest
from app.core.exceptions import MarkdownProcessingException
from app.domain.models.document_model import DocumentBase, DocumentsBase
from app.schemas.document_to_ingest_schema import (
    ChunkToIngest,
    DocumentsToIngest,
    DocumentToIngest,
)
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.schemas.vector_store_items_schema import (
    VectorMetadataBase,
    VectorStoreItemsBase,
)
from app.services import ingest_documents_service as service


def test_clean_title_decodes_path_name_and_normalizes_separators() -> None:
    assert service.clean_title("Guide%20API_interne-v2.md") == "Guide API interne v2"


def test_convert_to_chroma_format_flattens_all_document_chunks() -> None:
    documents = DocumentsToIngest(
        documents=[
            DocumentToIngest(
                chunks=[
                    ChunkToIngest(
                        id="doc-1#chunk_0",
                        chunk="contenu 1",
                        embeded_text=[0.1, 0.2],
                        metadatas=VectorMetadataBase(
                            path="doc-1.md", title="Doc 1", chunk_index=0
                        ),
                    )
                ]
            ),
            DocumentToIngest(
                chunks=[
                    ChunkToIngest(
                        id="doc-2#chunk_0",
                        chunk="contenu 2",
                        embeded_text=[0.3, 0.4],
                        metadatas=VectorMetadataBase(
                            path="doc-2.md", title="Doc 2", chunk_index=0
                        ),
                    )
                ]
            ),
        ]
    )

    result = service.convert_to_chroma_format(documents)

    assert result.ids == ["doc-1#chunk_0", "doc-2#chunk_0"]
    assert result.documents == ["contenu 1", "contenu 2"]
    assert result.embeddings == [[0.1, 0.2], [0.3, 0.4]]
    assert [metadata.path for metadata in result.metadatas] == [
        "doc-1.md",
        "doc-2.md",
    ]


@pytest.mark.asyncio
async def test_prepare_document_to_ingest_embeds_chunks_with_document_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_texts: list[str] = []

    def fake_chunk_text(content: str, config: dict) -> list[str]:
        assert content == "source"
        assert config == {"chunking": {}}
        return ["Premier chunk avec [lien](./Autre-page)", "Second chunk"]

    async def fake_embed(
        texts: list[str], config: dict, is_query: bool
    ) -> list[list[float]]:
        captured_texts.extend(texts)
        assert not is_query
        return [[float(index)] for index, _ in enumerate(texts, start=1)]

    monkeypatch.setattr(service, "chunk_text", fake_chunk_text)
    monkeypatch.setattr(service, "client_embed", fake_embed)

    result = await service.prepare_document_to_ingest(
        DocumentBase(path="docs/Guide%20API.md", content="source"),
        {"chunking": {}},
    )

    assert [chunk.id for chunk in result.chunks] == [
        "Guide API#chunk_0#docs/Guide%20API.md",
        "Guide API#chunk_1#docs/Guide%20API.md",
    ]
    assert result.chunks[0].metadatas.model_dump() == {
        "path": "docs/Guide%20API.md",
        "title": "Guide API",
        "chunk_index": 0,
        "related_links": "docs/Autre-page.md",
        "has_links": True,
    }
    assert result.chunks[1].metadatas.has_links is False
    assert result.chunks[0].embeded_text == [1.0]
    assert result.chunks[1].embeded_text == [2.0]
    assert captured_texts[0].startswith("TITLE=Guide API | PATH=docs/Guide%20API.md")
    assert len(captured_texts) == 2


@pytest.mark.asyncio
async def test_ingest_documents_saves_vector_store_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved_payloads: list[VectorStoreItemsBase] = []

    async def fake_prepare_document_to_ingest(
        document: DocumentBase,
        config: dict,
    ) -> DocumentToIngest:
        return DocumentToIngest(
            chunks=[
                ChunkToIngest(
                    id=f"{document.path}#chunk_0",
                    chunk=document.content,
                    embeded_text=[1.0],
                    metadatas=VectorMetadataBase(
                        path=document.path,
                        title=document.path,
                        chunk_index=0,
                    ),
                )
            ]
        )

    async def fake_save_items(
        vector_store_items: VectorStoreItemsBase,
    ) -> SaveItemsResponseBase:
        saved_payloads.append(vector_store_items)
        return SaveItemsResponseBase(
            collection_count_before=0,
            collection_count_after=len(vector_store_items.ids),
            saved_items=[
                {
                    "id": item_id,
                    "chunk": chunk,
                    "metadatas": metadata.model_dump(),
                }
                for item_id, chunk, metadata in zip(
                    vector_store_items.ids,
                    vector_store_items.documents,
                    vector_store_items.metadatas,
                )
            ],
        )

    monkeypatch.setattr(
        service, "prepare_document_to_ingest", fake_prepare_document_to_ingest
    )
    monkeypatch.setattr(service, "client_save_items", fake_save_items)

    response = await service.ingest_documents(
        DocumentsBase(
            documents=[
                DocumentBase(path="a.md", content="A"),
                DocumentBase(path="b.md", content="B"),
            ]
        ),
        {},
    )

    assert len(response.saved_items) == 2
    assert saved_payloads[0].ids == ["a.md#chunk_0", "b.md#chunk_0"]
    assert saved_payloads[0].delete_obsolete is True


@pytest.mark.asyncio
async def test_ingest_documents_rejects_documents_without_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save_called = False

    async def fake_prepare_document_to_ingest(
        document: DocumentBase,
        config: dict,
    ) -> DocumentToIngest:
        return DocumentToIngest(chunks=[])

    async def fake_save_items(vector_store_items: VectorStoreItemsBase) -> None:
        nonlocal save_called
        save_called = True

    monkeypatch.setattr(
        service, "prepare_document_to_ingest", fake_prepare_document_to_ingest
    )
    monkeypatch.setattr(service, "client_save_items", fake_save_items)

    with pytest.raises(MarkdownProcessingException) as exc_info:
        await service.ingest_documents(
            DocumentsBase(documents=[DocumentBase(path="empty.md", content="")]),
            {},
        )

    assert exc_info.value.internal_details == {
        "operation": "ingest_documents",
        "reason": "no_chunk",
        "document_count": 1,
    }
    assert save_called is False


@pytest.mark.parametrize(
    ("link", "source_path", "expected"),
    [
        ("./Autre%20page", "docs/guide.md", "docs/Autre page.md"),
        ("../index.md#section", "docs/api/guide.md", "docs/index.md"),
        ("/accueil", "docs/guide.md", "accueil.md"),
        ("https://example.com/page", "docs/guide.md", None),
        ("#section", "docs/guide.md", None),
        ("./image.png", "docs/guide.md", None),
    ],
)
def test_normalize_markdown_link_resolves_only_internal_markdown_targets(
    link: str,
    source_path: str,
    expected: str | None,
) -> None:
    assert service.normalize_markdown_link(link, source_path) == expected
