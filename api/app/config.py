from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[1] / '.env', extra='ignore')
    database_url: str = ''
    app_env: str = 'development'
    synthetic_data_only: bool = True
    cookie_secure: bool = False
    model_provider: str = 'none'
    model_endpoint: str = 'http://127.0.0.1:11434/api/chat'
    model_name: str = ''
    model_api_key: str = ''
    model_timeout_seconds: int = 15


settings = Settings()
