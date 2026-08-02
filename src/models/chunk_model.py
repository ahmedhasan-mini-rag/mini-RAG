"""Operations of the 'chunks' table in the database."""

from __future__ import annotations
import uuid
from collections.abc import AsyncGenerator

from .custom_base_model import CustomBaseModel
from .enums import DataBaseEnums
from .schemas import Chunk
from sqlalchemy import select, func, delete
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from exceptions import DatabaseReadError, DatabaseWriteError


class ChunkModel(CustomBaseModel):
    def __init__(self, db_client):
        super().__init__(db_client)
        self.collection = db_client

    async def insert_chunk(self, chunk: Chunk) -> Chunk:
        try:
            async with self.db_client() as session:
                async with session.begin():
                    session.add(chunk)
                await session.refresh(chunk)
        except SQLAlchemyError as e:
            raise DatabaseWriteError(
                f"Failed to insert chunk", detail=str(e)
            ) from e
        return chunk


    async def get_chunk(self, chunk_id: uuid.UUID) -> Chunk | None:
        try:
            async with self.db_client() as session:
                stmt = select(Chunk).where(Chunk.id == chunk_id)

                result = await session.execute(stmt)
                chunk = result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseReadError(
                f"Failed to query chunk '{chunk_id}'", detail=str(e)
            ) from e

        return chunk

    async def get_project_chunks(
        self, chunk_project_id: uuid.UUID
    ) -> AsyncGenerator[Chunk, None]:
        try:
            async with self.db_client() as session:
                stmt = select(Chunk).where(
                    Chunk.chunk_project_id == chunk_project_id
                )

                async for chunk in await session.stream_scalars(stmt):
                    yield chunk

        except SQLAlchemyError as e:
            raise DatabaseReadError(
                f"Failed to query chunks for project '{chunk_project_id}'",
                detail=str(e)
            ) from e

        
    async def insert_multiple_chunks(self, chunks: list[Chunk], batch_size: int = 100) -> int:
        try:
            async with self.db_client() as session:
                async with session.begin():
                    for i in range(0, len(chunks), batch_size):
                        session.add_all(chunks[i : i+batch_size])
        except SQLAlchemyError as e:
            raise DatabaseWriteError("Failed to insert chunks", detail=str(e)) from e

        return len(chunks)
    
    async def delete_multiple_chunks(self, chunk_project_id: uuid.UUID) -> int:
        try:
            async with self.db_client() as session:
                async with session.begin():
                    stmt = delete(Chunk).where(
                        Chunk.chunk_project_id == chunk_project_id
                    )
                    result = await session.execute(stmt)
        except SQLAlchemyError as e:
            raise DatabaseWriteError("Failed to delete chunks", detail=str(e)) from e

        return result.rowcount