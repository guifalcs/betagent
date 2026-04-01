from __future__ import annotations

from datetime import date
from typing import Any

from src.analysis import kelly, probability_engine, value_detector
from src.collectors import odds_collector, stats_collector


def _normalize_name(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def _first_non_empty(mapping: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = mapping.get(key)
        normalized = _normalize_name(value)
        if normalized:
            return normalized
    return ""


def _extract_football_teams(item: dict[str, Any]) -> tuple[str, str]:
    home = _first_non_empty(
        item,
        [
            "home_team",
            "home",
            "team_home",
            "team1",
            "participant_home",
        ],
    )
    away = _first_non_empty(
        item,
        [
            "away_team",
            "away",
            "team_away",
            "team2",
            "participant_away",
        ],
    )
    return home, away


def _extract_mma_fighters(item: dict[str, Any]) -> tuple[str, str]:
    fighter_a = _first_non_empty(
        item,
        [
            "fighter_a",
            "fighter1",
            "fighter_red",
            "home_fighter",
            "home",
            "participant_1",
            "participant1",
        ],
    )
    fighter_b = _first_non_empty(
        item,
        [
            "fighter_b",
            "fighter2",
            "fighter_blue",
            "away_fighter",
            "away",
            "participant_2",
            "participant2",
        ],
    )
    return fighter_a, fighter_b


def _find_matching_event(
    odds_events: list[dict[str, Any]],
    target_a: str,
    target_b: str,
    sport: str,
) -> dict[str, Any] | None:
    if not target_a or not target_b:
        return None

    for event in odds_events:
        if not isinstance(event, dict):
            continue

        if sport == "football":
            event_a, event_b = _extract_football_teams(event)
        else:
            event_a, event_b = _extract_mma_fighters(event)

        if not event_a or not event_b:
            continue

        same_order = event_a == target_a and event_b == target_b
        reversed_order = event_a == target_b and event_b == target_a
        if same_order or reversed_order:
            return event

    return None


def _extract_stats_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in ("fixtures", "events", "matches", "fights", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def _process_football(
    odds_events: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    bankroll: float,
    kelly_scale: float,
) -> list[dict[str, Any]]:
    opportunities: list[dict[str, Any]] = []

    for fixture in fixtures:
        home_team, away_team = _extract_football_teams(fixture)
        event = _find_matching_event(odds_events, home_team, away_team, "football")

        probs = probability_engine.run(fixture, "football")
        if probs is None:
            continue

        if event is None:
            continue

        value_detection = value_detector.run(probs, event, "football")
        if value_detection is None:
            continue

        kelly_result = kelly.run(value_detection, bankroll, kelly_scale)
        if not isinstance(kelly_result, dict):
            continue

        value_bets = kelly_result.get("value_bets")
        if isinstance(value_bets, list) and value_bets:
            opportunities.append(kelly_result)

    return opportunities


def _process_mma(
    odds_events: list[dict[str, Any]],
    fights: list[dict[str, Any]],
    bankroll: float,
    kelly_scale: float,
) -> list[dict[str, Any]]:
    opportunities: list[dict[str, Any]] = []

    for fight in fights:
        fighter_a, fighter_b = _extract_mma_fighters(fight)
        event = _find_matching_event(odds_events, fighter_a, fighter_b, "mma")

        probs = probability_engine.run(fight, "mma")
        if probs is None:
            continue

        if event is None:
            continue

        value_detection = value_detector.run(probs, event, "mma")
        if value_detection is None:
            continue

        kelly_result = kelly.run(value_detection, bankroll, kelly_scale)
        if not isinstance(kelly_result, dict):
            continue

        value_bets = kelly_result.get("value_bets")
        if isinstance(value_bets, list) and value_bets:
            opportunities.append(kelly_result)

    return opportunities


def run(bankroll: float = 1000.0, kelly_scale: float = 0.25) -> dict[str, Any] | None:
    try:
        print("[BetAgent][flow] Iniciando fluxo daily_report.")

        odds_payload = odds_collector.run()
        football_stats = stats_collector.run("football")
        mma_stats = stats_collector.run("mma")

        odds_events = _extract_stats_items(odds_payload)
        football_fixtures = _extract_stats_items(football_stats)
        mma_fights = _extract_stats_items(mma_stats)

        football_opportunities = _process_football(
            odds_events=odds_events,
            fixtures=football_fixtures,
            bankroll=bankroll,
            kelly_scale=kelly_scale,
        )
        mma_opportunities = _process_mma(
            odds_events=odds_events,
            fights=mma_fights,
            bankroll=bankroll,
            kelly_scale=kelly_scale,
        )

        result: dict[str, Any] = {
            "date": date.today().isoformat(),
            "football_opportunities": football_opportunities,
            "mma_opportunities": mma_opportunities,
            "total_opportunities": len(football_opportunities) + len(mma_opportunities),
            "bankroll": bankroll,
            "kelly_scale": kelly_scale,
        }

        print("[BetAgent][flow] Fluxo daily_report concluido.")
        return result
    except Exception as exc:
        print(f"[BetAgent][flow] Falha no fluxo daily_report: {exc}")
        return None


if __name__ == "__main__":
    print("Fluxo daily_report disponível — use via src.main ou importe run().")
