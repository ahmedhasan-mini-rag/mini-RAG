from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import AsyncMongoClient

from routes import base, data, nlp
from utils.config import Settings, get_settings, setup_logging
from services.llms import LLMProviderFactory
from services.vectordb import VectorDBProviderFactory
from models import ProjectModel
from exceptions import (
    NotFoundError, ValidationError, DatabaseError,
    ServiceError, FileIOError as AppFileIOError,
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    app.state.mongo_client = AsyncMongoClient(settings.MONGODB_URL)
    app.state.db_client = app.state.mongo_client[settings.MONGODB_DATABASE]

    app.state.project_model = await ProjectModel.create_instance(
        db_client=app.state.db_client
    )

    clients = prepare_clients(settings)

    app.state.chat_client = clients['chat_client']
    app.state.embedding_client = clients['embedding_client']
    app.state.vectordb_client = clients['vectordb_client']

    yield 

    await app.state.mongo_client.close()
    await app.state.vectordb_client.disconnect()


def prepare_clients(settings: Settings) -> dict:
    llm_client_factory = LLMProviderFactory(config=settings)

    chat_client = llm_client_factory.create(
        provider=settings.CHAT_MODEL_PROVIDER
    )
    chat_client.set_chat_model(model_id=settings.CHAT_MODEL_ID)

    # set the system message (optional)

    if settings.CHAT_MODEL_PROVIDER == settings.EMBEDDING_MODEL_PROVIDER:
        embedding_client = chat_client

        embedding_client.set_embedding_model(
            model_id=settings.EMBEDDING_MODEL_ID,
            embedding_size=settings.EMBEDDING_SIZE
        )
    else:
        embedding_client = llm_client_factory.create(
            provider=settings.EMBEDDING_MODEL_PROVIDER
        )
        embedding_client.set_embedding_model(
            model_id=settings.EMBEDDING_MODEL_ID,
            embedding_size=settings.EMBEDDING_SIZE
        )

    vectordb_client_factory = VectorDBProviderFactory(
        similarity_metric=settings.VECTORDB_SIMILARITY_METRIC
    )

    vectordb_client = vectordb_client_factory.create(
        provider=settings.VECTORDB_PROVIDER
    )

    return {
        'chat_client': chat_client,
        'embedding_client': embedding_client,
        'vectordb_client': vectordb_client
    }

setup_logging()

app = FastAPI(lifespan=lifespan)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": exc.message}
    )

@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": exc.message}
    )

@app.exception_handler(DatabaseError)
async def database_handler(request: Request, exc: DatabaseError):
    logger.error(f"Database error: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=503,
        content={"error": "A database error occurred"}
    )

@app.exception_handler(ServiceError)
async def service_handler(request: Request, exc: ServiceError):
    logger.error(f"Service error: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=502,
        content={"error": exc.message}
    )

@app.exception_handler(AppFileIOError)
async def file_io_handler(request: Request, exc: AppFileIOError):
    logger.error(f"File I/O error: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "A file system error occurred"}
    )

@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.critical(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )