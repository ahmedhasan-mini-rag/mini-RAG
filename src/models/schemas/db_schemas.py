from pydantic import BaseModel, ConfigDict, Field, field_validator
from bson import ObjectId 


class Project(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    id: ObjectId | None = Field(default=None, alias='_id')
    project_id: str = Field(min_length=1)

    @field_validator('project_id')
    def validate_project_id(cls, value):
        if not value.isalnum():
            raise ValueError('<project_id> must be alphanumeric value.')
        return value

class DataChunk(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    id: ObjectId | None = Field(default=None, alias='_id') # hash id of the chunk document
    chunk_text: str
    chunk_metadata: dict
    chunk_order: int = Field(gt=0)
    chunk_project_id: ObjectId