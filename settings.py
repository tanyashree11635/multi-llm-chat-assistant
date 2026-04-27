"""Application settings using pydantic BaseModel and environment variables.

This module intentionally avoids the `pydantic-settings` package to keep
import-time dependencies minimal. It reads a `.env` file (if present) using
python-dotenv, then uses pydantic for validation.
"""
from functools import lru_cache
from typing import Optional
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


# Load .env if present
load_dotenv()


class AppSettings(BaseModel):
	"""Application configuration loaded from environment variables.

	To use, set environment variables or create a `.env` file at the project
	root (an example file is provided as `.env.example`).
	"""

	openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
	gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))

	app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "llm_chatbot"))
	app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
	debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "true").lower() in ("1", "true", "yes"))
	log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

	# Provider-specific settings
	openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))
	gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))
	default_provider: str = Field(default_factory=lambda: os.getenv("DEFAULT_PROVIDER", "openai"))
	max_response_tokens: int = Field(default_factory=lambda: int(os.getenv("MAX_RESPONSE_TOKENS", "512")))

	admin_email: Optional[str] = Field(default_factory=lambda: os.getenv("ADMIN_EMAIL"))
	telemetry_endpoint: Optional[str] = Field(default_factory=lambda: os.getenv("TELEMETRY_ENDPOINT"))

	@validator("app_env")
	def validate_app_env(cls, v: str) -> str:
		allowed = {"development", "staging", "production"}
		v_lower = v.lower()
		if v_lower not in allowed:
			raise ValueError(f"APP_ENV must be one of {allowed}, got '{v}'")
		return v_lower

	@validator("log_level")
	def validate_log_level(cls, v: str) -> str:
		allowed = {"debug", "info", "warning", "error", "critical"}
		v_lower = v.lower()
		if v_lower not in allowed:
			raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
		return v_lower

	@validator("max_response_tokens")
	def validate_max_tokens(cls, v: int) -> int:
		if v <= 0 or v > 100000:
			raise ValueError("MAX_RESPONSE_TOKENS must be positive and reasonably bounded")
		return v

	@validator("openai_model", "gemini_model")
	def normalize_model_name(cls, v: str) -> str:
		return v.strip()

	@validator("default_provider")
	def validate_provider(cls, v: str) -> str:
		allowed = {"openai", "gemini"}
		v_lower = v.lower()
		if v_lower not in allowed:
			raise ValueError(f"default_provider must be one of {allowed}, got '{v}'")
		return v_lower

	def require_any_api_key(self) -> None:
		if not (self.openai_api_key or self.gemini_api_key):
			raise RuntimeError("No LLM API key configured. Provide OPENAI_API_KEY or GEMINI_API_KEY.")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
	return AppSettings()


__all__ = ["AppSettings", "get_settings"]

