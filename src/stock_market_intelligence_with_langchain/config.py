"""Configuration is loaded explicitly, never during module import."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    market_data_dir: Path = Path("data")
    deepseek_api_key: SecretStr = SecretStr("")
    fred_api_key: SecretStr = SecretStr("")
    sec_user_agent: str = ""

    @property
    def database_path(self) -> Path:
        return self.market_data_dir / "market.sqlite3"
