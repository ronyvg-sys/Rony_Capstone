"""W6 application settings."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration for the W6 RAG application."""

    questions_csv: Path = Path("data/questions.csv")
    results_json: Path = Path("results.json")
    results_db: Path = Path("results.db")

    batch_size: int = Field(5, gt=0, le=20)
    fail_rate: float = Field(0.0, ge=0.0, le=1.0)

    model: str = "gpt-4o-mini"
    use_fake: bool = False

    # Read the API key from the environment.
    # Never store the actual key in source code.
    openai_api_key: str = Field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )

    max_retries: int = 3
    retry_delay_s: float = 1.0
