from utils.config import get_settings, setup_logging
from celery import Celery
from celery.signals import setup_logging as celery_setup_logging

@celery_setup_logging.connect
def config_loggers(*args, **kwargs):
    setup_logging()

settings = get_settings()

celery_app = Celery(
    main='minirag',
    broker=settings.celery_broker_url,
    backend=settings.celery_results_backend_url,
    include=[
        "worker.tasks.process_project_data",
        "worker.tasks.embed_project_chunks",
        "worker.tasks.maintenance"
    ]
)

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=[settings.CELERY_TASK_SERIALIZER],

    task_acks_late=settings.CELERY_TASK_ACKS_LATE,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    worker_concurrency=settings.CELERY_TASK_WORKER_CONCURRENCY, # parallel tasks allowed per worker

    task_ignore_result=False,
    result_expires=3600, # time before deleting the result from the result backend

    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=5,
    worker_cancel_long_running_tasks_on_connection_loss=True,

    task_default_queue='default',

    task_routes={
        "worker.tasks.process_project_data.process": {"queue": "process_project_data"},
        "worker.tasks.embed_project_chunks.process": {"queue": "embed_project_chunks"},
        "worker.tasks.maintenance.clean_up": {"queue": "default"}
    },

    beat_schedule = {
        "cleanup_old_tasks": {
            "task": "worker.tasks.maintenance.clean_up",
            "schedule": settings.TASK_EXECUTION_TABLE_RETENTION_TIME,
            "args": ()
        }
    },

    timezone = 'UTC'
)
