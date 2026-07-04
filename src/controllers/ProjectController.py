from pathlib import Path
from .BaseController import BaseController

class ProjectController(BaseController):
    def __init__(self):
        super().__init__()
    
    def get_project_path(self, project_id: str) -> Path:
        project_dir = self.files_dir / project_id

        if not project_dir.exists():
            project_dir.mkdir(parents=True, exist_ok=True)
        
        return project_dir