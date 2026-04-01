from __future__ import annotations

from typing import Any

from src.analysis import kelly, value_detector
from src.collectors import odds_collector


def _normalize_name(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def _event_label(event: dict[str, Any]) -> str:
    for key in ("event_name", "name", "label", "match_name", "title"):
        label = _normalize_name(event.get(key))
        if label:
            return label

    participants: list[str] = []
    for key in (
        "home_team",
        "away_team",
        "fighter_a",
        "fighter_b",
        "team1",
        "team2",
        "home",
        "away",
    ):
        value = _normalize_name(event.get(key))
        if value:
            participants.append(value)

    return " ".join(participants).strip()


def _extract_events(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in ("events", "data", "items", "fixtures", "matches"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def _find_event_by_name(events: list[dict[str, Any]], event_name: str) -> dict[str, Any] | None:
    target = _normalize_name(event_name)
    if not target:
        return None

    for event in events:
        label = _event_label(event)
        if not label:
            continue
        if target in label or label in target:
            return event

    return None


def run(
    event_name: str,
    probs: dict[str, Any],
    bankroll: float = 1000.0,
    kelly_scale: float = 0.25,
    sport: str = "football",
) -> dict[str, Any] | None:
    try:
        print("[BetAgent][flow] Iniciando fluxo revalidate.")

        odds_payload = odds_collector.run()
        events = _extract_events(odds_payload)
        event = _find_event_by_name(events, event_name)

        if event is None:
            return {
                "event": event_name,
                "status": "not_found",
                "value_bets": [],
            }

        value_detection = value_detector.run(probs, event, sport)
        if value_detection is None:
            return None

        kelly_result = kelly.run(value_detection, bankroll, kelly_scale)
        if not isinstance(kelly_result, dict):
            return None

        kelly_result["status"] = "revalidated"

        print("[BetAgent][flow] Fluxo revalidate concluido.")
        return kelly_result
    except Exception as exc:
        print(f"[BetAgent][flow] Falha no fluxo revalidate: {exc}")
        return None


if __name__ == "__main__":
    print("Fluxo revalidate disponível — use via src.main ou importe run().")
