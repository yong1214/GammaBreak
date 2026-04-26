from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_auth_token: str = "change-me"

    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 17

    polygon_api_key: str = ""

    flashalpha_api_key: str = ""
    flashalpha_base_url: str = "https://api.flashalpha.io/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
