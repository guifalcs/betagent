"""Helpers de normalizacao para dados brutos de APIs externas."""

from __future__ import annotations

import re


_NUMERIC_CHARS_PATTERN: re.Pattern[str] = re.compile(r"[^0-9.\-]+")
_RECORD_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*(\d+)\s*[-/]\s*(\d+)(?:\s*[-/]\s*(\d+))?\s*$"
)
_LOG_PREFIX: str = "[BetAgent][normalizers]"


def safe_float(value: str | int | float | None, default: float = 0.0) -> float:
    """Converte valores numericos diversos para ``float`` com fallback seguro."""
    try:
        if value is None:
            return default

        if isinstance(value, (int, float)):
            return float(value)

        cleaned_value: str = _NUMERIC_CHARS_PATTERN.sub("", value)
        if not cleaned_value or cleaned_value in {"-", ".", "-."}:
            return default

        return float(cleaned_value)
    except (TypeError, ValueError):
        return default


def safe_int(value: str | int | float | None, default: int = 0) -> int:
    """Converte valores numericos diversos para ``int`` via ``safe_float``."""
    try:
        return int(safe_float(value, float(default)))
    except (TypeError, ValueError, OverflowError):
        return default


def normalize_pct(value: str | int | float | None, default: float = 0.0) -> float:
    """Normaliza porcentagens para decimal no intervalo de 0.0 a 1.0."""
    try:
        numeric_value: float = safe_float(value, default)
        if numeric_value < 0.0 or numeric_value > 100.0:
            return default
        if numeric_value > 1.0:
            return numeric_value / 100.0
        return numeric_value
    except (TypeError, ValueError):
        return default


def parse_record(
    record_str: str | int | float | None,
    default: tuple[int, int, int] = (0, 0, 0),
) -> tuple[int, int, int]:
    """Faz parse de records MMA em formatos como ``21-4-0`` ou ``21/4``."""
    try:
        if record_str is None:
            return default

        match: re.Match[str] | None = _RECORD_PATTERN.match(str(record_str))
        if match is None:
            return default

        wins: int = int(match.group(1))
        losses: int = int(match.group(2))
        draws: int = int(match.group(3) or 0)
        return wins, losses, draws
    except (TypeError, ValueError):
        return default


if __name__ == "__main__":
    assert safe_float("R$1.92", 0.0) == 1.92
    assert safe_float(None, 0.0) == 0.0
    assert safe_int("42abc", 0) == 42
    assert normalize_pct(65.4) == 0.654
    assert normalize_pct(0.654) == 0.654
    assert normalize_pct("65.4%") == 0.654
    assert normalize_pct(-5.0) == 0.0
    assert parse_record("21-4-0") == (21, 4, 0)
    assert parse_record("21-4") == (21, 4, 0)
    assert parse_record("invalid") == (0, 0, 0)

    print(f"{_LOG_PREFIX} Todos os testes passaram.")
