from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
import logging
import shutil

from utils.config import get_settings, Settings
from controllers import DataController, NLPController, ProjectController
from models.enums import ResponseSignal
from models.schemas import ProcessRequest
from models import ChunkModel, AssetModel
from exceptions import ProjectNotFoundError
from worker.celery_app import celery_app
from worker.tasks.process_project_data import process
from worker.task_utils.idempotency_manager import IdempotencyManager

data_router = APIRouter(
    prefix='/api/data',
    tags=['data']
)

logger = logging.getLogger(__name__)
settings = get_settings()

@data_router.post('/upload/{project_name}')
async def upload_files(
    request: Request, 
    project_name: str, 
    files: list[UploadFile]
) -> JSONResponse:
    """Upload files to a specified project.

    Args:
        request (Request): FastAPI request object containing application context.
        project_name (str): Name of the target project for file upload.
        files (list[UploadFile]): List of uploaded files to process and store.

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
    idempotency_manager = IdempotencyManager(db_client=request.app.state.db_client)

    process_request_dict = process_request.model_dump()
    task_args = {
        'project_name': project_name,
        'process_request': process_request_dict
    }

    task = process.delay(
        project_name=project_name,
        process_request=process_request_dict,
    )

    _ = await idempotency_manager.create_task_record(
        task_args=task_args,
        task_name=process.name, # type: ignore
        celery_id=task.id
    )

    return JSONResponse(
        content={
            'response' : ResponseSignal.TASK_IN_PROGRESS,
            'task_id' : task.id
        }
    )

@data_router.get('/tasks/{task_id}')
async def get_task_status(task_id: str) -> JSONResponse:
    """Check the status and result of a background processing task.

    Args:
        task_id (str): The Celery task ID returned by the process endpoint.

    Returns:
        JSONResponse: Response containing the task state and result (if available).
    """
    result = celery_app.AsyncResult(task_id)

    response = {
        'task_id': task_id,
        'state': result.state,
    }

    if result.ready():
        if result.successful():
            response['result'] = result.result
        else:
            response['error'] = str(result.result)

    return JSONResponse(content=response)

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