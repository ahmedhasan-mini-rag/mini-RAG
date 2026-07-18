from fastapi import APIRouter, Depends
from utils.config import get_settings, Settings

base_router = APIRouter(
    prefix='/api/v1',
    tags=['api_v1']
)

@base_router.get('/')
async def welcome(settings: Settings = Depends(get_settings)):
    return{
        'app_name' : settings.APP_NAME,
        'app_version' : settings.APP_VERSION
    }