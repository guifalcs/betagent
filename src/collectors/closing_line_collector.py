from __future__ import annotations

from datetime import datetime

import requests

from config.settings import ODDS_API_KEY

BASE_URL = "https://api.the-odds-api.com/v4"
REQUEST_TIMEOUT = 30
SPORT_KEYS = {
    "football": [
        "soccer_brazil_campeonato",
        "soccer_epl",
        "soccer_uefa_champs_league",
    ],
    "ufc": ["mma_mixed_martial_arts"],
}


def _fetch_event(sport_key: str, event_id: str) -> dict | None:
    """Busca os dados de odds de um evento na API e retorna o payload JSON."""
    try:
        response = requests.get(
            f"{BASE_URL}/sports/{sport_key}/odds/{event_id}",
            params={
                "apiKey": ODDS_API_KEY,
                "regions": "eu",
                "markets": "h2h",
                "oddsFormat": "decimal",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        print(
            "[BetAgent][closing_line] Payload invalido recebido para "
            f"event_id={event_id} sport_key={sport_key}."
        )
        return None
    except Exception as exc:
        print(
            "[BetAgent][closing_line] Falha ao buscar evento "
            f"event_id={event_id} sport_key={sport_key}: {exc}"
        )
        return None


def _best_h2h_odd(event: dict, team_name: str) -> float | None:
    """Extrai a maior odd H2H encontrada para o time informado."""
    try:
        normalized_team = team_name.strip().lower()
        best_odd: float | None = None

        bookmakers = event.get("bookmakers", [])
        if not isinstance(bookmakers, list):
            return None

        for bookmaker in bookmakers:
            markets = bookmaker.get("markets", [])
            if not isinstance(markets, list):
                continue

            for market in markets:
                if str(market.get("key", "")).lower() != "h2h":
                    continue

                outcomes = market.get("outcomes", [])
                if not isinstance(outcomes, list):
                    continue

                for outcome in outcomes:
                    outcome_name = str(outcome.get("name", "")).strip().lower()
                    if outcome_name != normalized_team:
                        continue

                    price = outcome.get("price")
                    try:
                        odd = float(price)
                    except (TypeError, ValueError):
                        continue

                    if best_odd is None or odd > best_odd:
                        best_odd = odd

        return best_odd
    except Exception as exc:
        print(
            "[BetAgent][closing_line] Falha ao extrair odd H2H para "
            f"time={team_name}: {exc}"
        )
        return None


def capture_closing_line(event_id: str, sport: str, team_name: str) -> dict | None:
    """Captura a closing line de um time para um evento esportivo."""
    try:
        if not ODDS_API_KEY:
            print("[BetAgent][closing_line] ODDS_API_KEY ausente.")
            return None

        sport_keys = SPORT_KEYS.get(sport, [])
        if not sport_keys:
            print(f"[BetAgent][closing_line] Esporte nao suportado: {sport}")
            return None

        for sport_key in sport_keys:
            event = _fetch_event(sport_key=sport_key, event_id=event_id)
            if event is None:
                continue

            closing_odd = _best_h2h_odd(event=event, team_name=team_name)
            if closing_odd is None:
                continue

            result = {
                "event_id": event_id,
                "team": team_name,
                "closing_odds": float(closing_odd),
                "captured_at": datetime.utcnow().isoformat(),
            }
            print(
                "[BetAgent][closing_line] Closing line capturada para "
                f"event_id={event_id} team={team_name}: {closing_odd}"
            )
            return result

        print(
            "[BetAgent][closing_line] Nenhuma closing line encontrada para "
            f"event_id={event_id} team={team_name}."
        )
        return None
    except Exception as exc:
        print(
            "[BetAgent][closing_line] Falha ao capturar closing line para "
            f"event_id={event_id} team={team_name}: {exc}"
        )
        return None


if __name__ == "__main__":
    print("Modulo closing_line_collector disponivel.")
