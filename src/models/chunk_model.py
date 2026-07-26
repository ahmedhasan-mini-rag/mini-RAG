"""Operations of the 'chunks' collection in the database."""

from __future__ import annotations

from bson import ObjectId
from pymongo.errors import PyMongoError

from .custom_base_model import CustomBaseModel
from .enums import DataBaseEnums
from .schemas import DataChunk
from pymongo.cursor import Cursor
from exceptions import DatabaseReadError, DatabaseWriteError


class ChunkModel(CustomBaseModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = db_client[DataBaseEnums.COLLECTION_CHUNK_NAME]
    
    @classmethod
    async def create_instance(cls, db_client: object) -> ChunkModel:
        obj = cls(db_client=db_client)
        await obj.init_indexes()

        return obj

    async def init_indexes(self):
        indexes = DataChunk.get_indexes()
        
        for index in indexes:
            await self.collection.create_index(
                keys = index['keys'],
                name = index['name'],
                unique = index['unique']
            )

    async def insert_chunk(self, chunk: DataChunk) -> DataChunk:
        try:
            result = await self.collection.insert_one(
                chunk.model_dump(exclude_none=True)
                )
        except PyMongoError as e:
            raise DatabaseWriteError("Failed to insert chunk", detail=str(e)) from e
        
        chunk.id = result.inserted_id
        return chunk
    
    async def get_chunk(self, chunk_id: str | ObjectId) -> DataChunk | None:
        try:
            doc = await self.collection.find_one({
                '_id' : self.prepare_id(chunk_id)
            })
        except PyMongoError as e:
            raise DatabaseReadError(f"Failed to query chunk '{chunk_id}'", detail=str(e)) from e

        return None if doc is None else DataChunk(**doc)

    async def get_project_chunks(self, chunk_project_id: str | ObjectId) -> Cursor:
        try:
            return self.collection.find({
                "chunk_project_id" : self.prepare_id(chunk_project_id)
            })
        except PyMongoError as e:
            raise DatabaseReadError(
                f"Failed to query chunks for project '{chunk_project_id}'",
                detail=str(e)
            ) from e

    async def insert_multiple_chunks(self, chunks: list[DataChunk], batch_size: int = 100) -> int:
        total_inserted = 0

        for i in range(0, len(chunks), batch_size):

            batch_docs = [
                        chunk.model_dump(exclude_none=True) 
                        for chunk in chunks[i : i+batch_size]
            ]
        
            try:
                result = await self.collection.insert_many(batch_docs)
            except PyMongoError as e:
                raise DatabaseWriteError(
                    "Failed to insert chunks batch",
                    detail=str(e)
                ) from e

            total_inserted += len(result.inserted_ids)
        
        return total_inserted
    
    async def delete_multiple_chunks(self, chunk_project_id: str | ObjectId) -> int:
        try:
            result = await self.collection.delete_many({
                'chunk_project_id' : self.prepare_id(chunk_project_id)
            })
        except PyMongoError as e:
            raise DatabaseWriteError("Failed to delete chunks", detail=str(e)) from e

        return result.deleted_count