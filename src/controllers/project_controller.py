import logging
from pathlib import Path
from .base_controller import BaseController

logger = logging.getLogger(__name__)

class ProjectController(BaseController):
    def __init__(self):
        super().__init__()
    
    def get_project_path(self, project_name: str, 
                        create_if_missing: bool = False) -> Path:
        project_dir = self.files_dir / project_name

        if create_if_missing and not project_dir.exists():
            project_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f'Project directory "{project_name}" created')
        
        return project_dir