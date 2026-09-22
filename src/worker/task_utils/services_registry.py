"""Registry and provider functions for initializing and injecting services required by worker tasks."""

from typing import Any
from celery import Task
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from utils.config import get_settings
from services.llms import LLMProviderFactory
from services.vectordb import VectorDBProviderFactory
from .enums import TaskService

UTILS_REGISTRY: dict[str, list[TaskService]] = {}
CONFIG = get_settings()

def _get_db_client():
    engine = create_async_engine(CONFIG.sqlalchemy_url)
    db_client = async_sessionmaker(
        engine, expire_on_commit=False
    )

    return engine, db_client

def _get_chat_client():
    llm_client_factory = LLMProviderFactory(config=CONFIG)
    
    chat_client = llm_client_factory.create(
        provider=CONFIG.CHAT_MODEL_PROVIDER
    )
    chat_client.set_chat_model(model_id=CONFIG.CHAT_MODEL_ID)

    return chat_client

def _get_embedding_client(chat_client):
    if CONFIG.CHAT_MODEL_PROVIDER == CONFIG.EMBEDDING_MODEL_PROVIDER:
        embedding_client = chat_client

        embedding_client.set_embedding_model(
            model_id=CONFIG.EMBEDDING_MODEL_ID,
            embedding_size=CONFIG.EMBEDDING_SIZE
        )
    else:
        llm_client_factory = LLMProviderFactory(config=CONFIG)

        embedding_client = llm_client_factory.create(
            provider=CONFIG.EMBEDDING_MODEL_PROVIDER
        )
        embedding_client.set_embedding_model(
            model_id=CONFIG.EMBEDDING_MODEL_ID,
            embedding_size=CONFIG.EMBEDDING_SIZE
        )
    return embedding_client

def _get_vectordb_client(db_client=None):
    if not db_client:
        db_client = _get_db_client()
    
    vectordb_client_factory = VectorDBProviderFactory(
        pg_client=db_client,
        config=CONFIG
    )

    vectordb_client = vectordb_client_factory.create(
        provider=CONFIG.VECTORDB_PROVIDER
    )
    return vectordb_client

_ORDERED_UTIL_RESOLVER = {
    TaskService.DB_CLIENT: _get_db_client,
    TaskService.CHAT_CLIENT: _get_chat_client,
    TaskService.EMBEDDING_CLIENT: _get_embedding_client,
    TaskService.VECTORDB_CLIENT: _get_vectordb_client,
}

def register_task_utils(*task_utils):
    def decorator(task: Task) -> Task:
        ordered = [
            util for util in _ORDERED_UTIL_RESOLVER.keys() 
            if util in task_utils
        ]
        UTILS_REGISTRY[task.name] = ordered # type: ignore
        return task

    return decorator

async def get_task_utils(task_name: str) -> dict[TaskService, Any]:
    utils = UTILS_REGISTRY[task_name]
    utils_dict = {}

    if TaskService.DB_CLIENT in utils:
        engine, db_client = _get_db_client()
        utils_dict[TaskService.DB_CLIENT] = db_client
        utils_dict[TaskService._DB_ENGINE] = engine

    if TaskService.CHAT_CLIENT in utils:
        utils_dict[TaskService.CHAT_CLIENT] = _get_chat_client()
        
    if TaskService.EMBEDDING_CLIENT in utils:
        utils_dict[TaskService.EMBEDDING_CLIENT] = _get_embedding_client(
            utils_dict.get(TaskService.CHAT_CLIENT)
        )

    if TaskService.VECTORDB_CLIENT in utils:
        vectordb_client = _get_vectordb_client(
            utils_dict.get(TaskService.DB_CLIENT)
        )

        await vectordb_client.init_db()
        utils_dict[TaskService.VECTORDB_CLIENT] = vectordb_client


    return utils_dict
