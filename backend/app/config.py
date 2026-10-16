"""Runtime configuration via environment variables. Stdlib only.

Everything defaults to the zero-dependency mock stack so `uvicorn app.main:app` boots with no setup.
Flip STT_PROVIDER / ORCH_PROVIDER to go live.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    db_path: str = os.getenv("AIGLASS_DB", "aiglass.db")

    # If set, every endpoint except /health requires  Authorization: Bearer <token>  (or ?token= on WS).
    # Empty = auth disabled (fine for local/dev; set it in production).
    api_token: str = os.getenv("API_TOKEN", "")

    stt_provider: str = os.getenv("STT_PROVIDER", "mock")        # mock | whisper
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")

    orch_provider: str = os.getenv("ORCH_PROVIDER", "mock")      # mock | hermes
    hermes_url: str = os.getenv("HERMES_URL", "http://127.0.0.1:8080")
    hermes_api_key: str | None = os.getenv("HERMES_API_KEY") or None

    # The /v1/chat/completions shim runs each task via `hermes -z <task>`. Needs the absolute path to the
    # hermes binary (systemd's PATH is minimal). Find it with: which hermes
    hermes_bin: str = os.getenv("HERMES_BIN", "hermes")
    hermes_timeout: float = float(os.getenv("HERMES_TIMEOUT", "120"))

    vision_provider: str = os.getenv("VISION_PROVIDER", "mock")  # mock | llm
    vision_base_url: str = os.getenv("VISION_BASE_URL", "https://api.openai.com/v1")
    vision_api_key: str = os.getenv("VISION_API_KEY", "")
    vision_model: str = os.getenv("VISION_MODEL", "gpt-4o-mini")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")

def load_settings() -> Settings:
    return Settings()


def build_stt(settings: Settings):
    if settings.stt_provider == "whisper":
        from .stt.whisper import WhisperSTT
        return WhisperSTT(model_size=settings.whisper_model)
    from .stt.mock import MockSTT
    return MockSTT()


def build_orchestrator(settings: Settings):
    if settings.orch_provider == "hermes":
        from .orchestrator.hermes import HermesOrchestrator
        return HermesOrchestrator(settings.hermes_url, api_key=settings.hermes_api_key)
    from .orchestrator.mock import MockOrchestrator
    return MockOrchestrator()


def build_vision(settings: Settings):
    if settings.vision_provider == "llm":
        from .vision.llm import LLMVision
        return LLMVision(settings.vision_base_url, settings.vision_api_key, settings.vision_model)
    from .vision.mock import MockVision
    return MockVision()
