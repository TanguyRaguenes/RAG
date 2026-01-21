from pydantic import BaseModel

from app.schemas.save_items_response_schema import SaveItemsResponseBase


class IngestBulkResponseBase(BaseModel):
    duration: str
    savedItems: SaveItemsResponseBase
