from fastapi import UploadFile
import re

from .BaseController import BaseController
from .ProjectController import ProjectController
from models import ResponseSignal

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.file_size_scaler = 1024 * 1024

    def validate_uploaded_file(self, file: UploadFile):
        
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
            
        if file.size > self.app_settings.FILE_MAX_SIZE * self.file_size_scaler:
            return False, ResponseSignal.FILE_SIZE_EXCEEDED.value

        return True, ResponseSignal.FILE_VALIDATION_SUCCESS.value
    
    def generate_unique_filepath(self, original_name: str, project_id: str):
        random_string = self.generate_random_string()
        project_path = ProjectController().get_project_path(project_id=project_id)

        cleaned_file_name = self.clean_file_name(original_name)

        file_path = project_path / '_'.join((random_string, cleaned_file_name)) 

        while file_path.exists():
            self.generate_unique_filename(cleaned_file_name, project_id)
        
        return file_path, file_path.name

    def clean_file_name(self, file_name: str) -> str:
        cleaned_file_name = re.sub(r'[^\w.]', '', file_name.strip())
        cleaned_file_name = cleaned_file_name.replace(' ', '_')

        return cleaned_file_name