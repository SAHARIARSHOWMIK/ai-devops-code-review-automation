from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI DevOps & Code Review Automation Platform"
    app_env: str = "development"
    demo_mode: bool = True
    secret_key: str = "change-this-in-production"
    access_token_expire_minutes: int = 480
    database_url: str = "sqlite:///./devops_review.db"
    redis_url: str = "redis://localhost:6379/0"
    use_celery: bool = True
    frontend_url: str = "http://localhost:5173"

    github_app_id: str | None = None
    github_installation_id: str | None = None
    github_private_key_path: str | None = None
    github_webhook_secret: str = "change-webhook-secret"
    github_api_url: str = "https://api.github.com"

    ai_provider: str = "mock"
    ai_base_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_timeout_seconds: int = 60

    analyzer_timeout_seconds: int = 120
    analyzer_execution_enabled: bool = False
    run_project_tests: bool = False
    max_diff_characters: int = 200_000
    workspace_root: str = "./workspaces"

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore", case_sensitive=False)

    @property
    def workspace_path(self) -> Path:
        path = Path(self.workspace_root).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
