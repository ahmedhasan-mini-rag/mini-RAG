from utils.config import get_settings, Settings
from bson import ObjectId

class CustomBaseModel:
    def __init__(self, db_client):
        self.db_client = db_client
        self.settings = get_settings()
    
    def prepare_id(self, idx: str | ObjectId) -> ObjectId:
        return ObjectId(idx) if isinstance(idx, str) else idx
