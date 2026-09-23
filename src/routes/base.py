from fastapi import APIRouter, Depends
from utils.config import get_settings, Settings

base_router = APIRouter(
    prefix='/api',
    tags=['api']
)

@base_router.get('/')
async def welcome(settings: Settings = Depends(get_settings)):
    """Retrieve application metadata.

    Args:
        settings (Settings, optional): Application settings injected via dependency.

    Returns:
        str: Welcoming string containing application name and version.
    """

    return {
        'message': 'Welcome to the mini RAG application! :)',
        'app_name': settings.APP_NAME,
        'app_version': settings.APP_VERSION
    }

