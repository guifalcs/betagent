"""Coleta odds de eventos futuros via The Odds API para validacao local."""

from __future__ import annotations

import json
from typing import Any

import requests

from config.settings import ODDS_API_KEY


BASE_URL = "https://api.the-odds-api.com/v4"
REQUEST_TIMEOUT = 30
SPORTS = (
    {
        "key": "soccer_brazil_campeonato",
        "sport": "football",
        "competition": "Brasileirao",
    },
    {
        "key": "soccer_epl",
        "sport": "football",
        "competition": "Premier League",
    },
    {
        "key": "soccer_uefa_champs_league",
        "sport": "football",
        "competition": "Champions League",
    },
    {
        "key": "mma_mixed_martial_arts",
        "sport": "ufc",
        "competition": "UFC/MMA",
    },
)


def _build_params() -> dict[str, str]:
    """Monta os parametros padrao para a consulta de odds."""
    return {
        "apiKey": ODDS_API_KEY or "",
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
        "daysFrom": "7",
    }


def _fetch_odds_for_sport(sport_key: str) -> list[dict[str, Any]]:
    """Busca odds para um esporte especifico na The Odds API."""
    response = requests.get(
        f"{BASE_URL}/sports/{sport_key}/odds",
        params=_build_params(),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    _print_remaining_requests(response.headers)
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(f"Resposta inesperada para o esporte {sport_key}.")
    return payload


def _print_remaining_requests(headers: requests.structures.CaseInsensitiveDict[str]) -> None:
    """Printa a quantidade restante de requisicoes da API."""
    remaining = headers.get("x-requests-remaining", "desconhecido")
    used = headers.get("x-requests-used", "desconhecido")
    last_cost = headers.get("x-requests-last", "desconhecido")
    print(
        "[BetAgent][odds] Creditos restantes: "
        f"{remaining} | usados: {used} | custo da ultima chamada: {last_cost}"
    )


def _normalize_outcomes(raw_outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normaliza os outcomes retornados por um bookmaker."""
    outcomes: list[dict[str, Any]] = []
    for outcome in raw_outcomes:
        price = outcome.get("price")
        name = outcome.get("name")
        if name is None or price is None:
            continue
        outcomes.append({"name": str(name), "odds": float(price)})
    return outcomes


def _normalize_bookmakers(raw_bookmakers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normaliza bookmakers e outcomes para a estrutura padrao do projeto."""
    bookmakers: list[dict[str, Any]] = []
    for bookmaker in raw_bookmakers:
        name = bookmaker.get("title")
        if name is None:
            continue

        markets: list[dict[str, Any]] = bookmaker.get("markets", [])
        for market in markets:
            market_key = market.get("key")
            if market_key not in {"h2h", "totals"}:
                continue

            outcomes = _normalize_outcomes(market.get("outcomes", []))
            if not outcomes:
                continue

            bookmakers.append({"name": str(name), "market": str(market_key), "outcomes": outcomes})

    return bookmakers


def _normalize_markets(raw_bookmakers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrupa os bookmakers normalizados por mercado."""
    grouped_markets: dict[str, list[dict[str, Any]]] = {"h2h": [], "totals": []}

    for bookmaker in _normalize_bookmakers(raw_bookmakers):
        grouped_markets[bookmaker["market"]].append(
            {"name": bookmaker["name"], "outcomes": bookmaker["outcomes"]}
        )

    markets: list[dict[str, Any]] = []
    for market_name, bookmakers in grouped_markets.items():
        if bookmakers:
            markets.append({"market": market_name, "bookmakers": bookmakers})
    return markets


def _normalize_event(raw_event: dict[str, Any], sport_meta: dict[str, str]) -> dict[str, Any]:
    """Converte um evento bruto da API no formato padrao do projeto."""
    return {
        "event_id": str(raw_event.get("id", "")),
        "sport": sport_meta["sport"],
        "competition": sport_meta["competition"],
        "home_team": str(raw_event.get("home_team", "")),
        "away_team": str(raw_event.get("away_team", "")),
        "event_date": str(raw_event.get("commence_time", "")),
        "markets": _normalize_markets(raw_event.get("bookmakers", [])),
    }


def _format_outcomes(outcomes: list[dict[str, Any]]) -> str:
    """Formata outcomes em uma linha legivel para o terminal."""
    parts = [f"{outcome['name']}: {outcome['odds']}" for outcome in outcomes]
    return ", ".join(parts)


def _print_event_summary(event: dict[str, Any]) -> None:
    """Printa um resumo legivel do evento e das odds principais."""
    print(
        f"\n[BetAgent][odds] {event['competition']} | "
        f"{event['home_team']} vs {event['away_team']} | {event['event_date']}"
    )

    markets: list[dict[str, Any]] = event.get("markets", [])
    if not markets:
        print("[BetAgent][odds] Nenhum mercado disponivel para este evento.")
        return

    for market in markets:
        print(f"[BetAgent][odds] Mercado: {market['market']}")
        bookmakers = market.get("bookmakers", [])
        featured_bookmakers = bookmakers[:3]
        for bookmaker in featured_bookmakers:
            outcomes = bookmaker.get("outcomes", [])
            print(
                f"[BetAgent][odds]   {bookmaker['name']}: "
                f"{_format_outcomes(outcomes)}"
            )
        if len(bookmakers) > len(featured_bookmakers):
            print(
                "[BetAgent][odds]   ... "
                f"+{len(bookmakers) - len(featured_bookmakers)} bookmaker(s) neste mercado"
            )


def run() -> list[dict[str, Any]] | None:
    """Busca odds futuras de futebol e MMA/UFC e retorna eventos normalizados."""
    try:
        if not ODDS_API_KEY:
            print("[BetAgent][odds] ODDS_API_KEY ausente. Configure o .env antes de rodar.")
            return None

        events: list[dict[str, Any]] = []

        for sport_meta in SPORTS:
            sport_key = sport_meta["key"]
            try:
                print(f"\n[BetAgent][odds] Buscando odds para {sport_meta['competition']}...")
                sport_events = _fetch_odds_for_sport(sport_key)
            except requests.RequestException as exc:
                print(
                    f"[BetAgent][odds] Falha ao buscar odds para {sport_meta['competition']}: {exc}"
                )
                continue
            except Exception as exc:
                print(
                    "[BetAgent][odds] Erro inesperado ao processar "
                    f"{sport_meta['competition']}: {exc}"
                )
                continue

            if not sport_events:
                print(
                    f"[BetAgent][odds] Nenhum evento encontrado para {sport_meta['competition']}."
                )
                continue

            for raw_event in sport_events:
                event = _normalize_event(raw_event, sport_meta)
                events.append(event)
                _print_event_summary(event)

        print(f"\n[BetAgent][odds] Total de eventos coletados: {len(events)}")
        return events
    except Exception as exc:
        print(f"[BetAgent][odds] Falha total no coletor de odds: {exc}")
        return None


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
