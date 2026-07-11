"""Operations of the 'chunks' collection in the database."""

from __future__ import annotations
from bson import ObjectId

from .CustomBaseModel import CustomBaseModel
from .enums import DataBaseEnums
from .schemas import DataChunk


class ChunkModel(CustomBaseModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = db_client[DataBaseEnums.COLLECTION_CHUNK_NAME.value]
    
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
        result = await self.collection.insert_one(
            chunk.model_dump(exclude_none=True)
            )
        
        chunk.id = result.inserted_id
        return chunk
    
    async def get_chunk(self, chunk_id: str) -> DataChunk | None:
        doc = await self.collection.find_one({
            '_id' :  ObjectId(chunk_id) if isinstance(chunk_id, str) else chunk_id
        })

        return None if doc is None else DataChunk(**doc)
    
    async def insert_multiple_chunks(self, chunks: list[DataChunk], batch_size: int = 100) -> int:
        total_inserted = 0

        for i in range(0, len(chunks), batch_size):

            batch_docs = [
                        chunk.model_dump(exclude_none=True) 
                        for chunk in chunks[i : i+batch_size]
            ]
        
            result = await self.collection.insert_many(batch_docs)
            total_inserted += len(result.inserted_ids)
        
        return total_inserted
    
    async def delete_multiple_chunks(self, db_project_id: ObjectId) -> int:
        result = await self.collection.delete_many({
            'chunk_project_id' : db_project_id
        })

        return result.deleted_count
        