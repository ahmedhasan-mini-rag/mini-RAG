from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
import aiofiles
import logging
import os

from helpers.config import get_settings, Settings
from controllers import DataController, ProcessController
from models.enums import ResponseSignal, AssetTypeEnums
from models.schemas import ProcessRequest, DataChunk, Asset
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel

data_router = APIRouter(
    prefix='/api/v1/data',
    tags=['api_v1', 'data']
)

logger = logging.getLogger('uvicorn.error')

@data_router.post('/upload/{project_id}')
async def upload_file(request: Request,project_id: str, file: UploadFile,
                    settings: Settings = Depends(get_settings)) -> JSONResponse:
                    
                    project_model = await ProjectModel.create_instance(
                        db_client=request.app.state.db_client
                    )

                    project = await project_model.get_project(
                        project_id=project_id,
                        create_if_missing=True
                    )

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
                    
                    # create the file asset in the database
                    asset_model = await AssetModel.create_instance(
                        db_client=request.app.state.db_client
                    )

                    asset = Asset(
                        asset_project_id=project.id,
                        asset_type=AssetTypeEnums.FILE.value,
                        asset_name=file_id,
                        asset_size=os.path.getsize(file_path),
                    )
                    file_asset = await asset_model.insert_asset(asset=asset)

                    return JSONResponse(
                        content={
                            'response' : ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                            'file_id' : str(file_asset.id),
                            'project_id' : project_id
                        }
                    )

@data_router.post('/process/{project_id}')
async def process_file(request: Request, project_id: str, process_request: ProcessRequest):
    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    # check file existence 
    if not process_request.check_file_exists(project_id=project_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                'response' : ResponseSignal.FILE_NOT_FOUND.value
            }
        )

    project_model = await ProjectModel.create_instance(
        db_client=request.app.state.db_client
    )

    project = await project_model.get_project(
        project_id=project_id,
        create_if_missing=False
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
    
    data_chunks = [
        DataChunk(
            chunk_text = chunk.page_content,
            chunk_metadata = chunk.metadata,
            chunk_order = i,
            chunk_project_id = project.id
        )
        for i, chunk in enumerate(chunks, 1)
    ]

    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.state.db_client
    )

    if do_reset:
        _ = await chunk_model.delete_multiple_chunks(db_project_id=project.id)

    num_chunks_inserted = await chunk_model.insert_multiple_chunks(chunks=data_chunks)

    return JSONResponse(
        content={
            'response' : ResponseSignal.PROCESSING_SUCCESS.value,
            'inserted_chunks' : num_chunks_inserted
        }
    )