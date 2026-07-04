import random
import string
from helpers.config import get_settings, Settings, BASE_DIR

class BaseController:
    def __init__(self):
        self.app_settings = get_settings()
        self.files_dir = BASE_DIR / 'src' / 'assets' / 'files'
    
    def generate_random_string(self, length: int = 8) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
