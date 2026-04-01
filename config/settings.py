"""Carrega variaveis de ambiente do projeto a partir de um arquivo .env."""

from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


def _get_required_env(name: str) -> str:
    """Retorna uma variavel obrigatoria do ambiente ou levanta erro claro."""
    value = os.environ.get(name)
    if value:
        return value
    raise EnvironmentError(f"Variavel de ambiente obrigatoria ausente: {name}")


def _get_optional_env(name: str) -> str | None:
    """Retorna uma variavel opcional do ambiente quando disponivel."""
    return os.environ.get(name)


SUPABASE_URL: str = _get_required_env("SUPABASE_URL")
SUPABASE_KEY: str = _get_required_env("SUPABASE_KEY")
ODDS_API_KEY: str | None = _get_optional_env("ODDS_API_KEY")
API_FOOTBALL_KEY: str | None = _get_optional_env("API_FOOTBALL_KEY")
APIFY_TOKEN: str | None = _get_optional_env("APIFY_TOKEN")
N8N_WEBHOOK_URL: str | None = _get_optional_env("N8N_WEBHOOK_URL")
TELEGRAM_BOT_TOKEN: str | None = _get_optional_env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID: str | None = _get_optional_env("TELEGRAM_CHAT_ID")
KELLY_FRACTION_GREEN: float = 0.50
KELLY_FRACTION_YELLOW: float = 0.25
KELLY_MAX_STAKE_PCT: float = 0.05
KELLY_MIN_STAKE_PCT: float = 0.01
KELLY_ROUND_TO: float = 0.50
