from utils.config import get_settings

class CustomBaseModel:
    def __init__(self, db_client):
        self.db_client = db_client
        self.settings = get_settings()

