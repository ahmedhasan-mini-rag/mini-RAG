import asyncio
import logging
from celery import shared_task, Task
from celery.exceptions import Ignore
from sqlalchemy.exc import OperationalError, TimeoutError as SATimeoutError, DisconnectionError

from utils.config import get_settings
from models import ChunkModel, ProjectModel
from controllers import NLPController
from worker.task_utils.services_registry import register_task_utils, TaskService, get_task_utils
from worker.task_utils.idempotency_manager import IdempotencyManager
from worker.task_utils.enums import TaskState
from exceptions import DatabaseError, LLMServiceError, VectorDBServiceError

logger = logging.getLogger(__name__)
settings = get_settings()

@register_task_utils( # type: ignore
    TaskService.DB_CLIENT, TaskService.CHAT_CLIENT,
    TaskService.EMBEDDING_CLIENT, TaskService.VECTORDB_CLIENT
)
@shared_task(
    bind=True,
    name='embed_project_chunks.process',
    autoretry_for=(
        OperationalError,
        SATimeoutError,
        DisconnectionError,
        DatabaseError,
        LLMServiceError,
        VectorDBServiceError,
        ConnectionError,
    ),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def process(self, project_name: str, do_reset: bool):
    try:
        result = asyncio.run(
            _process(self, project_name, do_reset)
        )
        return result
    except Exception as exc:
        self.update_state(
            state=TaskState.FAILURE,
            meta={'exc_type': type(exc).__name__, 'exc_message': str(exc)}
        )
        raise


async def _process(task_instance: Task, project_name: str, do_reset: bool):
    task_name: str = task_instance.name # type: ignore
    utils = await get_task_utils(task_name)

    try:
        idempotency_manager = IdempotencyManager(db_client=utils[TaskService.DB_CLIENT])
        task_args = {
            'project_name': project_name,
            'do_reset': do_reset
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

        # create a function in celery_tasks file or celery_app.py
        # that manages the used utils.
        nlp_controller = NLPController(
            chat_client=utils[TaskService.CHAT_CLIENT],
            embedding_client=utils[TaskService.EMBEDDING_CLIENT],
            vectordb_client=utils[TaskService.VECTORDB_CLIENT]
        )

        chunk_model = ChunkModel(db_client=utils[TaskService.DB_CLIENT])

        # Materialize all chunks upfront so the streaming DB session is released
        # before any vectordb operations that need connections from the same pool.
        chunks = [
            chunk async for chunk 
            in chunk_model.get_project_chunks(chunk_project_id=project.id)
        ]

        BATCH_SIZE = 50

        num_inserted = await nlp_controller.embed_and_store_chunks(
            project_name=project_name,
            chunks=chunks,
            do_reset=do_reset,
            batch_size=BATCH_SIZE
        )

        await idempotency_manager.update_task_state(
            task_args=task_args,
            task_name=task_name,
            celery_id=task_instance.request.id,
            state=TaskState.SUCCESS
        )

        return {'inserted_vectors' : num_inserted}
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

