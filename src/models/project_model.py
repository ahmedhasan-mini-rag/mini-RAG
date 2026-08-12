"""Operations of the 'projects' table in the database."""

from __future__ import annotations
import re

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import select, exists, delete
from sqlalchemy.ext.asyncio import async_sessionmaker
from collections.abc import AsyncGenerator

from .custom_base_model import CustomBaseModel
from .schemas import Project
from exceptions import ProjectNotFoundError, DatabaseReadError, DatabaseWriteError


class ProjectModel(CustomBaseModel):
    def __init__(self, db_client: async_sessionmaker):
        super().__init__(db_client)
        self.db_client = db_client
    
    async def insert_project(self, project: Project) -> Project:
        self.validate_project_name(project.name)

        try:
            async with self.db_client() as session:
                async with session.begin():
                    session.add(project)
                await session.refresh(project)
        except IntegrityError as e:
            raise DatabaseWriteError(
                f"Project '{project.name}' already exists",
                detail=str(e)
            ) from e
        except SQLAlchemyError as e:
            raise DatabaseWriteError(
                f"Failed to insert project '{project.name}'",
                detail=str(e)
            ) from e
        return project
    
    async def get_project(self, project_name: str, create_if_missing: bool = False) -> Project:
        self.validate_project_name(project_name)

        try:
            async with self.db_client() as session:
                async with session.begin():
                    stmt = select(Project).where(Project.name == project_name)
                    result = await session.execute(stmt)
                    project = result.scalar_one_or_none()

                    if not project:
                        if create_if_missing :
                            project = Project(name=project_name)
                            session.add(project)
                        
                        else:
                            raise ProjectNotFoundError(f"Project '{project_name}' not found")

                await session.refresh(project)
                return project
        except SQLAlchemyError as e:
                    raise DatabaseReadError(
                        f"Failed to query project '{project_name}'",
                        detail=str(e)
                    ) from e


    async def get_all_projects(self, batch_size: int = 12) -> AsyncGenerator[tuple[Project]]:
        try:
            async with self.db_client() as session:
                stream = await session.stream_scalars(select(Project))
                async for batch in stream.partitions(batch_size):
                    yield batch
        except SQLAlchemyError as e:
            raise DatabaseReadError("Failed to fetch projects", detail=str(e)) from e

    async def delete_project(self, project_name: str) -> bool:
        try:
            async with self.db_client() as session:
                async with session.begin():
                    stmt = delete(Project).where(
                        Project.name == project_name
                    )
                    result = await session.execute(stmt)
        except SQLAlchemyError as e:
            raise DatabaseWriteError(
                f"Failed to delete project '{project_name}'", detail=str(e)
            ) from e

        return True if result.rowcount == 1 else False

    async def project_exists(self, project_name: str) -> bool:
        try:
            async with self.db_client() as session:
                stmt = select(exists().where(Project.name == project_name))
                result = await session.execute(stmt)
                return bool(result.scalar_one_or_none())
        except SQLAlchemyError as e:
            raise DatabaseReadError(
                f"Failed to check if project '{project_name}' exists",
                detail=str(e)
            ) from e

    @classmethod
    def validate_project_name(cls, project_name: str) -> None:
        if not project_name or not project_name.strip():
            raise ValueError("Project name cannot be empty")
        
        if not re.match(r'^[a-zA-Z0-9_]+$', project_name):
            raise ValueError("Project name can only contain alphanumeric characters and underscores")