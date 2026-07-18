"""Operations of the 'assets' collection in the database."""

from __future__ import annotations
from bson import ObjectId

from .CustomBaseModel import CustomBaseModel
from .enums import DataBaseEnums
from .schemas import Asset

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
        result = await self.collection.insert_one(
            asset.model_dump(exclude_none=True)
        )
        asset.id = result.inserted_id

        return asset
    
    async def get_asset(self, asset_project_id: str | ObjectId, asset_name: str) -> Asset:
        query = {
            "asset_project_id":(
                ObjectId(asset_project_id)
                if isinstance(asset_project_id, str)
                else asset_project_id
            ),
            'asset_name' : asset_name
        }
        doc = await self.collection.find_one(query)

        return Asset(**doc) if doc is not None else None

    async def get_all_project_assets(
        self, 
        asset_project_id: str | ObjectId, 
        asset_type: str | None = None
    ) -> list[Asset]:
    
        query = {
            "asset_project_id":(
                ObjectId(asset_project_id)
                if isinstance(asset_project_id, str)
                else asset_project_id
            )
        }

        if asset_type is not None:
            query["asset_type"] = asset_type

        docs = await self.collection.find(query).to_list(length=None)
        
        return [Asset(**doc) for doc in docs]
