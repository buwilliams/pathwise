from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    pathwise_data_dir: Path = Field(default=Path("./data"))
    pathwise_host: str = "0.0.0.0"
    pathwise_port: int = 8000

    pathwise_otp_ttl_seconds: int = 600
    pathwise_otp_max_per_hour: int = 3
    pathwise_otp_max_verify_attempts: int = 5

    pathwise_session_ttl_seconds: int = 60 * 60 * 24 * 30

    pathwise_plan_model: str = "claude-opus-4-7"
    pathwise_research_model: str = "claude-opus-4-7"
    # Chat uses Sonnet for snappy back-and-forth — quality is plenty since the
    # full essay + plan + life-state are pinned in the cached system prompt.
    pathwise_chat_model: str = "claude-sonnet-4-6"

    @property
    def data_dir(self) -> Path:
        return self.pathwise_data_dir

    @property
    def users_dir(self) -> Path:
        return self.data_dir / "users"

    @property
    def auth_dir(self) -> Path:
        return self.data_dir / "auth"

    @property
    def otp_dir(self) -> Path:
        return self.auth_dir / "otp"

    @property
    def sessions_dir(self) -> Path:
        return self.auth_dir / "sessions"

    @property
    def twilio_enabled(self) -> bool:
        return bool(
            self.twilio_account_sid
            and self.twilio_auth_token
            and self.twilio_from_number
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
