"""Operations of the 'projects' collection in the database."""

from __future__ import annotations

from .CustomBaseModel import CustomBaseModel
from .enums import DataBaseEnums
from .schemas import Project

class ProjectModel(CustomBaseModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = db_client[DataBaseEnums.COLLECTION_PROJECT_NAME]
    
    @classmethod
    async def create_instance(cls ,db_client: object) -> ProjectModel:
        obj = cls(db_client=db_client) 
        await obj.init_indexes()

        return obj

    async def init_indexes(self) -> None:
        indexes = Project.get_indexes()

        for index in indexes:
            await self.collection.create_index(
                keys = index['keys'],
                name = index['name'],
                unique = index['unique']
            )

    async def insert_project(self, project: Project) -> Project:
        result = await self.collection.insert_one(
            project.model_dump(exclude_none=True)
        )
        project.id = result.inserted_id

        return project
    
    async def get_project(self, project_id: str, create_if_missing: bool) -> Project | None:
        doc = await self.collection.find_one({
            'project_id' : project_id
        })

        if doc is not None:
            return Project(**doc)
        
        if create_if_missing:
            project = Project(project_id=project_id)
            project = await self.insert_project(project=project)
            return project
        
        return None


    async def get_all_projects(self, page: int = 1, page_size: int = 12) -> tuple[list[Project], int]:
        total_docs = await self.collection.count_documents({})

        total_pages = (total_docs // page_size) + (total_docs % page_size > 0)

        cursor = self.collection.find().skip((page - 1) * page_size).limit(page_size)

        projects = [Project(**doc) async for doc in cursor]
        
        return projects, total_pages