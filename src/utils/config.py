from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
import tomllib
import yaml
import logging
import logging.config
from pathlib import Path

from exceptions import InvalidConfigError

BASE_DIR = Path(__file__).resolve().parents[2]

def _read_toml() -> dict:
    toml_path = BASE_DIR / "pyproject.toml"

    try:
        with open(toml_path, "rb") as f:
            project_data = tomllib.load(f)
    except FileNotFoundError:
        raise InvalidConfigError(f"pyproject.toml file missing at {toml_path}")
    except tomllib.TOMLDecodeError:
        raise InvalidConfigError(f"{toml_path} is corrupted or has invalid formatting")
    
    return project_data.get('project', {})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env',
        env_ignore_empty=True,
        extra='ignore'
    )
    APP_NAME: str 
    APP_VERSION: str

    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    FILE_CHUNK_SIZE: int
    
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int
    POSTGRES_HOST: str

    CHAT_MODEL_PROVIDER: str
    EMBEDDING_MODEL_PROVIDER: str

    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    COHERE_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None

    CHAT_MODEL_ID: str 
    EMBEDDING_MODEL_ID: str
    EMBEDDING_SIZE: int | None = None

    DEFAULT_MAX_OUTPUT_TOKENS: int = 1400
    DEFAULT_MAX_INPUT_CHARS: int = 1800
    DEFAULT_TEMPERATURE: float = 0.5

    VECTORDB_PROVIDER: str
    VECTORDB_SIMILARITY_METRIC: str
    VECTORDB_INDEX_BUILDING_THRESHOLD: int
    VECTORDB_INDEX_TYPE: str

    SCANNED_PAGE_TEXT_MAX_LIMIT: int
    SCANNED_PAGE_MIN_RATIO_LIMIT: float
    CONVERSION_DPI: int = 150
    OCR_MODEL_ID: str
    OCR_MODEL_URL: str
    OCR_MODEL_API_KEY: str
    MAX_CONCURRENT_VLM_CALLS: int = 3

    R2_BUCKET_NAME: str
    R2_ACCOUNT_ID: str
    R2_PUBLIC_URL: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str

    @computed_field
    @property
    def sqlalchemy_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @computed_field
    @property
    def r2_bucket_config(self) -> dict:
        return {
            'bucket_name': self.R2_BUCKET_NAME,
            'account_id': self.R2_ACCOUNT_ID,
            'r2_public_url': self.R2_PUBLIC_URL,
            'access_key_id': self.R2_ACCESS_KEY_ID,
            'secret_access_key': self.R2_SECRET_ACCESS_KEY
        }


def get_settings() -> Settings:
    meta_data = _read_toml()
    settings = Settings( 
        APP_NAME = meta_data.get('name', 'unknown'),
        APP_VERSION = meta_data.get('version', 'unknown')
    )

    return settings

def setup_logging():
    yaml_path = BASE_DIR / "logging_config.yml"
    logs_dir = BASE_DIR / "logs"
    
    logs_dir.mkdir(exist_ok=True)
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as file:
            logger_config = yaml.safe_load(file)
            
        if "handlers" in logger_config:
            if "app_file" in logger_config["handlers"]:
                logger_config["handlers"]["app_file"]["filename"] = str(logs_dir / "app.log")
            if "error_file" in logger_config["handlers"]:
                logger_config["handlers"]["error_file"]["filename"] = str(logs_dir / "error.log")
        
        logging.config.dictConfig(logger_config)
        
    except FileNotFoundError:
        print(f"Warning: Logging config file '{yaml_path}' not found. Using default basic logging.")
        logging.basicConfig(level=logging.INFO)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        logging.basicConfig(level=logging.INFO)
