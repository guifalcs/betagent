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


def _revalidation_status(original_odd: float, current_odd: float) -> str:
    """Classifica o status da revalidacao com base na variacao percentual da odd."""
    variation_pct = (current_odd / original_odd - 1) * 100
    if abs(variation_pct) < 5:
        return "GO"
    if abs(variation_pct) <= 10:
        return "ATENCAO"
    return "NO-GO"


def _print_revalidation_report(
    event_name: str,
    original_odd: float,
    current_odd: float,
    edge: float,
    kelly_result: Any,
) -> None:
    """Imprime um resumo formatado da revalidacao da oportunidade."""
    variation_pct = (current_odd / original_odd - 1) * 100
    status = _revalidation_status(original_odd, current_odd)
    stake = kelly_result.get("stake", 0.0) if isinstance(kelly_result, dict) else 0.0
    emoji = {"GO": "✅", "ATENCAO": "⚠️", "NO-GO": "❌"}.get(status, "❌")

    print(f"[BetAgent] Revalidacao: {event_name}")
    print(f"Odd original (relatorio): {original_odd}")
    print(f"Odd atual:                {current_odd}")
    print(f"Variacao:                 {variation_pct:+.1f}%")
    print(f"Edge recalculado:         {edge:+.1f}%")
    print(f"Kelly recalculado:        R${stake:.2f}")
    print(f"Status:                   {emoji} {status}")


def run(
    event_name: str,
    probs: dict[str, Any],
    bankroll: float = 1000.0,
    kelly_scale: float = 0.25,
    sport: str = "football",
    manual_odd: float | None = None,
    original_odd: float | None = None,
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

        current_odd = manual_odd
        if current_odd is None:
            value_bets = kelly_result.get("value_bets")
            if isinstance(value_bets, list) and value_bets:
                first_value_bet = value_bets[0]
                if isinstance(first_value_bet, dict):
                    odd_value = first_value_bet.get("odd")
                    if isinstance(odd_value, int | float):
                        current_odd = float(odd_value)

        if current_odd is not None and original_odd is not None:
            variation_pct = (current_odd / original_odd - 1) * 100
            edge = value_detection.get("edge", 0.0) if isinstance(value_detection, dict) else 0.0
            edge_value = float(edge) if isinstance(edge, int | float) else 0.0
            _print_revalidation_report(
                event_name=event_name,
                original_odd=original_odd,
                current_odd=current_odd,
                edge=edge_value,
                kelly_result=kelly_result,
            )
            status = _revalidation_status(original_odd, current_odd)
            kelly_result["revalidation_status"] = status
            kelly_result["odd_variation_pct"] = round(variation_pct, 2)

        kelly_result["status"] = "revalidated"

        print("[BetAgent][flow] Fluxo revalidate concluido.")
        return kelly_result
    except Exception as exc:
        print(f"[BetAgent][flow] Falha no fluxo revalidate: {exc}")
        return None


if __name__ == "__main__":
    print("Fluxo revalidate disponível — use via src.main ou importe run().")
