from pydantic import BaseModel
from controllers import ProjectController

class ProcessRequest(BaseModel):
    file_id: str
    chunk_size: int | None = 120
    overlap_size: int | None = 20
    do_reset: bool | None = False

    def check_file_exists(cls, project_id: str):
        project_path = ProjectController().get_project_path(project_id=project_id)
        
        file_path = project_path / cls.file_id
        return file_path.exists()