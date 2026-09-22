import asyncio
import logging
from celery import shared_task, Task
from celery.exceptions import Ignore
from sqlalchemy.exc import OperationalError, TimeoutError as SATimeoutError, DisconnectionError

from utils.config import get_settings
from models.schemas import ProcessRequest
from models import ChunkModel, AssetModel, ProjectModel
from controllers import ProcessController
from worker.task_utils.services_registry import register_task_utils, TaskService, get_task_utils
from worker.task_utils.idempotency_manager import IdempotencyManager
from worker.task_utils.enums import TaskState
from exceptions import DatabaseError

logger = logging.getLogger(__name__)
settings = get_settings()

@register_task_utils(TaskService.DB_CLIENT) # type: ignore
@shared_task(
    bind=True,
    name="process_project_data.process",
    autoretry_for=(
        OperationalError,
        SATimeoutError,
        DisconnectionError,
        DatabaseError,
        ConnectionError,
    ),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def process(
    self: Task, 
    project_name: str, 
    process_request: dict
) -> dict[str, int | list[str]]:
    try:
        result = asyncio.run(
            _process(self, project_name, process_request) # type: ignore
        )
        return result
    except Exception as exc:
        self.update_state(
            state=TaskState.FAILURE,
            meta={'exc_type': type(exc).__name__, 'exc_message': str(exc)}
        )
        raise


async def _process(task_instance: Task, project_name: str, process_request: dict):
    task_name: str = task_instance.name # type: ignore
    utils = await get_task_utils(task_name)

    try:
        idempotency_manager = IdempotencyManager(db_client=utils[TaskService.DB_CLIENT])
        task_args = {
            'project_name': project_name,
            'process_request': process_request
        }

        execution_allowed, task = await idempotency_manager.task_execution_allowed(
            task_args=task_args,
            task_name=task_name, 
            celery_id=task_instance.request.id,
            task_time_limit=settings.CELERY_TASK_TIME_LIMIT
        )

        if not execution_allowed:
            logger.warning(
                f'Worker not allowed to start the task: {task_name}. '
                f'current task state: {task.state}' # type: ignore
            )
            raise Ignore()

        await idempotency_manager.update_task_state(
            task_args=task_args,
            task_name=task_name,
            celery_id=task_instance.request.id,
            state=TaskState.STARTED
        )

        project_model = ProjectModel(db_client=utils[TaskService.DB_CLIENT])
        project = await project_model.get_project(
            project_name=project_name,
            create_if_missing=False
        )

        chunk_model = ChunkModel(db_client=utils[TaskService.DB_CLIENT])
        asset_model = AssetModel(db_client=utils[TaskService.DB_CLIENT])

        request = ProcessRequest(**process_request)

        results = {}
        if request.do_reset:
            results['deleted_chunks'] = await chunk_model.delete_project_chunks(
                chunk_project_id=project.id
            )

        process_controller = ProcessController(project=project)
        results.update(
            await process_controller.process_tasks(
                process_request=request,
                chunk_model=chunk_model,
                asset_model=asset_model,
            )
        )

        await idempotency_manager.update_task_state(
            task_args=task_args,
            task_name=task_name,
            celery_id=task_instance.request.id,
            state=TaskState.SUCCESS
        )
        return results
    except Exception:
            await idempotency_manager.update_task_state(
                task_args=task_args,
                task_name=task_name,
                celery_id=task_instance.request.id,
                state=TaskState.FAILURE
            )
            raise
    finally:
        await utils[TaskService._DB_ENGINE].dispose()