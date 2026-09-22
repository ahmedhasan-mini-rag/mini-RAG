from utils.config import get_settings

settings = get_settings()

port = 5555
max_tasks = 7000
auto_refresh = True
basic_auth = [f'admin:{settings.CELERY_FLOWER_PASS}']