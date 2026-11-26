"""Configuration: repo location, env settings, and YAML config loading."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


def home() -> Path:
    """Project root. Override with SR_HOME for installed use."""
    env = os.getenv("SR_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    d = home() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def reports_dir() -> Path:
    d = home() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(home() / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    github_token: str = ""
    database_url: str = "sqlite:///data/startup_radar.db"
    llm_enabled: bool = False
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    google_service_account_json: str = ""
    notion_token: str = ""
    notion_parent_page_id: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


CONFIG_NAMES = ("profile", "sources", "scoring", "schedule", "llm")


@lru_cache
def load_config() -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    for name in CONFIG_NAMES:
        path = home() / "config" / f"{name}.yaml"
        cfg[name] = yaml.safe_load(path.read_text()) if path.exists() else {}
    return cfg


def profile() -> dict[str, Any]:
    return load_config().get("profile") or {}


def sources() -> dict[str, Any]:
    return load_config().get("sources") or {}


def scoring() -> dict[str, Any]:
    return load_config().get("scoring") or {}


def llm() -> dict[str, Any]:
    return load_config().get("llm") or {}
