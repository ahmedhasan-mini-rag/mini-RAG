from pydantic import BaseModel, Field

class ProcessRequest(BaseModel):
    asset_name: str | None = None
    chunk_size: int | None = Field(default=120, gt=10)
    overlap_size: int | None = Field(default=20, ge=0)
    do_reset: bool | None = False # clear all chunks of a specific project in the mongo db

class EmbedRequest(BaseModel):
    do_reset: bool = False # clear the collection of a specific project in the vector db

class SearchRequest(BaseModel):
    text: str
    top_k: int = 4
    response_language: str = "auto"

class RetrievedDocument(BaseModel):
    text: str
    score: float
    table_md: str | None 
    img_url: str | None 
