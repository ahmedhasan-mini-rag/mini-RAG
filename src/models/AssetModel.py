"""Operations of the 'assets' collection in the database."""

from __future__ import annotations
from bson import ObjectId

from .CustomBaseModel import CustomBaseModel
from .enums import DataBaseEnums
from .schemas import Asset

class AssetModel(CustomBaseModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = db_client[DataBaseEnums.COLLECTION_ASSET_NAME.value]
    
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
    
    async def get_all_project_assets(self, asset_project_id: str) -> list:
        docs = await self.collection.find({
            "asset_project_id" : ObjectId(asset_project_id) if isinstance(asset_project_id, str) else asset_project_id
        }).to_list(length=None)

        return docs

