"""Calculo de stake com criterio de Kelly fracionado."""

from __future__ import annotations

import json
import math
from typing import Any

from config.settings import (
    KELLY_FRACTION_GREEN,
    KELLY_FRACTION_YELLOW,
    KELLY_MAX_STAKE_PCT,
    KELLY_MIN_STAKE_PCT,
    KELLY_ROUND_TO,
)


def _round_to_nearest(value: float, nearest: float) -> float:
    """Arredonda um valor para o multiplo mais proximo informado."""
    if nearest <= 0:
        return value
    return math.floor(value / nearest + 0.5) * nearest


def calculate_kelly(
    p_estimated: float,
    odds: float,
    bankroll: float,
    signal: str,
) -> dict[str, float | str]:
    """Calcula a stake recomendada usando Kelly fracionado com limites."""
    try:
        signal_normalized = signal.strip().lower()

        if signal_normalized == "red":
            return {
                "kelly_full_pct": 0.0,
                "kelly_fraction": 0.0,
                "kelly_fractional_pct": 0.0,
                "kelly_capped_pct": 0.0,
                "stake": 0.0,
                "stake_reason": "Sinal vermelho",
            }

        if not (0 < p_estimated < 1) or odds <= 1 or bankroll <= 0:
            return {
                "kelly_full_pct": 0.0,
                "kelly_fraction": 0.0,
                "kelly_fractional_pct": 0.0,
                "kelly_capped_pct": 0.0,
                "stake": 0.0,
                "stake_reason": "Input invalido",
            }

        kelly_full = (p_estimated * odds - 1) / (odds - 1)
        if kelly_full <= 0:
            return {
                "kelly_full_pct": round(kelly_full, 6),
                "kelly_fraction": 0.0,
                "kelly_fractional_pct": 0.0,
                "kelly_capped_pct": 0.0,
                "stake": 0.0,
                "stake_reason": "Kelly negativo",
            }

        fraction = (
            KELLY_FRACTION_GREEN
            if signal_normalized == "green"
            else KELLY_FRACTION_YELLOW
        )
        kelly_fractional = kelly_full * fraction
        kelly_capped = min(kelly_fractional, KELLY_MAX_STAKE_PCT)

        if kelly_capped < KELLY_MIN_STAKE_PCT:
            return {
                "kelly_full_pct": round(kelly_full, 6),
                "kelly_fraction": fraction,
                "kelly_fractional_pct": round(kelly_fractional, 6),
                "kelly_capped_pct": round(kelly_capped, 6),
                "stake": 0.0,
                "stake_reason": "Kelly abaixo do minimo",
            }

        stake_raw = bankroll * kelly_capped
        stake = _round_to_nearest(stake_raw, KELLY_ROUND_TO)
        stake = max(0.0, min(stake, bankroll))

        return {
            "kelly_full_pct": round(kelly_full, 6),
            "kelly_fraction": fraction,
            "kelly_fractional_pct": round(kelly_fractional, 6),
            "kelly_capped_pct": round(kelly_capped, 6),
            "stake": round(stake, 2),
            "stake_reason": "Stake calculada",
        }
    except Exception as exc:
        print(f"[BetAgent][kelly] erro ao calcular Kelly: {exc}")
        return {
            "kelly_full_pct": 0.0,
            "kelly_fraction": 0.0,
            "kelly_fractional_pct": 0.0,
            "kelly_capped_pct": 0.0,
            "stake": 0.0,
            "stake_reason": "Falha no calculo",
        }


def run(
    value_detection: dict[str, Any] | None,
    bankroll: float,
    kelly_scale: float | None,
) -> dict[str, float | str]:
    """Mantem compatibilidade com a interface antiga do modulo."""
    try:
        if not value_detection:
            return {
                "kelly_full_pct": 0.0,
                "kelly_fraction": 0.0,
                "kelly_fractional_pct": 0.0,
                "kelly_capped_pct": 0.0,
                "stake": 0.0,
                "stake_reason": "Input invalido",
            }

        probability_keys = ("p_estimated", "estimated_probability", "probability", "p")
        odds_keys = ("odds", "best_odds", "price")
        signal_keys = ("signal", "value_signal", "classification")

        p_estimated = next(
            (
                float(value_detection[key])
                for key in probability_keys
                if value_detection.get(key) is not None
            ),
            0.0,
        )
        odds = next(
            (
                float(value_detection[key])
                for key in odds_keys
                if value_detection.get(key) is not None
            ),
            0.0,
        )
        signal = next(
            (
                str(value_detection[key])
                for key in signal_keys
                if value_detection.get(key) is not None
            ),
            "yellow",
        )

        result = calculate_kelly(
            p_estimated=p_estimated,
            odds=odds,
            bankroll=bankroll,
            signal=signal,
        )

        if kelly_scale is not None:
            result["kelly_scale"] = float(kelly_scale)

        return result
    except Exception as exc:
        print(f"[BetAgent][kelly] erro no run: {exc}")
        return {
            "kelly_full_pct": 0.0,
            "kelly_fraction": 0.0,
            "kelly_fractional_pct": 0.0,
            "kelly_capped_pct": 0.0,
            "stake": 0.0,
            "stake_reason": "Falha no calculo",
        }


if __name__ == "__main__":
    cenarios = [
        {"p_estimated": 0.62, "odds": 1.92, "bankroll": 100.0, "signal": "green"},
        {"p_estimated": 0.58, "odds": 2.10, "bankroll": 100.0, "signal": "yellow"},
        {"p_estimated": 0.45, "odds": 1.80, "bankroll": 100.0, "signal": "green"},
        {"p_estimated": 0.70, "odds": 1.50, "bankroll": 100.0, "signal": "red"},
        {"p_estimated": 0.62, "odds": 1.92, "bankroll": 20.0, "signal": "green"},
        {"p_estimated": 0.53, "odds": 2.00, "bankroll": 100.0, "signal": "green"},
    ]

    for indice, cenario in enumerate(cenarios, start=1):
        resultado = calculate_kelly(**cenario)
        payload = {
            "cenario": indice,
            **cenario,
            "resultado": resultado,
        }
        print(f"[BetAgent][kelly] {json.dumps(payload, ensure_ascii=False, indent=2)}")
