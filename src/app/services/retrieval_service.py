from typing import Any

def retrieve_chunks(collection, query_embedding: list[float], top_k: int) -> list[dict[str, Any]]:

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "ids"],
    )

    chunks: list[dict[str, Any]] = []
    ids = result["ids"][0]
    docs = result["documents"][0]
    metas = result["metadatas"][0]

    for chunk_id, doc, meta in zip(ids, docs, metas):
        chunks.append({
            "id": chunk_id,
            "document": doc,
            "metadata": meta,
        })

    return chunks