from app.schemas.save_items_response_schema import SavedItemBase
from app.schemas.vector_db_items_schema import VectorStoreItemsBase
from app.services.saving_service import save_items


class FakeCollection:
    def __init__(self):
        self.count_calls = 0

    def count(self) -> int:
        self.count_calls += 1
        return 1 if self.count_calls == 1 else 2


class FakeVectorStoreRepository:
    def __init__(self):
        self.collection = FakeCollection()
        self.inserted_items = None

    def get_or_create_collection(self, collection_name: str) -> FakeCollection:
        assert collection_name == "wiki_chunks"
        return self.collection

    def insert_or_update_items_in_collection(
        self,
        collection: FakeCollection,
        items: VectorStoreItemsBase,
    ) -> None:
        self.inserted_items = items

    def get_collection_items(
        self,
        collection: FakeCollection,
        ids: list[str],
        columns: list[str],
    ) -> list[SavedItemBase]:
        assert ids == ["id-1"]
        assert columns == ["documents", "metadatas"]
        return [SavedItemBase(id="id-1", chunk="chunk", metadatas={"title": "Doc"})]


def test_save_items_upserts_and_returns_saved_items() -> None:
    repository = FakeVectorStoreRepository()
    items = VectorStoreItemsBase(
        ids=["id-1"],
        documents=["chunk"],
        embeddings=[[0.1, 0.2]],
        metadatas=[{"title": "Doc"}],
    )

    response = save_items(items, repository)

    assert repository.inserted_items == items
    assert response.collection_count_before == 1
    assert response.collection_count_after == 2
    assert response.saved_items[0].id == "id-1"
