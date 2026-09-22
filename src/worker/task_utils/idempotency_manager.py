"""Manager for tracking and maintaining idempotency of Celery task executions in the database."""

import json, uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, delete

from models.schemas.db import CeleryTaskExecution
from exceptions import DatabaseWriteError, DatabaseReadError
from .enums import TaskState

class IdempotencyManager:
    def __init__(self, db_client):
        self.db_client = db_client

    def create_task_hash(self, task_args: dict, task_name: str, celery_id: str) -> str:
        task_content = {
            **task_args,
            'task_name': task_name,
            'celery_id': celery_id
        }
        json_string = json.dumps(task_content, sort_keys=True, default=str)

        return str(uuid.uuid5(uuid.NAMESPACE_OID, json_string))

    async def create_task_record(
            self, 
            task_name: str, 
            task_args: dict, 
            celery_id: str
    ) -> CeleryTaskExecution:

        hash_id = self.create_task_hash(task_args, task_name, celery_id)
        task = CeleryTaskExecution(
            name=task_name,
            state=TaskState.PENDING,
            celery_id=celery_id,
            unique_hash=hash_id
        )
        
        try:
            async with self.db_client() as session:
                async with session.begin():
                    session.add(task)
                await session.refresh(task)
        except SQLAlchemyError as e:
            raise DatabaseWriteError(
                f"Failed to insert the task '{task_name}'", detail=str(e)
            ) from e
        return task

    async def update_task_state(
            self, 
            task_args: dict, 
            task_name: str,
            celery_id: str,
            state: str
    ) -> CeleryTaskExecution:
        
        hash_id = self.create_task_hash(task_args, task_name, celery_id)
        try:
            async with self.db_client() as session:
                async with session.begin():
                    task = await session.get(CeleryTaskExecution, hash_id)

                    task.state = state
                    if state == TaskState.STARTED:
                        task.started_at = datetime.now(timezone.utc)
                    elif state in [TaskState.SUCCESS, TaskState.FAILURE]:
                        task.finished_at = datetime.now(timezone.utc)
        except SQLAlchemyError as e:
            raise DatabaseWriteError(
                f"Failed to update the task '{task_name}'", detail=str(e)
            ) from e
        return task

    async def get_task(
            self, 
            task_args: dict, 
            task_name: str, 
            celery_id: str
    ) -> CeleryTaskExecution | None:
        
        hash_id = self.create_task_hash(task_args, task_name, celery_id)

        try:
            async with self.db_client() as session:
                stmt = select(CeleryTaskExecution).where(
                    CeleryTaskExecution.name == task_name,
                    CeleryTaskExecution.unique_hash == hash_id
                )

                result = await session.execute(stmt)
                task = result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseWriteError(
                f"Failed to get the task '{task_name}'", detail=str(e)
            ) from e

        return task 

    async def task_execution_allowed(
            self, 
            task_args: dict, 
            task_name: str,
            celery_id: str,
            task_time_limit: int
    ) -> tuple[bool, CeleryTaskExecution | None]:

        task = await self.get_task(task_args, task_name, celery_id)

        if not task:
            return True, task

        if task.state == TaskState.PENDING:
            return True, task
        elif task.state == TaskState.SUCCESS:
            return False, task
        elif task.state == TaskState.STARTED:
            time_tol = 15
            time_elapsed = task.started_at - datetime.now(timezone.utc)

            if time_elapsed.total_seconds() > (task_time_limit + time_tol):
                return True, task
            else:
                return False, task

        return True, task # Failure state

    async def cleanup_old_tasks(self, retention_time: int = 86400) -> int:
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=retention_time)
        try:
            async with self.db_client() as session:
                async with session.begin():
                    stmt = delete(CeleryTaskExecution).where(
                        CeleryTaskExecution.created_at < cutoff_time
                    )
                    result = await session.execute(stmt)
        except SQLAlchemyError as e:
            raise DatabaseWriteError(
                "Failed to clean up the table", detail=str(e)
            ) from e
        
        return result.rowcount
