from pydantic import BaseModel


class IngestBulkResponseBase(BaseModel):
    started_at: str
    finished_at: str
    duration: str
    collection_count_before: int
    collection_count_after: int
