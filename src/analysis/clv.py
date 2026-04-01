from __future__ import annotations

import json


def calculate_clv(bet_odds: float, closing_odds: float) -> dict:
    """Calcula o Closing Line Value de uma aposta com base na odd apostada e na odd de fechamento."""
    try:
        if bet_odds <= 1.0 or closing_odds <= 1.0:
            print(
                "[BetAgent][clv] Odds invalidas para calculo: "
                f"bet_odds={bet_odds}, closing_odds={closing_odds}"
            )
            return {"clv_pct": 0.0, "beat_closing": False}

        clv_pct = round((bet_odds / closing_odds - 1) * 100, 2)
        beat_closing = clv_pct > 0
        result = {"clv_pct": clv_pct, "beat_closing": beat_closing}
        print(f"[BetAgent][clv] Resultado calculado: {result}")
        return result
    except Exception as exc:
        print(f"[BetAgent][clv] Falha ao calcular CLV: {exc}")
        return {"clv_pct": 0.0, "beat_closing": False}


if __name__ == "__main__":
    scenarios = [
        {"bet_odds": 1.92, "closing_odds": 1.80},
        {"bet_odds": 1.75, "closing_odds": 1.90},
        {"bet_odds": 2.10, "closing_odds": 2.10},
    ]

    for scenario in scenarios:
        result = calculate_clv(
            bet_odds=scenario["bet_odds"],
            closing_odds=scenario["closing_odds"],
        )
        print(
            json.dumps(
                {
                    **scenario,
                    **result,
                },
                ensure_ascii=True,
                indent=2,
            )
        )
