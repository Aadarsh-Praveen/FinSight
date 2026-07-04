"""Loads env vars, model IDs, dataset names. No secrets in code."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, model_validator

load_dotenv()

REQUIRED_VARS = [
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_GENAI_USE_VERTEXAI",
    "BIGQUERY_PROJECT",
    "BIGQUERY_DATASET",
    "MODEL_ROUTER",
    "MODEL_WORKER",
    "MODEL_VERIFIER",
    "TOOLBOX_URL",
]


class Settings(BaseModel):
    google_cloud_project: str
    google_cloud_location: str
    google_genai_use_vertexai: bool
    google_api_key: str | None = None
    bigquery_project: str
    bigquery_dataset: str
    model_router: str
    model_worker: str
    model_verifier: str
    toolbox_url: str
    enable_tracing: bool = False
    enable_verifier: bool = True
    """Whether the orchestrator's retry loop includes the verifier critic. Toggle for the
    Phase 9 with-verifier vs. without-verifier ablation; build_orchestrator_agent() also accepts
    an explicit override so eval/ablation.py can construct both variants in one process without
    touching the environment."""

    @model_validator(mode="after")
    def _require_api_key_for_ai_studio(self) -> Settings:
        if not self.google_genai_use_vertexai and not self.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY is required when GOOGLE_GENAI_USE_VERTEXAI is FALSE"
            )
        return self


def _bool_from_env(name: str, default: str = "FALSE") -> bool:
    return os.getenv(name, default).strip().upper() in {"TRUE", "1", "YES"}


def load_settings() -> Settings:
    """Builds `Settings` from environment variables, failing loudly (not with a downstream
    AttributeError) if any required variable is missing. See README.md's "Configuration /
    Environment Variables" section for the full list and what each one does.
    """
    missing = [name for name in REQUIRED_VARS if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Missing required environment variable(s): "
            f"{', '.join(missing)}. See README.md's Configuration section and create a .env file."
        )
    try:
        return Settings(
            google_cloud_project=os.environ["GOOGLE_CLOUD_PROJECT"],
            google_cloud_location=os.environ["GOOGLE_CLOUD_LOCATION"],
            google_genai_use_vertexai=_bool_from_env("GOOGLE_GENAI_USE_VERTEXAI"),
            google_api_key=os.getenv("GOOGLE_API_KEY") or None,
            bigquery_project=os.environ["BIGQUERY_PROJECT"],
            bigquery_dataset=os.environ["BIGQUERY_DATASET"],
            model_router=os.environ["MODEL_ROUTER"],
            model_worker=os.environ["MODEL_WORKER"],
            model_verifier=os.environ["MODEL_VERIFIER"],
            toolbox_url=os.environ["TOOLBOX_URL"],
            enable_tracing=_bool_from_env("ENABLE_TRACING"),
            enable_verifier=_bool_from_env("ENABLE_VERIFIER", default="TRUE"),
        )
    except ValidationError as exc:
        raise RuntimeError(f"Invalid configuration: {exc}") from exc


settings = load_settings()


def _print_settings() -> None:
    print("FinSight resolved settings:")
    print(f"  GOOGLE_CLOUD_PROJECT      = {settings.google_cloud_project}")
    print(f"  GOOGLE_CLOUD_LOCATION     = {settings.google_cloud_location}")
    print(f"  GOOGLE_GENAI_USE_VERTEXAI = {settings.google_genai_use_vertexai}")
    key_status = "<set>" if settings.google_api_key else "<not set>"
    print(f"  GOOGLE_API_KEY            = {key_status}")
    print(f"  BIGQUERY_PROJECT          = {settings.bigquery_project}")
    print(f"  BIGQUERY_DATASET          = {settings.bigquery_dataset}")
    print(f"  MODEL_ROUTER              = {settings.model_router}")
    print(f"  MODEL_WORKER              = {settings.model_worker}")
    print(f"  MODEL_VERIFIER            = {settings.model_verifier}")
    print(f"  TOOLBOX_URL               = {settings.toolbox_url}")
    print(f"  ENABLE_TRACING            = {settings.enable_tracing}")
    print(f"  ENABLE_VERIFIER           = {settings.enable_verifier}")


if __name__ == "__main__":
    _print_settings()
