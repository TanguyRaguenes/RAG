import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pytest

from app.domain.models.vector_store_model import StoredVectorItem, VectorMetadata
from app.schemas.vector_db_items_schema import VectorStoreItemsBase
from app.services.saving_service import save_items


class FakeVectorStoreRepository:
    def __init__(self) -> None:
        self.ids = {"old-id", "kept-id"}
        self.calls: list[tuple[str, object]] = []
        self.fail_upsert = False

    def count_items(self, collection_name: str) -> int:
        self.calls.append(("count", collection_name))
        return len(self.ids)

    def list_item_ids(self, collection_name: str) -> list[str]:
        self.calls.append(("list", collection_name))
        return list(self.ids)

    def upsert_items(self, collection_name: str, items: object) -> None:
        self.calls.append(("upsert", collection_name))
        if self.fail_upsert:
            raise RuntimeError("write failed")
        self.ids.update(items.ids)

    def delete_items(self, collection_name: str, ids: list[str]) -> None:
        self.calls.append(("delete", ids))
        self.ids.difference_update(ids)

    def get_items(self, collection_name: str, ids: list[str]) -> list[StoredVectorItem]:
        self.calls.append(("get", ids))
        return [
            StoredVectorItem(
                id=item_id,
                document="chunk",
                metadata=VectorMetadata(
                    path="doc.md",
                    title="Doc",
                    chunk_index=0,
                ),
            )
            for item_id in ids
        ]


def _items(*, delete_obsolete: bool, item_id: str = "kept-id") -> VectorStoreItemsBase:
    return VectorStoreItemsBase(
        ids=[item_id],
        documents=["chunk"],
        embeddings=[[0.1, 0.2]],
        metadatas=[{"path": "doc.md", "title": "Doc", "chunk_index": 0}],
        delete_obsolete=delete_obsolete,
    )


def test_save_items_uses_configured_collection_and_deletes_stale_ids() -> None:
    repository = FakeVectorStoreRepository()

    response = save_items(
        _items(delete_obsolete=True),
        {"collection": {"name": "configured-wiki"}},
        repository,
    )

    assert ("upsert", "configured-wiki") in repository.calls
    assert ("delete", ["old-id"]) in repository.calls
    assert repository.ids == {"kept-id"}
    assert response.collection_count_before == 2
    assert response.collection_count_after == 1
    assert response.saved_items[0].metadatas.path == "doc.md"


def test_save_items_does_not_delete_stale_ids_in_upsert_mode() -> None:
    repository = FakeVectorStoreRepository()

    save_items(
        _items(delete_obsolete=False),
        {"collection": {"name": "wiki"}},
        repository,
    )

    assert not any(call[0] == "delete" for call in repository.calls)
    assert repository.ids == {"old-id", "kept-id"}


def test_delete_obsolete_snapshots_are_serialized_in_process() -> None:
    class SlowVectorStoreRepository(FakeVectorStoreRepository):
        def __init__(self) -> None:
            super().__init__()
            self.active_counts = 0
            self.maximum_active_counts = 0
            self.tracker_lock = Lock()

        def count_items(self, collection_name: str) -> int:
            with self.tracker_lock:
                self.active_counts += 1
                self.maximum_active_counts = max(
                    self.maximum_active_counts, self.active_counts
                )
            try:
                time.sleep(0.02)
                return super().count_items(collection_name)
            finally:
                with self.tracker_lock:
                    self.active_counts -= 1

    repository = SlowVectorStoreRepository()
    config = {"collection": {"name": "wiki"}}

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                save_items,
                _items(delete_obsolete=True, item_id=item_id),
                config,
                repository,
            )
            for item_id in ("snapshot-a", "snapshot-b")
        ]
        for future in futures:
            future.result()

    assert repository.maximum_active_counts == 1
    assert repository.ids in ({"snapshot-a"}, {"snapshot-b"})


def test_save_items_never_deletes_old_items_when_upsert_fails() -> None:
    repository = FakeVectorStoreRepository()
    repository.fail_upsert = True

    with pytest.raises(RuntimeError, match="write failed"):
        save_items(
            _items(delete_obsolete=True),
            {"collection": {"name": "wiki"}},
            repository,
        )

    assert not any(call[0] == "delete" for call in repository.calls)
    assert repository.ids == {"old-id", "kept-id"}
