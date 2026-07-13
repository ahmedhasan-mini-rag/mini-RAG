from pydantic import BaseModel, Field
from controllers import ProjectController

class ProcessRequest(BaseModel):
    asset_name: str | None = None
    chunk_size: int | None = Field(default=120, gt=10)
    overlap_size: int | None = Field(default=20, ge=0)
    do_reset: bool | None = False