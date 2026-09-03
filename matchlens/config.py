from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file=".env",extra="ignore")
    api_key: str = ""
    public_base_url: str = ""
    data_dir: Path = Path("/data")
    max_download_gb: float = 8
    download_timeout_minutes: int = 45
    worker_concurrency: int = 1
    analyzer_command: str = ""
    analyzer_timeout_minutes: int = 360
    signed_url_ttl_minutes: int = 1440
    log_level: str = "INFO"


settings=Settings()
