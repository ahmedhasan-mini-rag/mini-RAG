from fastapi import UploadFile
import aiofiles
import re
import os
import logging
from pathlib import Path

from .base_controller import BaseController
from .project_controller import ProjectController
from models.enums import ResponseSignal, AssetTypeEnums
from models.schemas import Project, Asset
from models import AssetModel
from exceptions import (
    FileValidationError, FileIOError as AppFileIOError,
    DatabaseWriteError,
)

logger = logging.getLogger(__name__)

class DataController(BaseController):
    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.file_size_scaler = 1024 * 1024

    def validate_uploaded_file(self, file: UploadFile) -> None:
        """Validate file type and size. Raises FileValidationError on failure."""
        
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            raise FileValidationError(ResponseSignal.FILE_TYPE_NOT_SUPPORTED)
            
        if file.size > self.app_settings.FILE_MAX_SIZE * self.file_size_scaler:
            raise FileValidationError(ResponseSignal.FILE_SIZE_EXCEEDED)
    
    def generate_unique_filepath(self, original_name: str, project_name: str) -> tuple[Path, str]:
        random_string = self.generate_random_string()
        project_path = ProjectController().get_project_path(
            project_name=project_name, create_if_missing=True
            )

        cleaned_file_name = self.clean_file_name(original_name)

        file_path = project_path / '_'.join((random_string, cleaned_file_name)) 

        while file_path.exists():
            self.generate_unique_filepath(cleaned_file_name, project_name)
        
        return file_path, file_path.name

    def clean_file_name(self, file_name: str) -> str:
        cleaned_file_name = re.sub(r'[^\w.]', '', file_name.strip())
        cleaned_file_name = cleaned_file_name.replace(' ', '_')

        return cleaned_file_name
    
    async def process_tasks(
        self, 
        files: list[UploadFile], 
        asset_model: AssetModel, 
    ) -> tuple[list[str], list[dict]]:

        successful_uploads = []
        failed_uploads = []

        for file in files:
            
            try:
                self.validate_uploaded_file(file=file)
            except FileValidationError as e:
                failed_uploads.append({
                    'filename': file.filename,
                    'reason': e.message
                })
                continue 
            
            file_path, file_name = self.generate_unique_filepath(
                original_name=file.filename,
                project_name=self.project.name
            )

            try:
                async with aiofiles.open(file_path, 'wb') as f:
                    while chunk := await file.read(self.app_settings.FILE_CHUNK_SIZE):
                        await f.write(chunk)
            
            except OSError as e:
                logger.error(f'Error while uploading file {file.filename}: {e}')
                failed_uploads.append({
                    'filename': file.filename,
                    'reason': ResponseSignal.FILE_UPLOAD_FAIL
                })
                continue
            
            # create the file asset in the database
            asset = Asset(
                asset_project_id=self.project.id,
                asset_type=AssetTypeEnums.FILE,
                asset_name=file_name,
                asset_size=os.path.getsize(file_path),
            )

            try:
                await asset_model.insert_asset(asset=asset)
            except DatabaseWriteError as e:
                logger.error(
                    f"Failed to save asset record for '{file.filename}': {e.message}"
                )

                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up orphan file '{file_name}' from disk.")
                except OSError as cleanup_err:
                    logger.error(
                        f"Failed to clean up orphan file. "
                        f"Manual removal required at: {file_path} — {cleanup_err}"
                    )

                failed_uploads.append({
                    'filename': file.filename,
                    'reason': ResponseSignal.FILE_UPLOAD_FAIL
                })
                continue
            
            logger.info(f"Successfully uploaded '{file.filename}' as '{file_name}'")
            successful_uploads.append(file_name)
        
        return successful_uploads, failed_uploads