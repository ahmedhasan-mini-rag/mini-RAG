from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
import aiofiles
import logging

from helpers.config import get_settings, Settings
from controllers import DataController, ProcessController
from models import ResponseSignal
from schemes import ProcessRequest

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
                            content={
                                'response' : response_message
                            }
                        )

                    # file_id is the file's name(e.g, "file.txt")
                    file_path, file_id = data_controller.generate_unique_filepath(
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
                            content={
                                'response' : ResponseSignal.FILE_UPLOAD_FAIL.value
                            }
                        )
                        
                    return JSONResponse(
                        content={
                            'response' : ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                            'file_id' : file_id
                        }
                    )

@data_router.post('/process/{project_id}')
async def process_file(project_id: str, process_request: ProcessRequest):
    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size

    if not process_request.check_file_exists(project_id=project_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                'response' : ResponseSignal.FILE_NOT_FOUND.value
            }
        )

    process_controller = ProcessController(project_id=project_id)
    file_content = process_controller.get_file_content(file_id=file_id)

    chunks = process_controller.process_file_content(
        file_content=file_content,
        chunk_size=chunk_size, 
        overlap_size=overlap_size
    )

    if chunks is None or len(chunks) == 0 :
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ResponseSignal.PROCESSING_FAIL.value
        )
    
    return chunks