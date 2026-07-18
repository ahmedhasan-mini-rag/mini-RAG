from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from pymongo import AsyncMongoClient

from routes import base, data
from utils.config import get_settings, setup_logging
from services.llms import LLMProviderFactory

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    app.state.mongo_client = AsyncMongoClient(settings.MONGODB_URL)
    app.state.db_client = app.state.mongo_client[settings.MONGODB_DATABASE]

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

    app.state.chat_client = chat_client
    app.state.embedding_client = embedding_client

    yield 

    app.state.mongo_client.close()

setup_logging()

app = FastAPI(lifespan=lifespan)

app.include_router(base.base_router)
app.include_router(data.data_router)

if __name__ == "__main__":
    ...
