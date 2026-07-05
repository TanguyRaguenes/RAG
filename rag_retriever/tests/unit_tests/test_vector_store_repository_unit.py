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
