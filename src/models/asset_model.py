"""Operations of the 'assets' table in the database."""

from __future__ import annotations
import uuid

from .custom_base_model import CustomBaseModel
from .schemas import Asset
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from exceptions import AssetNotFoundError, DatabaseReadError, DatabaseWriteError


class AssetModel(CustomBaseModel):
    def __init__(self, db_client):
        super().__init__(db_client)
        self.collection = db_client
    
    async def insert_asset(self, asset: Asset) -> Asset:
        try:
            async with self.db_client() as session:
                async with session.begin():
                    session.add(asset)
                await session.refresh(asset)
        except IntegrityError as e:
            raise DatabaseWriteError(
                f"Asset '{asset.asset_name}' already exists",
                detail=str(e)
            ) from e
        except SQLAlchemyError as e:
            raise DatabaseWriteError(
                f"Failed to insert asset '{asset.asset_name}'",
                detail=str(e)
            ) from e
        return asset
    
    async def get_asset(self, asset_project_id: uuid.UUID, asset_name: str) -> Asset:
        try:
            async with self.db_client() as session:
                stmt = select(Asset).where(
                    Asset.asset_project_id == asset_project_id,
                    Asset.asset_name == asset_name
                )

                result = await session.execute(stmt)
                asset = result.scalar_one_or_none()

        except SQLAlchemyError as e:
            raise DatabaseReadError(
                f"Failed to query asset '{asset_name}'",
                detail=str(e)
            ) from e

        if asset is None:
            raise AssetNotFoundError(f"Asset '{asset_name}' not found")
        
        return asset

    async def get_project_assets(
        self, 
        asset_project_id: uuid.UUID, 
        asset_type: str | None = None
    ) -> list[Asset]:
    
        try:
            async with self.db_client() as session:
                stmt = select(Asset).where(
                    Asset.asset_project_id == asset_project_id
                )

                if asset_type is not None:
                    stmt = stmt.where(Asset.asset_type == asset_type)

                result = await session.execute(stmt)
                assets = result.scalars().all()

        except SQLAlchemyError as e:
            raise DatabaseReadError("Failed to fetch project assets", detail=str(e)) from e

        return list(assets)
