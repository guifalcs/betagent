from __future__ import annotations

import copy
import json
from typing import Any


def _normalize_text(value: str | None) -> str:
    """Normaliza textos para comparacoes case-insensitive."""
    return (value or "").strip().lower()


def _build_match_label(bet: dict[str, Any]) -> str | None:
    """Monta o rotulo do evento com base no esporte."""
    try:
        sport = _normalize_text(str(bet.get("sport", "")))

        if sport == "football":
            home_team = str(bet.get("home_team", "")).strip()
            away_team = str(bet.get("away_team", "")).strip()
            if home_team and away_team:
                return f"{home_team} vs {away_team}"

        if sport == "ufc":
            fighter_a = str(bet.get("fighter_a", "")).strip()
            fighter_b = str(bet.get("fighter_b", "")).strip()
            if fighter_a and fighter_b:
                return f"{fighter_a} vs {fighter_b}"

        return None
    except Exception as exc:
        print(f"[BetAgent][postmortem] erro ao montar match_label: {exc}")
        return None


def _find_matching_result(
    bet: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Encontra o resultado correspondente para a aposta."""
    try:
        match_label = _build_match_label(bet)
        if not match_label:
            return None

        normalized_match = _normalize_text(match_label)
        normalized_sport = _normalize_text(str(bet.get("sport", "")))

        for result in results:
            result_match = _normalize_text(str(result.get("match", "")))
            result_sport = _normalize_text(str(result.get("sport", "")))

            if result_match == normalized_match and result_sport == normalized_sport:
                return result

        return None
    except Exception as exc:
        print(f"[BetAgent][postmortem] erro ao buscar resultado correspondente: {exc}")
        return None


def _match_result(bet_outcome: str, result: dict[str, Any]) -> bool | None:
    """Verifica se o outcome da aposta corresponde ao vencedor real."""
    try:
        normalized_outcome = _normalize_text(bet_outcome)
        normalized_winner = _normalize_text(str(result.get("winner", "")))

        if not normalized_outcome or not normalized_winner:
            return None

        if normalized_outcome == "draw" and normalized_winner == "draw":
            return True

        return normalized_outcome == normalized_winner
    except Exception as exc:
        print(f"[BetAgent][postmortem] erro ao comparar resultado: {exc}")
        return None


def _pnl(won: bool, stake: float, odd: float) -> float | None:
    """Calcula lucro/prejuizo da aposta."""
    try:
        if won:
            return round(stake * (odd - 1), 2)
        return round(-stake, 2)
    except Exception as exc:
        print(f"[BetAgent][postmortem] erro ao calcular pnl: {exc}")
        return None


def run(
    bets: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Cruza apostas com resultados reais e calcula performance."""
    try:
        enriched_bets = copy.deepcopy(bets)

        total_bets = 0
        won_bets = 0
        lost_bets = 0
        unmatched_bets = 0
        total_staked = 0.0
        total_pnl = 0.0

        for bet in enriched_bets:
            matched_result = _find_matching_result(bet, results)
            matched_result_text = (
                str(matched_result.get("result")).strip() if matched_result else None
            )

            value_bets = bet.get("value_bets", [])
            if not isinstance(value_bets, list):
                print("[BetAgent][postmortem] value_bets invalido, ignorando registro")
                continue

            for value_bet in value_bets:
                if not isinstance(value_bet, dict):
                    print("[BetAgent][postmortem] value_bet invalido, ignorando item")
                    continue

                total_bets += 1

                stake = float(value_bet.get("stake_reais", 0.0) or 0.0)
                odd = float(value_bet.get("best_odd", 0.0) or 0.0)
                total_staked += stake

                won: bool | None = None
                pnl_reais = 0.0

                if matched_result:
                    won = _match_result(str(value_bet.get("outcome", "")), matched_result)

                    if won is None:
                        unmatched_bets += 1
                    else:
                        pnl_value = _pnl(won, stake, odd)
                        pnl_reais = pnl_value if pnl_value is not None else 0.0
                        total_pnl += pnl_reais

                        if won:
                            won_bets += 1
                        else:
                            lost_bets += 1
                else:
                    unmatched_bets += 1

                value_bet["won"] = won
                value_bet["pnl_reais"] = round(pnl_reais, 2)
                value_bet["matched_result"] = matched_result_text

        total_staked = round(total_staked, 2)
        total_pnl = round(total_pnl, 2)
        roi_pct = round((total_pnl / total_staked * 100), 2) if total_staked > 0 else 0.0
        decided_bets = won_bets + lost_bets
        accuracy = round((won_bets / decided_bets), 4) if decided_bets > 0 else 0.0

        return {
            "bets": enriched_bets,
            "metrics": {
                "total_bets": total_bets,
                "won_bets": won_bets,
                "lost_bets": lost_bets,
                "unmatched_bets": unmatched_bets,
                "total_staked": total_staked,
                "total_pnl": total_pnl,
                "roi_pct": roi_pct,
                "accuracy": accuracy,
            },
            "method": "post_mortem",
        }
    except Exception as exc:
        print(f"[BetAgent][postmortem] erro ao executar post mortem: {exc}")
        return None


if __name__ == "__main__":
    synthetic_bets: list[dict[str, Any]] = [
        {
            "event_id": "fb-001",
            "home_team": "Flamengo",
            "away_team": "Palmeiras",
            "fighter_a": "",
            "fighter_b": "",
            "sport": "football",
            "value_bets": [
                {
                    "outcome": "Flamengo",
                    "best_odd": 2.1,
                    "bookmaker": "Bet365",
                    "model_prob": 0.54,
                    "edge": 0.08,
                    "kelly_fraction": 0.04,
                    "stake_reais": 100.0,
                }
            ],
            "bankroll": 1000.0,
            "kelly_scale": 0.5,
            "total_exposure": 100.0,
        },
        {
            "event_id": "ufc-001",
            "home_team": "",
            "away_team": "",
            "fighter_a": "Charles Oliveira",
            "fighter_b": "Islam Makhachev",
            "sport": "ufc",
            "value_bets": [
                {
                    "outcome": "Islam Makhachev",
                    "best_odd": 1.8,
                    "bookmaker": "Pinnacle",
                    "model_prob": 0.62,
                    "edge": 0.05,
                    "kelly_fraction": 0.03,
                    "stake_reais": 120.0,
                }
            ],
            "bankroll": 1000.0,
            "kelly_scale": 0.5,
            "total_exposure": 120.0,
        },
        {
            "event_id": "fb-002",
            "home_team": "Santos",
            "away_team": "Corinthians",
            "fighter_a": "",
            "fighter_b": "",
            "sport": "football",
            "value_bets": [
                {
                    "outcome": "Draw",
                    "best_odd": 3.2,
                    "bookmaker": "Betano",
                    "model_prob": 0.35,
                    "edge": 0.04,
                    "kelly_fraction": 0.02,
                    "stake_reais": 80.0,
                }
            ],
            "bankroll": 1000.0,
            "kelly_scale": 0.5,
            "total_exposure": 80.0,
        },
    ]

    synthetic_results: list[dict[str, Any]] = [
        {
            "sport": "football",
            "competition": "Brasileirao",
            "match": "Flamengo vs Palmeiras",
            "event_date": "2026-03-28",
            "result": "Flamengo venceu por 2x1",
            "winner": "Flamengo",
            "method": None,
        },
        {
            "sport": "ufc",
            "competition": "UFC 310",
            "match": "Charles Oliveira vs Islam Makhachev",
            "event_date": "2026-03-29",
            "result": "Islam Makhachev venceu por decisao",
            "winner": "Islam Makhachev",
            "method": "Decision",
        },
        {
            "sport": "football",
            "competition": "Brasileirao",
            "match": "Santos vs Corinthians",
            "event_date": "2026-03-30",
            "result": "Corinthians venceu por 1x0",
            "winner": "Corinthians",
            "method": None,
        },
    ]

    output = run(synthetic_bets, synthetic_results)
    print(json.dumps(output, indent=2, ensure_ascii=False))
