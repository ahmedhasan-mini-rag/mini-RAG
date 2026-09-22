import asyncio
import logging
from celery import shared_task, Task
from sqlalchemy.exc import OperationalError, TimeoutError as SATimeoutError, DisconnectionError

from utils.config import get_settings
from worker.task_utils.services_registry import register_task_utils, TaskService, get_task_utils
from worker.task_utils.idempotency_manager import IdempotencyManager

logger = logging.getLogger(__name__)
settings = get_settings()

@register_task_utils(TaskService.DB_CLIENT) # type: ignore
@shared_task(
    bind=True,
    name="maintenance.clean_up",
    autoretry_for=(
        OperationalError,
        SATimeoutError,
        DisconnectionError,
    ),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def clean_up(self):
    async def _run():
        try:
            utils = await get_task_utils(self.name)
            idempotency_manager = IdempotencyManager(utils[TaskService.DB_CLIENT])
            await idempotency_manager.cleanup_old_tasks(settings.TASK_EXECUTION_TABLE_RETENTION_TIME)
        finally:
            await utils[TaskService._DB_ENGINE].dispose()

    asyncio.run(_run())

