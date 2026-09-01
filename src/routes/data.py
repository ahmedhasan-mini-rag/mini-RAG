from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
import logging
import shutil

from utils.config import get_settings, Settings
from controllers import DataController, ProcessController, NLPController, ProjectController
from models.enums import ResponseSignal
from models.schemas import ProcessRequest
from models import ChunkModel, AssetModel
from exceptions import ProjectNotFoundError

data_router = APIRouter(
    prefix='/api/v1/data',
    tags=['api_v1', 'data']
)

logger = logging.getLogger(__name__)

@data_router.post('/upload/{project_name}')
async def upload_files(
    request: Request, 
    project_name: str, 
    files: list[UploadFile],
    settings: Settings = Depends(get_settings)
) -> JSONResponse:
    """Upload files to a specified project.

    Args:
        request (Request): FastAPI request object containing application context.
        project_name (str): Name of the target project for file upload.
        files (list[UploadFile]): List of uploaded files to process and store.
        settings (Settings, optional): Application settings injected via dependency.

    Returns:
        JSONResponse: Response indicating upload outcome alongside lists of
            successful and failed file uploads.
    """

    asset_model = AssetModel(db_client=request.app.state.db_client)

    project = await request.app.state.project_model.get_project(
        project_name=project_name,
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
            'project_name': project_name,
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads
        }
    )


@data_router.post('/process/{project_name}')
async def process_project_data(
    request: Request, 
    project_name: str, 
    process_request: ProcessRequest
) -> JSONResponse:
    """Process uploaded project assets into searchable text chunks.

    Args:
        request (Request): FastAPI request object containing application context.
        project_name (str): Name of the target project.
        process_request (ProcessRequest): Parameters controlling chunk size, overlap,
            and optional chunk reset flag.

    Returns:
        JSONResponse: Response containing processing status and breakdown of processed
            files and generated chunks.
    """

    project = await request.app.state.project_model.get_project(
        project_name=project_name,
        create_if_missing=False
    )

    chunk_model = ChunkModel(db_client=request.app.state.db_client)
    asset_model = AssetModel(db_client=request.app.state.db_client)

    results = {}
    if process_request.do_reset:
        results['deleted_chunks'] = await chunk_model.delete_project_chunks(chunk_project_id=project.id)
    
    process_controller = ProcessController(project=project)

    results.update(
        await process_controller.process_tasks(
            process_request=process_request,
            chunk_model=chunk_model,
            asset_model=asset_model,
        )
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

@data_router.delete('/delete/{project_name}')
async def delete_project(request: Request, project_name: str) -> JSONResponse:
    """Delete a project and all associated data and its vector database collection.

    Args:
        request (Request): FastAPI request object containing application context.
        project_name (str): Name of the project to delete.

    Returns:
        JSONResponse: Response indicating deletion status.
    """
    try:
        project = await request.app.state.project_model.get_project(
            project_name=project_name,
            create_if_missing=False
        )
    except ProjectNotFoundError:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={
                'response': ResponseSignal.PROJECT_NOT_FOUND,
                'project_name': project_name
            }
        )

    chunk_model = ChunkModel(db_client=request.app.state.db_client)
    asset_model = AssetModel(db_client=request.app.state.db_client)

    await chunk_model.delete_project_chunks(chunk_project_id=project.id)
    await asset_model.delete_project_assets(asset_project_id=project.id)
    await request.app.state.project_model.delete_project(project_name=project_name)
    await request.app.state.vectordb_client.delete_collection(
        collection_name=NLPController.create_collection_name(project_name)
    )

    project_storage_path = ProjectController().get_project_path(
        project_name=project_name, 
        create_if_missing=False
    )

    if project_storage_path.exists():
        shutil.rmtree(project_storage_path)

    logger.info(f"Project '{project_name}' was wiped out successfully.")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'response': ResponseSignal.PROJECT_DELETED,
            'project_name': project_name
        }
    )