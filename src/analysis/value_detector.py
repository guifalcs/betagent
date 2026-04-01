"""Deteccao de apostas de valor com base em probabilidades do modelo e odds."""

from __future__ import annotations

import json
from typing import Any


def _normalize_name(value: str) -> str:
    return value.strip().casefold()


def _implied_prob(odd: float) -> float:
    if odd <= 1.0:
        return 1.0
    return 1.0 / odd


def _best_odds(bookmakers: list[dict[str, Any]], outcome_name: str) -> tuple[float, str]:
    target_name = _normalize_name(outcome_name)
    best_odd = 1.0
    best_bookmaker = ""

    for bookmaker in bookmakers:
        outcomes = bookmaker.get("outcomes", [])
        bookmaker_name = str(bookmaker.get("name", ""))

        for outcome in outcomes:
            current_name = str(outcome.get("name", ""))
            current_odd = float(outcome.get("odds", 1.0))

            if _normalize_name(current_name) != target_name:
                continue

            if current_odd > best_odd:
                best_odd = current_odd
                best_bookmaker = bookmaker_name

    return best_odd, best_bookmaker


def _edge(prob_model: float, odd: float) -> float:
    return prob_model - _implied_prob(odd)


def _kelly_fraction(prob_model: float, odd: float) -> float:
    if odd <= 1.0:
        return 0.0

    kelly = (prob_model * odd - 1.0) / (odd - 1.0)
    if kelly <= 0.0:
        return 0.0
    if kelly >= 1.0:
        return 1.0
    return kelly


def _find_market(markets: list[dict[str, Any]], market_name: str) -> dict[str, Any] | None:
    target_name = _normalize_name(market_name)

    for market in markets:
        current_name = str(market.get("market", ""))
        if _normalize_name(current_name) == target_name:
            return market

    return None


def _build_value_bets(
    outcome_probs: dict[str, float],
    bookmakers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    value_bets: list[dict[str, Any]] = []

    for outcome_name, model_prob in outcome_probs.items():
        best_odd, bookmaker = _best_odds(bookmakers, outcome_name)
        implied_prob = _implied_prob(best_odd)
        edge = _edge(model_prob, best_odd)

        if edge <= 0.0:
            continue

        value_bets.append(
            {
                "outcome": outcome_name,
                "best_odd": best_odd,
                "bookmaker": bookmaker,
                "implied_prob": implied_prob,
                "model_prob": model_prob,
                "edge": edge,
                "kelly_fraction": _kelly_fraction(model_prob, best_odd),
            }
        )

    return value_bets


def run_football(probs: dict[str, Any], event: dict[str, Any]) -> dict[str, Any] | None:
    try:
        home_team = str(event["home_team"])
        away_team = str(event["away_team"])
        markets = event.get("markets", [])

        h2h_market = _find_market(markets, "h2h")
        if h2h_market is None:
            print("[BetAgent][value] Mercado h2h nao encontrado para futebol")
            return None

        outcome_probs = {
            home_team: float(probs["home_win_prob"]),
            "Draw": float(probs["draw_prob"]),
            away_team: float(probs["away_win_prob"]),
        }

        value_bets = _build_value_bets(
            outcome_probs=outcome_probs,
            bookmakers=list(h2h_market.get("bookmakers", [])),
        )

        return {
            "event_id": str(event["event_id"]),
            "home_team": home_team,
            "away_team": away_team,
            "sport": "football",
            "value_bets": value_bets,
            "method": "value_detection",
        }
    except Exception as exc:
        print(f"[BetAgent][value] Falha em run_football: {exc}")
        return None


def run_mma(probs: dict[str, Any], event: dict[str, Any]) -> dict[str, Any] | None:
    try:
        fighter_a = str(probs["fighter_a_name"])
        fighter_b = str(probs["fighter_b_name"])
        markets = event.get("markets", [])

        h2h_market = _find_market(markets, "h2h")
        if h2h_market is None:
            print("[BetAgent][value] Mercado h2h nao encontrado para MMA")
            return None

        outcome_probs = {
            fighter_a: float(probs["fighter_a_win_prob"]),
            fighter_b: float(probs["fighter_b_win_prob"]),
        }

        value_bets = _build_value_bets(
            outcome_probs=outcome_probs,
            bookmakers=list(h2h_market.get("bookmakers", [])),
        )

        return {
            "event_id": str(event["event_id"]),
            "fighter_a": fighter_a,
            "fighter_b": fighter_b,
            "sport": "mma",
            "value_bets": value_bets,
            "method": "value_detection",
        }
    except Exception as exc:
        print(f"[BetAgent][value] Falha em run_mma: {exc}")
        return None


def run(
    probs: dict[str, Any],
    event: dict[str, Any],
    sport: str = "football",
) -> dict[str, Any] | None:
    try:
        normalized_sport = _normalize_name(sport)

        if normalized_sport == "football":
            return run_football(probs=probs, event=event)

        if normalized_sport == "mma":
            return run_mma(probs=probs, event=event)

        print(f"[BetAgent][value] Esporte nao suportado: {sport}")
        return None
    except Exception as exc:
        print(f"[BetAgent][value] Falha em run: {exc}")
        return None


if __name__ == "__main__":
    football_probs: dict[str, Any] = {
        "home_win_prob": 0.55,
        "draw_prob": 0.25,
        "away_win_prob": 0.20,
        "method": "synthetic_fixture",
    }
    football_event: dict[str, Any] = {
        "event_id": "football-001",
        "sport": "football",
        "home_team": "Flamengo",
        "away_team": "Palmeiras",
        "markets": [
            {
                "market": "h2h",
                "bookmakers": [
                    {
                        "name": "Book A",
                        "outcomes": [
                            {"name": "Flamengo", "odds": 2.05},
                            {"name": "Draw", "odds": 3.80},
                            {"name": "Palmeiras", "odds": 4.60},
                        ],
                    },
                    {
                        "name": "Book B",
                        "outcomes": [
                            {"name": "Flamengo", "odds": 1.95},
                            {"name": "Draw", "odds": 3.40},
                            {"name": "Palmeiras", "odds": 4.20},
                        ],
                    },
                ],
            }
        ],
    }

    mma_probs: dict[str, Any] = {
        "fighter_a_win_prob": 0.63,
        "fighter_b_win_prob": 0.37,
        "fighter_a_name": "Charles Oliveira",
        "fighter_b_name": "Islam Makhachev",
        "method": "synthetic_fixture",
    }
    mma_event: dict[str, Any] = {
        "event_id": "mma-001",
        "sport": "mma",
        "home_team": "Charles Oliveira",
        "away_team": "Islam Makhachev",
        "markets": [
            {
                "market": "h2h",
                "bookmakers": [
                    {
                        "name": "Book C",
                        "outcomes": [
                            {"name": "Charles Oliveira", "odds": 1.75},
                            {"name": "Islam Makhachev", "odds": 2.35},
                        ],
                    },
                    {
                        "name": "Book D",
                        "outcomes": [
                            {"name": "Charles Oliveira", "odds": 1.68},
                            {"name": "Islam Makhachev", "odds": 2.20},
                        ],
                    },
                ],
            }
        ],
    }

    football_result = run(football_probs, football_event, sport="football")
    mma_result = run(mma_probs, mma_event, sport="mma")

    print(json.dumps(football_result, ensure_ascii=False, indent=2))
    print(json.dumps(mma_result, ensure_ascii=False, indent=2))
