from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from pymongo import AsyncMongoClient

from routes import base, data
from helpers.config import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    app.state.mongo_client = AsyncMongoClient(settings.MONGODB_URL)
    app.state.db_client = app.state.mongo_client[settings.MONGODB_DATABASE]

    yield 

    app.state.mongo_client.close()

app = FastAPI(lifespan=lifespan)

app.include_router(base.base_router)
app.include_router(data.data_router)

if __name__ == "__main__":
    ...
