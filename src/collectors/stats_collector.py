"""Coleta estatisticas de futebol e MMA para validacao local no projeto."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

from config.settings import API_FOOTBALL_KEY


BASE_URL = "https://v3.football.api-sports.io"
UFCSTATS_UPCOMING_URL = "http://www.ufcstats.com/statistics/events/upcoming"
UFCSTATS_USER_AGENT = "Mozilla/5.0"
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


def _build_ufcstats_headers() -> dict[str, str]:
    """Monta os headers padrao para scraping do UFCStats."""
    return {"User-Agent": UFCSTATS_USER_AGENT}


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


def _fetch_ufcstats_page(url: str) -> BeautifulSoup:
    """Busca uma pagina do UFCStats e retorna o HTML parseado."""
    response = requests.get(
        url,
        headers=_build_ufcstats_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _extract_text_value(text: str) -> str:
    """Extrai o valor textual apos os dois pontos."""
    parts = text.split(":", maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    return text.strip()


def _parse_upcoming_event() -> tuple[str, str]:
    """Busca o proximo evento do UFCStats."""
    soup = _fetch_ufcstats_page(UFCSTATS_UPCOMING_URL)
    event_link = soup.select_one('a[href*="event-details/"]')
    if event_link is None:
        raise ValueError("Nao foi possivel encontrar o proximo evento no UFCStats.")

    event_url = str(event_link.get("href", "")).strip()
    event_name = event_link.get_text(" ", strip=True)
    if not event_url or not event_name:
        raise ValueError("O proximo evento do UFCStats veio sem nome ou URL.")
    return event_name, event_url


def _parse_event_date(event_soup: BeautifulSoup) -> str:
    """Extrai a data do evento a partir da pagina do card."""
    for item in event_soup.select(".b-list__box-list-item"):
        text = item.get_text(" ", strip=True)
        if text.startswith("Date:"):
            return _extract_text_value(text)
    return ""


def _parse_event_fights(event_soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Extrai os links dos lutadores de cada luta do card."""
    fights: list[tuple[str, str]] = []
    rows = event_soup.select("tr.b-fight-details__table-row")
    for row in rows:
        fighter_links = row.select('a[href*="fighter-details/"]')
        if len(fighter_links) < 2:
            continue

        fighter_a_url = str(fighter_links[0].get("href", "")).strip()
        fighter_b_url = str(fighter_links[1].get("href", "")).strip()
        if fighter_a_url and fighter_b_url:
            fights.append((fighter_a_url, fighter_b_url))
    return fights


def _parse_fighter_stat_items(fighter_soup: BeautifulSoup) -> dict[str, str]:
    """Monta um mapa label->valor para os itens de stats do lutador."""
    stats: dict[str, str] = {}
    for item in fighter_soup.select(".b-list__box-list-item"):
        if not isinstance(item, Tag):
            continue
        text = item.get_text(" ", strip=True)
        if not text or ":" not in text:
            continue
        label, value = text.split(":", maxsplit=1)
        stats[label.strip().lower()] = value.strip()
    return stats


def _parse_fighter_details(fighter_url: str) -> dict[str, Any]:
    """Extrai os detalhes normalizados de um lutador do UFCStats."""
    fighter_soup = _fetch_ufcstats_page(fighter_url)
    stats_map = _parse_fighter_stat_items(fighter_soup)

    name_node = fighter_soup.select_one(".b-content__title-highlight")
    record_node = fighter_soup.select_one(".b-content__title-record")

    name = name_node.get_text(" ", strip=True) if name_node else ""
    raw_record = record_node.get_text(" ", strip=True) if record_node else ""

    return {
        "name": name,
        "record": raw_record.replace("Record:", "").strip(),
        "height": stats_map.get("height", ""),
        "weight": stats_map.get("weight", ""),
        "reach": stats_map.get("reach", ""),
        "stance": stats_map.get("stance", stats_map.get("stance ", "")),
        "slpm": _to_float(stats_map.get("slpm")),
        "str_acc": stats_map.get("str. acc.", ""),
        "sapm": _to_float(stats_map.get("sapm")),
        "str_def": stats_map.get("str. def", ""),
        "td_avg": _to_float(stats_map.get("td avg.")),
        "td_acc": stats_map.get("td acc.", ""),
        "td_def": stats_map.get("td def.", ""),
        "sub_avg": _to_float(stats_map.get("sub. avg.")),
    }


def _print_mma_fight_summary(fight: dict[str, Any]) -> None:
    """Printa um resumo legivel de uma luta do card."""
    fighter_a = fight["fighter_a"]
    fighter_b = fight["fighter_b"]
    print(
        f"\n[BetAgent][stats][mma] {fight['event']} | {fight['event_date']}"
    )
    print(
        "[BetAgent][stats][mma]   "
        f"{fighter_a['name']} ({fighter_a['record']}) | "
        f"SLpM: {fighter_a['slpm']} | SApM: {fighter_a['sapm']} | "
        f"TD Avg: {fighter_a['td_avg']} | Sub Avg: {fighter_a['sub_avg']}"
    )
    print(
        "[BetAgent][stats][mma]   "
        f"{fighter_b['name']} ({fighter_b['record']}) | "
        f"SLpM: {fighter_b['slpm']} | SApM: {fighter_b['sapm']} | "
        f"TD Avg: {fighter_b['td_avg']} | Sub Avg: {fighter_b['sub_avg']}"
    )


def _run_mma() -> list[dict[str, Any]] | None:
    """Coleta o proximo card do UFCStats com stats dos dois lutadores por luta."""
    try:
        event_name, event_url = _parse_upcoming_event()
        print(f"[BetAgent][stats][mma] Buscando proximo card: {event_name}")

        event_soup = _fetch_ufcstats_page(event_url)
        event_date = _parse_event_date(event_soup)
        fight_links = _parse_event_fights(event_soup)
        if not fight_links:
            print("[BetAgent][stats][mma] Nenhuma luta encontrada no proximo card.")
            return []

        fighter_cache: dict[str, dict[str, Any]] = {}
        fights: list[dict[str, Any]] = []

        for fighter_a_url, fighter_b_url in fight_links:
            try:
                if fighter_a_url not in fighter_cache:
                    fighter_cache[fighter_a_url] = _parse_fighter_details(fighter_a_url)
                if fighter_b_url not in fighter_cache:
                    fighter_cache[fighter_b_url] = _parse_fighter_details(fighter_b_url)

                fight = {
                    "event": event_name,
                    "event_date": event_date,
                    "fighter_a": fighter_cache[fighter_a_url],
                    "fighter_b": fighter_cache[fighter_b_url],
                }
                fights.append(fight)
                _print_mma_fight_summary(fight)
            except requests.RequestException as exc:
                print(f"[BetAgent][stats][mma] Falha ao processar luta do card: {exc}")
                continue
            except Exception as exc:
                print(f"[BetAgent][stats][mma] Erro inesperado em uma luta: {exc}")
                continue

        print(f"\n[BetAgent][stats][mma] Total de lutas coletadas: {len(fights)}")
        return fights
    except Exception as exc:
        print(f"[BetAgent][stats][mma] Falha total no scraping do UFCStats: {exc}")
        return None


def run(sport: str = "football") -> list[dict[str, Any]] | None:
    """Busca fixtures futuros e estatisticas de futebol pela API-Football."""
    if sport == "mma":
        return _run_mma()

    if sport != "football":
        print(f"[BetAgent][stats] Esporte '{sport}' ainda nao suportado.")
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
