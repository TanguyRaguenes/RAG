from app.dal.repositories.vector_store_repository import (
    build_enriched_chunks,
    extract_related_links,
    filter_by_similarity,
)


def test_build_enriched_chunks_calculates_cosine_similarity() -> None:
    chunks = build_enriched_chunks(
        documents=["doc-a", "doc-b"],
        metadatas=[{"path": "a"}, {"path": "b"}],
        distances=[0.2, 0.8],
    )

    assert chunks == [
        {
            "document": "doc-a",
            "metadata": {"path": "a"},
            "distance": 0.2,
            "similarity": 0.8,
        },
        {
            "document": "doc-b",
            "metadata": {"path": "b"},
            "distance": 0.8,
            "similarity": 0.19999999999999996,
        },
    ]


def test_filter_by_similarity_keeps_best_chunks_sorted() -> None:
    chunks = [
        {"document": "low", "metadata": {}, "similarity": 0.2},
        {"document": "high", "metadata": {}, "similarity": 0.9},
        {"document": "mid", "metadata": {}, "similarity": 0.7},
    ]

    result = filter_by_similarity(chunks, minimum_similarity=0.5)

    assert [chunk["document"] for chunk in result] == ["high", "mid"]


def test_extract_related_links_keeps_highest_parent_score() -> None:
    chunks = [
        {
            "metadata": {
                "has_links": True,
                "related_links": "wiki/a.md, wiki/b.md",
            },
            "similarity": 0.6,
        },
        {
            "metadata": {
                "has_links": True,
                "related_links": "wiki/a.md",
            },
            "similarity": 0.9,
        },
        {
            "metadata": {
                "has_links": False,
                "related_links": "wiki/c.md",
            },
            "similarity": 1.0,
        },
    ]

    assert extract_related_links(chunks) == {
        "wiki/a.md": 0.9,
        "wiki/b.md": 0.6,
    }
from app.dal.repositories.vector_store_repository import (
    VectorStoreRepository,
    build_enriched_chunks,
    extract_related_links,
    filter_by_similarity,
)
from app.schemas.vector_db_items_schema import VectorStoreItemsBase


class FakeCollection:
    def __init__(self):
        self.upsert_calls = []
        self.delete_calls = []
        self.get_calls = []
        self.query_payload = {
            "documents": [["doc-a", "doc-b"]],
            "metadatas": [[
                {"path": "a.md", "title": "A", "chunk_index": 0, "has_links": True, "related_links": "b.md"},
                {"path": "b.md", "title": "B", "chunk_index": 0, "has_links": False, "related_links": ""},
            ]],
            "distances": [[0.1, 0.6]],
        }

    def upsert(self, **kwargs):
        self.upsert_calls.append(kwargs)

    def get(self, **kwargs):
        self.get_calls.append(kwargs)
        if kwargs.get("where"):
            return {"documents": ["related"], "metadatas": [{"path": "b.md", "title": "B"}]}
        if kwargs:
            return {"ids": ["id"], "documents": ["doc"], "metadatas": [{"path": "doc.md"}]}
        return {"ids": ["id"]}

    def delete(self, **kwargs):
        self.delete_calls.append(kwargs)

    def query(self, **kwargs):
        self.query_call = kwargs
        return self.query_payload


def _repository() -> VectorStoreRepository:
    repository = VectorStoreRepository.__new__(VectorStoreRepository)
    repository.config = {}
    return repository


def test_insert_or_update_items_in_collection_upserts_all_fields() -> None:
    collection = FakeCollection()
    items = VectorStoreItemsBase(ids=["id"], documents=["doc"], embeddings=[[0.1]], metadatas=[{"path": "doc.md"}])

    _repository().insert_or_update_items_in_collection(collection, items)

    assert collection.upsert_calls == [
        {"ids": ["id"], "documents": ["doc"], "embeddings": [[0.1]], "metadatas": [{"path": "doc.md"}]}
    ]


def test_get_collection_items_maps_chroma_payload_to_saved_items() -> None:
    items = _repository().get_collection_items(FakeCollection(), ["id"], ["documents", "metadatas"])

    assert items[0].id == "id"
    assert items[0].chunk == "doc"
    assert items[0].metadatas == {"path": "doc.md"}


def test_delete_items_by_ids_ignores_empty_list_and_deletes_non_empty_list() -> None:
    collection = FakeCollection()
    repository = _repository()

    repository.delete_items_by_ids(collection, [])
    repository.delete_items_by_ids(collection, ["id"])

    assert collection.delete_calls == [{"ids": ["id"]}]


def test_delete_all_items_deletes_existing_ids() -> None:
    collection = FakeCollection()

    _repository().delete_all_items(collection)

    assert collection.delete_calls == [{"ids": ["id"]}]


def test_retrieve_chunks_filtered_filters_falls_back_and_adds_related_chunks() -> None:
    collection = FakeCollection()

    result = _repository().retrieve_chunks_filtered(
        collection,
        query_embedding=[0.1],
        top_k=2,
        minimum_similarity=0.95,
        minimum_number_of_chunks=1,
        max_related_links=1,
    )

    assert result[0]["document"] == "doc-a"
    assert result[0]["similarity"] == 0.9
    assert result[1]["document"].startswith("CONTEXTE : DOCUMENT LIÉ")
    assert collection.query_call["include"] == ["documents", "metadatas", "distances"]


def test_build_enriched_chunks_and_filter_by_similarity_sort_results() -> None:
    chunks = build_enriched_chunks(
        ["low", "high"],
        [{"path": "low"}, {"path": "high"}],
        [0.7, 0.1],
    )

    result = filter_by_similarity(chunks, 0.5)

    assert [chunk["document"] for chunk in result] == ["high"]
    assert result[0]["similarity"] == 0.9


def test_extract_related_links_keeps_best_score_and_ignores_empty_links() -> None:
    result = extract_related_links(
        [
            {"metadata": {"has_links": True, "related_links": " a.md, "}, "similarity": 0.6},
            {"metadata": {"has_links": True, "related_links": "a.md,b.md"}, "similarity": 0.9},
            {"metadata": {"has_links": False, "related_links": "c.md"}, "similarity": 1.0},
        ]
    )

    assert result == {"a.md": 0.9, "b.md": 0.9}
