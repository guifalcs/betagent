"""Cálculo de stake em reais usando Kelly fracionado."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

KELLY_FRACTION_DEFAULT: float = 0.25


def _stake(bankroll: float, kelly_fraction: float, kelly_scale: float) -> float:
    """Calcula o valor em reais a ser apostado para uma bet."""
    raw_stake: float = bankroll * kelly_fraction * kelly_scale
    clamped_stake: float = max(0.0, min(raw_stake, bankroll))
    return round(clamped_stake, 2)


def run(
    value_detection: dict[str, Any],
    bankroll: float,
    kelly_scale: float = KELLY_FRACTION_DEFAULT,
) -> dict[str, Any] | None:
    """Enriquece value bets com stake em reais calculado via Kelly fracionado."""
    try:
        if bankroll <= 0:
            print("[BetAgent][kelly] bankroll inválido para cálculo de stake")
            return None

        if kelly_scale < 0:
            print("[BetAgent][kelly] kelly_scale inválido para cálculo de stake")
            return None

        value_bets_raw: Any = value_detection.get("value_bets")
        if not isinstance(value_bets_raw, list):
            print("[BetAgent][kelly] value_bets ausente ou inválido")
            return None

        enriched_detection: dict[str, Any] = deepcopy(value_detection)
        enriched_bets: list[dict[str, Any]] = []
        total_exposure: float = 0.0

        for bet_raw in value_bets_raw:
            if not isinstance(bet_raw, dict):
                print("[BetAgent][kelly] value_bet inválida encontrada")
                return None

            bet: dict[str, Any] = deepcopy(bet_raw)
            bet_kelly_fraction: Any = bet.get("kelly_fraction")
            if bet_kelly_fraction is None:
                print("[BetAgent][kelly] kelly_fraction ausente em value_bet")
                return None

            stake_reais: float = _stake(
                bankroll=float(bankroll),
                kelly_fraction=float(bet_kelly_fraction),
                kelly_scale=float(kelly_scale),
            )
            bet["stake_reais"] = stake_reais
            total_exposure += stake_reais
            enriched_bets.append(bet)

        total_exposure = round(total_exposure, 2)
        exposure_pct: float = round((total_exposure / bankroll) * 100, 2)

        enriched_detection["value_bets"] = enriched_bets
        enriched_detection["bankroll"] = round(float(bankroll), 2)
        enriched_detection["kelly_scale"] = round(float(kelly_scale), 4)
        enriched_detection["total_exposure"] = total_exposure
        enriched_detection["exposure_pct"] = exposure_pct

        print(
            "[BetAgent][kelly] cálculo concluído "
            f"para event_id={enriched_detection.get('event_id')} "
            f"com exposição total de R$ {total_exposure:.2f}"
        )
        return enriched_detection
    except Exception as exc:
        print(f"[BetAgent][kelly] falha ao calcular stakes: {exc}")
        return None


if __name__ == "__main__":
    football_value_detection: dict[str, Any] = {
        "event_id": "football-001",
        "home_team": "Flamengo",
        "away_team": "Palmeiras",
        "sport": "football",
        "value_bets": [
            {
                "outcome": "home_win",
                "best_odd": 2.15,
                "bookmaker": "Book A",
                "implied_prob": 0.4651,
                "model_prob": 0.53,
                "edge": 0.0649,
                "kelly_fraction": 0.12,
            },
            {
                "outcome": "over_2_5",
                "best_odd": 1.95,
                "bookmaker": "Book B",
                "implied_prob": 0.5128,
                "model_prob": 0.58,
                "edge": 0.0672,
                "kelly_fraction": 0.08,
            },
        ],
        "method": "ensemble_poisson",
    }

    mma_value_detection: dict[str, Any] = {
        "event_id": "mma-001",
        "fighter_a": "Charles Oliveira",
        "fighter_b": "Islam Makhachev",
        "sport": "mma",
        "value_bets": [
            {
                "outcome": "fighter_a_win",
                "best_odd": 2.75,
                "bookmaker": "Book C",
                "implied_prob": 0.3636,
                "model_prob": 0.42,
                "edge": 0.0564,
                "kelly_fraction": 0.07,
            }
        ],
        "method": "elo_mma_v1",
    }

    scenarios: list[tuple[str, dict[str, Any], float, float]] = [
        (
            "football_default",
            football_value_detection,
            1000.00,
            KELLY_FRACTION_DEFAULT,
        ),
        ("football_half_kelly", football_value_detection, 1000.00, 0.5),
        ("mma_default", mma_value_detection, 500.00, KELLY_FRACTION_DEFAULT),
        ("mma_half_kelly", mma_value_detection, 500.00, 0.5),
    ]

    for scenario_name, detection, bankroll_value, scale in scenarios:
        result: dict[str, Any] | None = run(
            value_detection=detection,
            bankroll=bankroll_value,
            kelly_scale=scale,
        )
        print(f"[BetAgent][kelly] cenário={scenario_name}")
        print(
            json.dumps(
                {
                    "scenario": scenario_name,
                    "result": result,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
