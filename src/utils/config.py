from pydantic_settings import BaseSettings, SettingsConfigDict
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
        env_file=BASE_DIR / 'src' / '.env',
        env_ignore_empty=True,
        extra='ignore'
    )
    APP_NAME: str 
    APP_VERSION: str

    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    FILE_CHUNK_SIZE: int
    
    MONGODB_URL: str
    MONGODB_DATABASE: str

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
