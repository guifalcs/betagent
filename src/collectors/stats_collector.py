"""Coleta fixtures e estatisticas de futebol via API-Football para validacao local."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

import requests

from config.settings import API_FOOTBALL_KEY


BASE_URL = "https://v3.football.api-sports.io"
REQUEST_TIMEOUT = 30
LEAGUES = [
    {"id": 71, "name": "Brasileirao", "season": 2025},
    {"id": 39, "name": "Premier League", "season": 2024},
    {"id": 2, "name": "Champions League", "season": 2024},
]
HISTORICAL_FALLBACKS = {
    71: {"season": 2024, "from": "2024-06-01", "to": "2024-06-30"},
    39: {"season": 2024, "from": "2025-04-01", "to": "2025-04-07"},
    2: {"season": 2024, "from": "2025-04-01", "to": "2025-04-30"},
}


def _build_headers() -> dict[str, str]:
    """Monta os headers padrao da API-Football."""
    return {
        "x-apisports-key": API_FOOTBALL_KEY or "",
    }


def _print_remaining_requests(headers: requests.structures.CaseInsensitiveDict[str]) -> None:
    """Printa a quantidade restante de requisicoes da API."""
    remaining = headers.get("x-ratelimit-requests-remaining", "desconhecido")
    limit = headers.get("x-ratelimit-requests-limit", "desconhecido")
    print(f"[BetAgent][stats] Requisicoes restantes: {remaining} / limite: {limit}")


def _request(endpoint: str, params: dict[str, Any]) -> Any:
    """Executa uma chamada HTTP para a API-Football e retorna o payload principal."""
    response = requests.get(
        f"{BASE_URL}{endpoint}",
        headers=_build_headers(),
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    _print_remaining_requests(response.headers)

    payload = response.json()
    if "response" not in payload:
        raise ValueError(f"Resposta inesperada da API-Football para {endpoint}.")
    return payload["response"]


def _to_int(value: Any) -> int:
    """Converte um valor numerico em inteiro com fallback seguro."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    """Converte um valor numerico em float com fallback seguro."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_average(total: Any, played: int) -> float:
    """Calcula uma media segura a partir do total e jogos disputados."""
    if played <= 0:
        return 0.0
    return round(_to_float(total) / played, 2)


def _extract_team_stats(statistics: dict[str, Any]) -> dict[str, Any]:
    """Normaliza as estatisticas de temporada de um time."""
    fixtures = statistics.get("fixtures", {})
    goals = statistics.get("goals", {})
    played = _to_int(fixtures.get("played", {}).get("total"))
    goals_for_total = goals.get("for", {}).get("total", {}).get("total")
    goals_against_total = goals.get("against", {}).get("total", {}).get("total")

    return {
        "wins": _to_int(fixtures.get("wins", {}).get("total")),
        "draws": _to_int(fixtures.get("draws", {}).get("total")),
        "losses": _to_int(fixtures.get("loses", {}).get("total")),
        "goals_for_avg": _safe_average(goals_for_total, played),
        "goals_against_avg": _safe_average(goals_against_total, played),
        "form": str(statistics.get("form") or ""),
    }


def _fetch_next_fixtures(league_id: int, season: int) -> list[dict[str, Any]]:
    """Busca os proximos fixtures de uma liga."""
    data = _request(
        "/fixtures",
        {"league": league_id, "season": season, "next": 5},
    )
    if not isinstance(data, list):
        raise ValueError(f"Resposta invalida ao buscar fixtures da liga {league_id}.")
    return data


def _fetch_fixtures_by_date_range(
    league_id: int,
    season: int,
    from_date: str,
    to_date: str,
) -> list[dict[str, Any]]:
    """Busca fixtures de uma liga em uma janela historica e limita a 5 resultados."""
    data = _request(
        "/fixtures",
        {"league": league_id, "season": season, "from": from_date, "to": to_date},
    )
    if not isinstance(data, list):
        raise ValueError(f"Resposta invalida ao buscar fixtures historicos da liga {league_id}.")
    return data[:5]


def _fetch_h2h(home_id: int, away_id: int) -> list[dict[str, Any]]:
    """Busca os ultimos confrontos diretos entre dois times."""
    data = _request(
        "/fixtures/headtohead",
        {"h2h": f"{home_id}-{away_id}", "last": 5},
    )
    if not isinstance(data, list):
        raise ValueError(f"Resposta invalida ao buscar H2H {home_id}-{away_id}.")
    return data


def _fetch_team_statistics(league_id: int, season: int, team_id: int) -> dict[str, Any]:
    """Busca as estatisticas de temporada de um time."""
    data = _request(
        "/teams/statistics",
        {"league": league_id, "season": season, "team": team_id},
    )
    if not isinstance(data, dict) or not data:
        raise ValueError(
            f"Nenhuma estatistica encontrada para team={team_id} league={league_id}."
        )
    return data


def _candidate_seasons(preferred_season: int) -> list[int]:
    """Monta temporadas candidatas para evitar ligas encerradas sem fixtures futuros."""
    current_year = datetime.now(ZoneInfo("America/Sao_Paulo")).year
    candidates = [preferred_season, current_year, current_year - 1, current_year + 1]
    seasons: list[int] = []
    for season in candidates:
        if season not in seasons:
            seasons.append(season)
    return seasons


def _fetch_next_fixtures_with_fallback(
    league: dict[str, Any],
) -> tuple[list[dict[str, Any]], int, str]:
    """Busca fixtures da liga tentando a temporada configurada e fallbacks uteis."""
    last_response: list[dict[str, Any]] = []
    for season in _candidate_seasons(int(league["season"])):
        fixtures = _fetch_next_fixtures(int(league["id"]), season)
        if fixtures:
            if season != int(league["season"]):
                print(
                    "[BetAgent][stats] Nenhum fixture na temporada configurada. "
                    f"Usando fallback {season} para {league['name']}."
                )
            return fixtures, season, "next"
        last_response = fixtures

    fallback = HISTORICAL_FALLBACKS.get(int(league["id"]))
    if fallback:
        fixtures = _fetch_fixtures_by_date_range(
            league_id=int(league["id"]),
            season=int(fallback["season"]),
            from_date=str(fallback["from"]),
            to_date=str(fallback["to"]),
        )
        if fixtures:
            print(
                "[BetAgent][stats] Sem acesso a fixtures futuros desta liga no plano atual. "
                f"Usando janela historica {fallback['from']}..{fallback['to']}."
            )
            return fixtures, int(fallback["season"]), "historical"

    return last_response, int(league["season"]), "next"


def _normalize_h2h(raw_h2h: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normaliza os confrontos diretos recentes."""
    normalized: list[dict[str, Any]] = []
    for item in raw_h2h:
        fixture = item.get("fixture", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        normalized.append(
            {
                "date": str(fixture.get("date", "")),
                "home_team": str(teams.get("home", {}).get("name", "")),
                "away_team": str(teams.get("away", {}).get("name", "")),
                "home_goals": _to_int(goals.get("home")),
                "away_goals": _to_int(goals.get("away")),
            }
        )
    return normalized


def _normalize_fixture(
    fixture_data: dict[str, Any],
    competition: str,
    home_stats: dict[str, Any],
    away_stats: dict[str, Any],
    h2h: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normaliza um fixture no formato esperado pelo projeto."""
    fixture = fixture_data.get("fixture", {})
    teams = fixture_data.get("teams", {})
    home_team = teams.get("home", {})
    away_team = teams.get("away", {})

    return {
        "fixture_id": _to_int(fixture.get("id")),
        "competition": competition,
        "home_team": {
            "id": _to_int(home_team.get("id")),
            "name": str(home_team.get("name", "")),
        },
        "away_team": {
            "id": _to_int(away_team.get("id")),
            "name": str(away_team.get("name", "")),
        },
        "event_date": str(fixture.get("date", "")),
        "home_stats": home_stats,
        "away_stats": away_stats,
        "h2h": h2h,
    }


def _print_fixture_summary(fixture: dict[str, Any]) -> None:
    """Printa um resumo legivel do fixture, estatisticas e H2H."""
    home_team = fixture["home_team"]["name"]
    away_team = fixture["away_team"]["name"]
    home_stats = fixture["home_stats"]
    away_stats = fixture["away_stats"]

    print(
        f"\n[BetAgent][stats] {fixture['competition']} | "
        f"{home_team} vs {away_team} | {fixture['event_date']}"
    )
    print(
        "[BetAgent][stats]   Home | "
        f"form: {home_stats['form']} | "
        f"GF: {home_stats['goals_for_avg']} | "
        f"GA: {home_stats['goals_against_avg']} | "
        f"W-D-L: {home_stats['wins']}-{home_stats['draws']}-{home_stats['losses']}"
    )
    print(
        "[BetAgent][stats]   Away | "
        f"form: {away_stats['form']} | "
        f"GF: {away_stats['goals_for_avg']} | "
        f"GA: {away_stats['goals_against_avg']} | "
        f"W-D-L: {away_stats['wins']}-{away_stats['draws']}-{away_stats['losses']}"
    )

    if not fixture["h2h"]:
        print("[BetAgent][stats]   H2H: nenhum confronto recente encontrado.")
        return

    print("[BetAgent][stats]   H2H recentes:")
    for match in fixture["h2h"]:
        print(
            "[BetAgent][stats]     "
            f"{match['date']} | {match['home_team']} {match['home_goals']} "
            f"x {match['away_goals']} {match['away_team']}"
        )


def run(sport: str = "football") -> list[dict[str, Any]] | None:
    """Busca fixtures futuros e estatisticas de futebol pela API-Football."""
    if sport != "football":
        print(f"[BetAgent][stats] Esporte '{sport}' ainda nao suportado. MMA vira depois.")
        return None

    try:
        if not API_FOOTBALL_KEY:
            print(
                "[BetAgent][stats] API_FOOTBALL_KEY ausente. Configure o .env antes de rodar."
            )
            return None

        all_fixtures: list[dict[str, Any]] = []
        team_stats_cache: dict[tuple[int, int, int], dict[str, Any]] = {}

        for league in LEAGUES:
            try:
                print(f"\n[BetAgent][stats] Buscando fixtures de {league['name']}...")
                fixtures, active_season, fixture_mode = _fetch_next_fixtures_with_fallback(league)
            except requests.RequestException as exc:
                print(f"[BetAgent][stats] Falha na liga {league['name']}: {exc}")
                continue
            except Exception as exc:
                print(f"[BetAgent][stats] Erro inesperado na liga {league['name']}: {exc}")
                continue

            if not fixtures:
                print(f"[BetAgent][stats] Nenhum fixture encontrado para {league['name']}.")
                continue

            for fixture_data in fixtures:
                try:
                    teams = fixture_data.get("teams", {})
                    home_team = teams.get("home", {})
                    away_team = teams.get("away", {})
                    home_id = _to_int(home_team.get("id"))
                    away_id = _to_int(away_team.get("id"))

                    h2h_raw = _fetch_h2h(home_id, away_id)
                    h2h = _normalize_h2h(h2h_raw)

                    home_cache_key = (league["id"], active_season, home_id)
                    away_cache_key = (league["id"], active_season, away_id)

                    if home_cache_key not in team_stats_cache:
                        team_stats_cache[home_cache_key] = _extract_team_stats(
                            _fetch_team_statistics(league["id"], active_season, home_id)
                        )
                    if away_cache_key not in team_stats_cache:
                        team_stats_cache[away_cache_key] = _extract_team_stats(
                            _fetch_team_statistics(league["id"], active_season, away_id)
                        )

                    normalized_fixture = _normalize_fixture(
                        fixture_data=fixture_data,
                        competition=(
                            f"{league['name']} ({'historical fallback' if fixture_mode == 'historical' else 'next fixtures'})"
                        ),
                        home_stats=team_stats_cache[home_cache_key],
                        away_stats=team_stats_cache[away_cache_key],
                        h2h=h2h,
                    )
                    all_fixtures.append(normalized_fixture)
                    _print_fixture_summary(normalized_fixture)
                except requests.RequestException as exc:
                    print(f"[BetAgent][stats] Falha ao processar fixture da liga {league['name']}: {exc}")
                    continue
                except Exception as exc:
                    print(
                        "[BetAgent][stats] Erro inesperado ao normalizar fixture "
                        f"da liga {league['name']}: {exc}"
                    )
                    continue

        print(f"\n[BetAgent][stats] Total de fixtures coletados: {len(all_fixtures)}")
        return all_fixtures
    except Exception as exc:
        print(f"[BetAgent][stats] Falha total no coletor de stats: {exc}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", default="football")
    args = parser.parse_args()
    print(json.dumps(run(args.sport), indent=2, ensure_ascii=False))
