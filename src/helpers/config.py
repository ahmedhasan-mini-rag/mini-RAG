from pydantic_settings import BaseSettings, SettingsConfigDict
import tomllib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

def _read_toml() -> dict:
    toml_path = BASE_DIR / "pyproject.toml"

    try:
        with open(toml_path, "rb") as f:
            project_data = tomllib.load(f)
    except FileNotFoundError:
        print(f"Error: pyproject.toml file missing at {toml_path}")
        project_data = {} 
    except tomllib.TOMLDecodeError:
        print(f"Error: {toml_path} is corrupted or has invalid formatting.")
        exit(1)
    
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

def get_settings() -> Settings:
    meta_data = _read_toml()
    settings = Settings( 
        APP_NAME = meta_data.get('name', 'unknown'),
        APP_VERSION = meta_data.get('version', 'unknown')
    )

    return settings
