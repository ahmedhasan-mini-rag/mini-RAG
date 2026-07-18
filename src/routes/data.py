from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
import aiofiles
import logging
import os

from utils.config import get_settings, Settings
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

logger = logging.getLogger(__name__)

@data_router.post('/upload/{project_id}')
async def upload_file(
    request: Request, 
    project_id: str, 
    files: list[UploadFile],
    settings: Settings = Depends(get_settings)
) -> JSONResponse:

    project_model = await ProjectModel.create_instance(
        db_client=request.app.state.db_client
    )

    asset_model = await AssetModel.create_instance(
        db_client=request.app.state.db_client
    )

    project = await project_model.get_project(
        project_id=project_id,
        create_if_missing=True
    )

    data_controller = DataController(project=project)

    successful_uploads, failed_uploads = await data_controller.process_tasks(
        files=files,
        asset_model=asset_model,
    )

    if not successful_uploads:
        status_code = status.HTTP_400_BAD_REQUEST
        final_response = ResponseSignal.FILE_UPLOAD_FAIL
    else:
        status_code = status.HTTP_200_OK
        final_response = ResponseSignal.FILE_UPLOAD_SUCCESS
    
    return JSONResponse(
        status_code=status_code,
        content={
            'response': final_response,
            'project_id': project_id,
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads
        }
    )


@data_router.post('/process/{project_id}')
async def process_file(
    request: Request, 
    project_id: str, 
    process_request: ProcessRequest
) -> JSONResponse:

    project_model = await ProjectModel.create_instance(
        db_client=request.app.state.db_client
    )

    project = await project_model.get_project(
        project_id=project_id,
        create_if_missing=False
    )

    if project is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                'response': ResponseSignal.PROJECT_NOT_FOUND
            }
        )

    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.state.db_client
    )

    asset_model = await AssetModel.create_instance(
        db_client=request.app.state.db_client
    )

    if process_request.do_reset:
        _ = await chunk_model.delete_multiple_chunks(db_project_id=project.id)
    
    process_controller = ProcessController(project=project)

    results = await process_controller.process_tasks(
        process_request=process_request,
        chunk_model=chunk_model,
        asset_model=asset_model,
    )
    
    if results['processed_files'] > 0:
        status_code = status.HTTP_200_OK
        final_response = ResponseSignal.PROCESSING_SUCCESS
    else:
        status_code = status.HTTP_404_NOT_FOUND
        final_response = ResponseSignal.FILE_NOT_FOUND

    return JSONResponse(
        status_code=status_code,
        content={
            'response' : final_response,
            'processing_details' : results
        }
    )