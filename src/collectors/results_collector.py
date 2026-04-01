"""Coleta resultados concluidos de futebol e MMA para uso em post-mortem."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from config.settings import API_FOOTBALL_KEY


FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
UFCSTATS_COMPLETED_URL = "http://www.ufcstats.com/statistics/events/completed"
UFCSTATS_USER_AGENT = "Mozilla/5.0"
REQUEST_TIMEOUT = 30
LEAGUES = [
    {"id": 71, "name": "Brasileirao"},
    {"id": 39, "name": "Premier League"},
    {"id": 2, "name": "Champions League"},
]


def _build_football_headers() -> dict[str, str]:
    """Monta os headers padrao da API-Football."""
    return {"x-apisports-key": API_FOOTBALL_KEY or ""}


def _build_ufc_headers() -> dict[str, str]:
    """Monta os headers padrao para scraping do UFCStats."""
    return {"User-Agent": UFCSTATS_USER_AGENT}


def _print_remaining_requests(headers: requests.structures.CaseInsensitiveDict[str]) -> None:
    """Printa a quantidade restante de requisicoes da API-Football."""
    remaining = headers.get("x-ratelimit-requests-remaining", "desconhecido")
    limit = headers.get("x-ratelimit-requests-limit", "desconhecido")
    print(f"[BetAgent][results] Requisicoes restantes: {remaining} / limite: {limit}")


def _to_int(value: Any) -> int:
    """Converte um valor numerico para inteiro com fallback seguro."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _validate_date(date: str) -> datetime:
    """Valida a data de entrada no formato YYYY-MM-DD."""
    return datetime.strptime(date, "%Y-%m-%d")


def _football_season_candidates(target_date: datetime) -> list[int]:
    """Retorna temporadas candidatas para a data informada."""
    year = target_date.year
    month = target_date.month
    candidates = [year]
    if month <= 7:
        candidates.append(year - 1)
    else:
        candidates.append(year + 1)

    seasons: list[int] = []
    for season in candidates:
        if season not in seasons:
            seasons.append(season)
    return seasons


def _fetch_football_fixtures(league_id: int, season: int, date: str) -> list[dict[str, Any]]:
    """Busca fixtures de uma liga em uma data especifica."""
    response = requests.get(
        f"{FOOTBALL_BASE_URL}/fixtures",
        headers=_build_football_headers(),
        params={"league": league_id, "season": season, "date": date},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    _print_remaining_requests(response.headers)

    payload = response.json()
    errors = payload.get("errors")
    if errors:
        raise ValueError(
            f"API-Football bloqueou league={league_id}, season={season}, date={date}: {errors}"
        )

    data = payload.get("response")
    if not isinstance(data, list):
        raise ValueError(
            f"Resposta inesperada ao buscar fixtures da liga {league_id} na temporada {season}."
        )
    return data


def _normalize_football_result(
    fixture_data: dict[str, Any],
    fallback_competition: str,
) -> dict[str, Any]:
    """Normaliza um resultado de futebol no formato padrao do projeto."""
    fixture = fixture_data.get("fixture", {})
    league = fixture_data.get("league", {})
    teams = fixture_data.get("teams", {})
    goals = fixture_data.get("goals", {})

    home_team = str(teams.get("home", {}).get("name", ""))
    away_team = str(teams.get("away", {}).get("name", ""))
    home_goals = _to_int(goals.get("home"))
    away_goals = _to_int(goals.get("away"))

    if home_goals > away_goals:
        winner = home_team
    elif away_goals > home_goals:
        winner = away_team
    else:
        winner = "draw"

    return {
        "sport": "football",
        "competition": str(league.get("name") or fallback_competition),
        "match": f"{home_team} vs {away_team}",
        "event_date": str(fixture.get("date", "")),
        "result": f"{home_team} {home_goals} x {away_goals} {away_team}",
        "winner": winner,
        "method": None,
    }


def _print_football_result(result: dict[str, Any]) -> None:
    """Printa um resumo legivel de um resultado de futebol."""
    print(
        f"[BetAgent][results][football] {result['competition']} | "
        f"{result['match']} | {result['result']}"
    )


def _run_football(date: str) -> list[dict[str, Any]]:
    """Coleta resultados concluidos de futebol para a data informada."""
    if not API_FOOTBALL_KEY:
        raise EnvironmentError("API_FOOTBALL_KEY ausente. Configure o .env antes de rodar.")

    target_date = _validate_date(date)
    season_candidates = _football_season_candidates(target_date)
    results: list[dict[str, Any]] = []
    seen_fixture_ids: set[int] = set()

    for league in LEAGUES:
        try:
            print(f"[BetAgent][results][football] Buscando resultados de {league['name']}...")
            league_fixtures: list[dict[str, Any]] = []

            for season in season_candidates:
                try:
                    fixtures = _fetch_football_fixtures(league["id"], season, date)
                except requests.RequestException as exc:
                    print(
                        "[BetAgent][results][football] Falha HTTP em "
                        f"{league['name']} ({season}): {exc}"
                    )
                    continue
                except Exception as exc:
                    print(
                        "[BetAgent][results][football] Erro ao consultar "
                        f"{league['name']} ({season}): {exc}"
                    )
                    continue

                if fixtures:
                    league_fixtures.extend(fixtures)

            for fixture_data in league_fixtures:
                try:
                    fixture = fixture_data.get("fixture", {})
                    fixture_id = _to_int(fixture.get("id"))
                    if fixture_id in seen_fixture_ids:
                        continue

                    status_short = str(fixture.get("status", {}).get("short", ""))
                    if status_short != "FT":
                        continue

                    normalized = _normalize_football_result(fixture_data, league["name"])
                    results.append(normalized)
                    seen_fixture_ids.add(fixture_id)
                    _print_football_result(normalized)
                except Exception as exc:
                    print(
                        "[BetAgent][results][football] Erro ao normalizar fixture "
                        f"de {league['name']}: {exc}"
                    )
                    continue
        except Exception as exc:
            print(f"[BetAgent][results][football] Falha na liga {league['name']}: {exc}")
            continue

    return results


def _fetch_ufc_page(url: str) -> BeautifulSoup:
    """Busca uma pagina do UFCStats e retorna o HTML parseado."""
    response = requests.get(url, headers=_build_ufc_headers(), timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _parse_completed_events(date: str) -> list[dict[str, str]]:
    """Lista eventos concluidos do UFCStats que ocorreram na data informada."""
    soup = _fetch_ufc_page(UFCSTATS_COMPLETED_URL)
    target_date = datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y")
    events: list[dict[str, str]] = []

    for row in soup.select("tr.b-statistics__table-row"):
        link = row.select_one('a[href*="event-details/"]')
        if link is None:
            continue

        event_name = link.get_text(" ", strip=True)
        row_text = row.get_text(" | ", strip=True)
        if target_date not in row_text:
            continue

        event_url = str(link.get("href", "")).strip()
        if not event_name or not event_url:
            continue

        events.append({"name": event_name, "url": event_url, "date": target_date})

    return events


def _split_fighter_names(row: BeautifulSoup) -> list[str]:
    """Extrai os nomes dos dois lutadores de uma linha de resultado."""
    names = [
        link.get_text(" ", strip=True)
        for link in row.select('a[href*="fighter-details/"]')[:2]
    ]
    return [name for name in names if name]


def _normalize_mma_method(raw_method: str) -> str | None:
    """Normaliza o metodo de vitoria para categorias mais estaveis."""
    normalized = raw_method.upper()
    if "KO/TKO" in normalized or normalized == "KO":
        return "KO"
    if "SUB" in normalized:
        return "Submission"
    if "DEC" in normalized:
        return "Decision"
    if not raw_method:
        return None
    return raw_method


def _normalize_mma_result(
    row: BeautifulSoup,
    competition: str,
    event_date: str,
) -> dict[str, Any] | None:
    """Normaliza uma luta concluida do UFCStats no formato padrao do projeto."""
    cells = row.select("td")
    if len(cells) < 10:
        return None

    fighters = _split_fighter_names(row)
    if len(fighters) < 2:
        return None

    status = cells[0].get_text(" ", strip=True).lower()
    fighter_a = fighters[0]
    fighter_b = fighters[1]

    if "win" in status:
        winner = fighter_a
    elif "loss" in status:
        winner = fighter_b
    elif "draw" in status:
        winner = "draw"
    else:
        winner = "draw"

    raw_method = cells[7].get_text(" ", strip=True)
    method = _normalize_mma_method(raw_method.split(" ", maxsplit=1)[0] if raw_method else raw_method)
    round_value = cells[8].get_text(" ", strip=True)
    time_value = cells[9].get_text(" ", strip=True)

    if winner == "draw":
        result_text = f"{fighter_a} e {fighter_b} empataram"
    else:
        method_text = method or raw_method or "resultado desconhecido"
        result_text = f"{winner} venceu por {method_text} no R{round_value}"
        if time_value:
            result_text += f" aos {time_value}"

    return {
        "sport": "ufc",
        "competition": competition,
        "match": f"{fighter_a} vs {fighter_b}",
        "event_date": event_date,
        "result": result_text,
        "winner": winner,
        "method": method,
    }


def _print_mma_result(result: dict[str, Any]) -> None:
    """Printa um resumo legivel de um resultado de MMA."""
    print(
        f"[BetAgent][results][mma] {result['competition']} | "
        f"{result['match']} | {result['result']}"
    )


def _run_mma(date: str) -> list[dict[str, Any]]:
    """Coleta resultados concluidos de MMA para a data informada."""
    results: list[dict[str, Any]] = []

    events = _parse_completed_events(date)
    if not events:
        print(f"[BetAgent][results][mma] Nenhum evento concluido encontrado em {date}.")
        return results

    for event in events:
        try:
            print(f"[BetAgent][results][mma] Buscando resultados de {event['name']}...")
            event_soup = _fetch_ufc_page(event["url"])
            rows = event_soup.select("tr.b-fight-details__table-row")
            for row in rows:
                try:
                    normalized = _normalize_mma_result(row, event["name"], event["date"])
                    if normalized is None:
                        continue
                    results.append(normalized)
                    _print_mma_result(normalized)
                except Exception as exc:
                    print(
                        f"[BetAgent][results][mma] Erro ao processar luta de {event['name']}: {exc}"
                    )
                    continue
        except requests.RequestException as exc:
            print(f"[BetAgent][results][mma] Falha HTTP em {event['name']}: {exc}")
            continue
        except Exception as exc:
            print(f"[BetAgent][results][mma] Erro inesperado em {event['name']}: {exc}")
            continue

    return results


def run(date: str, sport: str = "all") -> list[dict[str, Any]] | None:
    """Coleta resultados concluidos por data para futebol, MMA ou ambos."""
    try:
        _validate_date(date)

        results: list[dict[str, Any]] = []

        if sport in {"football", "all"}:
            results.extend(_run_football(date))

        if sport in {"mma", "all"}:
            results.extend(_run_mma(date))

        if sport not in {"football", "mma", "all"}:
            print(f"[BetAgent][results] Esporte '{sport}' ainda nao suportado.")
            return []

        print(f"[BetAgent][results] Total de resultados coletados: {len(results)}")
        return results
    except Exception as exc:
        print(f"[BetAgent][results] Falha total no coletor de resultados: {exc}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--sport", default="all")
    args = parser.parse_args()
    print(json.dumps(run(args.date, args.sport), indent=2, ensure_ascii=False))
