import re
from pydantic import BaseModel, ConfigDict, Field, field_validator
from bson import ObjectId 
from datetime import datetime, UTC

class Project(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    id: ObjectId | None = Field(default=None, alias='_id')
    project_name: str = Field(min_length=1)

    @field_validator('project_name')
    def validate_project_name(cls, value):
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise ValueError('<project_name> must contain only alphanumeric characters, underscores, or dashes')
        return value

    @staticmethod
    def get_indexes():
        return [
            {
                'keys' : [('project_name', 1)],
                'name' : 'project_name_index',
                'unique' : True
            }
        ]

class DataChunk(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    id: ObjectId | None = Field(default=None, alias='_id') # hash id of the chunk document
    chunk_text: str
    chunk_metadata: dict
    chunk_order: int = Field(gt=0)
    chunk_project_id: ObjectId
    chunk_asset_id: ObjectId

    @staticmethod
    def get_indexes():
        return [
            {
                'keys' : [('chunk_project_id', 1)],
                'name' : 'chunk_project_id_index',
                'unique' : False
            }
        ]

class Asset(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    id: ObjectId | None = Field(default=None, alias='_id') 
    asset_project_id: ObjectId
    asset_type: str = Field(min_length=1)
    asset_name: str = Field(min_length=1)
    asset_size: int | None = Field(ge=0, default=None)
    asset_config: dict = Field(default={})
    asset_created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def get_indexes():
        return [
            {
                "keys": [
                    ("asset_project_id", 1),
                    ("asset_name", 1)
                ],
                "name": "asset_project_id_name_index",
                "unique": True
            },
            {
                "keys": [
                    ("asset_project_id", 1),
                    ("asset_type", 1)
                ],
                "name": "asset_project_id_type_index",
                "unique": False
            }
        ]