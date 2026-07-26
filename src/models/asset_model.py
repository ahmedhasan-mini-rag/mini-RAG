"""Operations of the 'assets' collection in the database."""

from __future__ import annotations

from bson import ObjectId
from pymongo.errors import PyMongoError

from .custom_base_model import CustomBaseModel
from .enums import DataBaseEnums
from .schemas import Asset
from exceptions import AssetNotFoundError, DatabaseReadError, DatabaseWriteError


class AssetModel(CustomBaseModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = db_client[DataBaseEnums.COLLECTION_ASSET_NAME]
    
    @classmethod
    async def create_instance(cls ,db_client: object) -> AssetModel:
        obj = cls(db_client=db_client) 
        await obj.init_indexes()

        return obj

    async def init_indexes(self) -> None:
        indexes = Asset.get_indexes()

        for index in indexes:
            await self.collection.create_index(
                keys = index['keys'],
                name = index['name'],
                unique = index['unique']
            )
    
    async def insert_asset(self, asset: Asset) -> Asset:
        try:
            result = await self.collection.insert_one(
                asset.model_dump(exclude_none=True)
            )
        except PyMongoError as e:
            raise DatabaseWriteError(
                f"Failed to insert asset '{asset.asset_name}'",
                detail=str(e)
            ) from e

        asset.id = result.inserted_id

        return asset
    
    async def get_asset(self, asset_project_id: str | ObjectId, asset_name: str) -> Asset:
        try:
            doc = await self.collection.find_one(
                {
                    'asset_project_id' : self.prepare_id(asset_project_id),
                    'asset_name' : asset_name
                }
            )
        except PyMongoError as e:
            raise DatabaseReadError(
                f"Failed to query asset '{asset_name}'",
                detail=str(e)
            ) from e

        if doc is None:
            raise AssetNotFoundError(f"Asset '{asset_name}' not found")

        return Asset(**doc)

    async def get_project_assets(
        self, 
        asset_project_id: str | ObjectId, 
        asset_type: str | None = None
    ) -> list[Asset]:
    
        query = {
            "asset_project_id": self.prepare_id(asset_project_id)
        }

        if asset_type is not None:
            query["asset_type"] = asset_type

        try:
            docs = await self.collection.find(query).to_list(length=None)
        except PyMongoError as e:
            raise DatabaseReadError("Failed to fetch project assets", detail=str(e)) from e
        
        return [Asset(**doc) for doc in docs]
