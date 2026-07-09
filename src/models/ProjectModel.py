"""Operations of the 'projects' collection in the database."""

from .CustomBaseModel import CustomBaseModel
from .enums import DataBaseEnums
from .schemas import Project


class ProjectModel(CustomBaseModel):
    def __init__(self, db_client):
        super().__init__(db_client)

        self.collection = db_client[DataBaseEnums.COLLECTION_PROJECT_NAME.value]
    
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

        if doc is None and create_on_absence:
            project = Project(project_id=project_id)
            project = await self.insert_project(project=project)

            return project

        return Project(**doc)

    async def get_all_projects(self, page: int = 1, page_size: int = 12) -> tuple[list[Project], int]:
        total_docs = await self.collection.count_documents({})

        total_pages = (total_docs // page_size) + (total_docs % page_size > 0)

        cursor = self.collection.find().skip((page - 1) * page_size).limit(page_size)

        projects = [Project(**doc) async for doc in cursor]
        
        return projects, total_pages