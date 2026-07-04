from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
import aiofiles
import logging

from helpers.config import get_settings, Settings
from controllers import DataController
from models import ResponseSignal

data_router = APIRouter(
    prefix='/api/v1/data',
    tags=['api_v1', 'data']
)

logger = logging.getLogger('uvicorn.error') # TODO: create a logger class 

@data_router.post('/upload/{project_id}')
async def upload_file(project_id: str, file: UploadFile,
                    settings: Settings = Depends(get_settings)):
                    data_controller = DataController()

                    is_valid, response_message = data_controller.validate_uploaded_file(file=file)
                    
                    if not is_valid:
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content=response_message
                        )

                    file_path, file_name = data_controller.generate_unique_filepath(
                        original_name=file.filename,
                        project_id=project_id
                    )

                    try:
                        async with aiofiles.open(file_path, 'wb') as f:
                            while chunk := await file.read(settings.FILE_CHUNK_SIZE):
                                await f.write(chunk)
                        
                    except Exception as e:
                        logger.error(f'Error while uploading files: {e}')

                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content=ResponseSignal.FILE_UPLOAD_FAIL.value
                        )
                        
                    return JSONResponse(
                        content={
                            'response' : ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                            'file_id' : file_name
                        }
                    )