"""Probability engine for football and MMA events."""

from __future__ import annotations

import json
import math
from typing import Any


LIGA_AVG: float = 1.35
MAX_GOALS: int = 7


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _parse_pct(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            numeric_value: float = float(value)
            return numeric_value / 100.0 if numeric_value > 1 else numeric_value

        raw_value: str = str(value).strip().replace("%", "")
        if not raw_value:
            return 0.0

        numeric_value = float(raw_value)
        return numeric_value / 100.0 if numeric_value > 1 else numeric_value
    except (TypeError, ValueError):
        return 0.0


def _parse_record(value: Any) -> tuple[int, int]:
    try:
        if value is None:
            return 0, 0

        parts: list[str] = str(value).strip().split("-")
        if len(parts) < 2:
            return 0, 0

        wins: int = _safe_int(parts[0], 0)
        losses: int = _safe_int(parts[1], 0)
        return wins, losses
    except Exception:
        return 0, 0


def _normalize_probabilities(probabilities: list[float]) -> list[float]:
    total: float = sum(probabilities)
    if total <= 0:
        size: int = len(probabilities)
        return [1.0 / size for _ in probabilities] if size else []
    return [value / total for value in probabilities]


def _form_win_rate(form: Any) -> float:
    try:
        recent_form: str = str(form or "").upper()[-5:]
        if not recent_form:
            return 0.5

        points_map: dict[str, float] = {"W": 1.0, "D": 0.5, "L": 0.0}
        valid_scores: list[float] = [points_map[result] for result in recent_form if result in points_map]
        if not valid_scores:
            return 0.5

        return sum(valid_scores) / len(valid_scores)
    except Exception:
        return 0.5


def _form_multiplier(form: Any) -> float:
    win_rate: float = _form_win_rate(form)
    multiplier: float = 0.9 + (0.2 * win_rate)
    return _clamp(multiplier, 0.9, 1.1)


def _team_name_matches(candidate: Any, team_name: str) -> bool:
    return str(candidate or "").strip().lower() == str(team_name or "").strip().lower()


def _h2h_win_rates(
    h2h_matches: list[dict[str, Any]],
    home_team_name: str,
    away_team_name: str,
) -> tuple[float, float] | None:
    try:
        if len(h2h_matches) < 3:
            return None

        home_points: float = 0.0
        away_points: float = 0.0
        considered_matches: int = 0

        for match in h2h_matches:
            match_home_name: str = str(match.get("home_team", ""))
            match_away_name: str = str(match.get("away_team", ""))
            home_goals: int = _safe_int(match.get("home_goals"), 0)
            away_goals: int = _safe_int(match.get("away_goals"), 0)

            if _team_name_matches(match_home_name, home_team_name) and _team_name_matches(match_away_name, away_team_name):
                if home_goals > away_goals:
                    home_points += 1.0
                elif home_goals < away_goals:
                    away_points += 1.0
                else:
                    home_points += 0.5
                    away_points += 0.5
                considered_matches += 1
                continue

            if _team_name_matches(match_home_name, away_team_name) and _team_name_matches(match_away_name, home_team_name):
                if home_goals > away_goals:
                    away_points += 1.0
                elif home_goals < away_goals:
                    home_points += 1.0
                else:
                    home_points += 0.5
                    away_points += 0.5
                considered_matches += 1

        if considered_matches < 3:
            return None

        return home_points / considered_matches, away_points / considered_matches
    except Exception:
        return None


def _apply_h2h_adjustment(
    lambda_home: float,
    lambda_away: float,
    h2h_matches: list[dict[str, Any]],
    home_team_name: str,
    away_team_name: str,
) -> tuple[float, float]:
    rates: tuple[float, float] | None = _h2h_win_rates(h2h_matches, home_team_name, away_team_name)
    if rates is None:
        return lambda_home, lambda_away

    h2h_home_rate, h2h_away_rate = rates
    home_multiplier: float = 0.8 + (0.4 * h2h_home_rate)
    away_multiplier: float = 0.8 + (0.4 * h2h_away_rate)

    adjusted_home: float = (lambda_home * 0.8) + (lambda_home * home_multiplier * 0.2)
    adjusted_away: float = (lambda_away * 0.8) + (lambda_away * away_multiplier * 0.2)
    return adjusted_home, adjusted_away


def _calculate_poisson_probabilities(lambda_home: float, lambda_away: float) -> dict[str, float]:
    try:
        from scipy.stats import poisson
    except ImportError as exc:
        raise ImportError("scipy is required to run football probability calculations") from exc

    home_win: float = 0.0
    draw: float = 0.0
    away_win: float = 0.0

    for home_goals in range(MAX_GOALS + 1):
        for away_goals in range(MAX_GOALS + 1):
            probability: float = float(poisson.pmf(home_goals, lambda_home) * poisson.pmf(away_goals, lambda_away))
            if home_goals > away_goals:
                home_win += probability
            elif home_goals == away_goals:
                draw += probability
            else:
                away_win += probability

    normalized_home, normalized_draw, normalized_away = _normalize_probabilities([home_win, draw, away_win])
    return {
        "home_win_prob": normalized_home,
        "draw_prob": normalized_draw,
        "away_win_prob": normalized_away,
    }


def _fighter_score(fighter: dict[str, Any]) -> float:
    striking_score: float = _safe_float(fighter.get("slpm")) - _safe_float(fighter.get("sapm"))
    wrestling_score: float = _safe_float(fighter.get("td_avg")) * _parse_pct(fighter.get("td_acc"))
    defense_score: float = _parse_pct(fighter.get("str_def")) + _parse_pct(fighter.get("td_def"))

    wins, losses = _parse_record(fighter.get("record"))
    total_fights: int = wins + losses
    win_rate: float = wins / total_fights if total_fights > 0 else 0.5

    return (
        (0.35 * striking_score)
        + (0.25 * wrestling_score)
        + (0.20 * defense_score)
        + (0.20 * win_rate)
    )


def _softmax(scores: list[float]) -> list[float]:
    if not scores:
        return []

    max_score: float = max(scores)
    exponentials: list[float] = [math.exp(score - max_score) for score in scores]
    return _normalize_probabilities(exponentials)


def run_football(fixture: dict[str, Any]) -> dict[str, Any] | None:
    try:
        home_stats: dict[str, Any] = fixture.get("home_stats", {})
        away_stats: dict[str, Any] = fixture.get("away_stats", {})
        home_team: dict[str, Any] = fixture.get("home_team", {})
        away_team: dict[str, Any] = fixture.get("away_team", {})

        lambda_home: float = _safe_float(home_stats.get("goals_for_avg"), 0.0) * (
            _safe_float(away_stats.get("goals_against_avg"), 0.0) / LIGA_AVG
        )
        lambda_away: float = _safe_float(away_stats.get("goals_for_avg"), 0.0) * (
            _safe_float(home_stats.get("goals_against_avg"), 0.0) / LIGA_AVG
        )

        lambda_home *= _form_multiplier(home_stats.get("form"))
        lambda_away *= _form_multiplier(away_stats.get("form"))

        lambda_home, lambda_away = _apply_h2h_adjustment(
            lambda_home=lambda_home,
            lambda_away=lambda_away,
            h2h_matches=fixture.get("h2h", []) or [],
            home_team_name=str(home_team.get("name", "")),
            away_team_name=str(away_team.get("name", "")),
        )

        lambda_home = max(lambda_home, 0.05)
        lambda_away = max(lambda_away, 0.05)

        probabilities: dict[str, float] = _calculate_poisson_probabilities(
            lambda_home=lambda_home,
            lambda_away=lambda_away,
        )

        result: dict[str, Any] = {
            **probabilities,
            "lambda_home": lambda_home,
            "lambda_away": lambda_away,
            "method": "poisson_bivariate",
        }
        print(f"[BetAgent][probability] Football probabilities generated for fixture {fixture.get('fixture_id')}")
        return result
    except Exception as exc:
        print(f"[BetAgent][probability] Failed to run football model: {exc}")
        return None


def run_mma(fight: dict[str, Any]) -> dict[str, Any] | None:
    try:
        fighter_a: dict[str, Any] = fight.get("fighter_a", {})
        fighter_b: dict[str, Any] = fight.get("fighter_b", {})

        fighter_a_score: float = _fighter_score(fighter_a)
        fighter_b_score: float = _fighter_score(fighter_b)
        probabilities: list[float] = _softmax([fighter_a_score, fighter_b_score])

        result: dict[str, Any] = {
            "fighter_a_win_prob": probabilities[0],
            "fighter_b_win_prob": probabilities[1],
            "fighter_a_name": str(fighter_a.get("name", "")),
            "fighter_b_name": str(fighter_b.get("name", "")),
            "method": "composite_score",
        }
        print(
            "[BetAgent][probability] MMA probabilities generated for "
            f"{fighter_a.get('name', 'fighter_a')} vs {fighter_b.get('name', 'fighter_b')}"
        )
        return result
    except Exception as exc:
        print(f"[BetAgent][probability] Failed to run MMA model: {exc}")
        return None


def run(event: dict[str, Any], sport: str = "football") -> dict[str, Any] | None:
    try:
        normalized_sport: str = str(sport).strip().lower()
        if normalized_sport == "football":
            return run_football(event)
        if normalized_sport == "mma":
            return run_mma(event)

        print(f"[BetAgent][probability] Unsupported sport: {sport}")
        return None
    except Exception as exc:
        print(f"[BetAgent][probability] Failed to dispatch probability model: {exc}")
        return None


if __name__ == "__main__":
    synthetic_fixture: dict[str, Any] = {
        "fixture_id": 1001,
        "competition": "Synthetic League",
        "home_team": {"id": 1, "name": "Atlas FC"},
        "away_team": {"id": 2, "name": "Boreal United"},
        "event_date": "2026-04-03T20:00:00Z",
        "home_stats": {
            "wins": 3,
            "draws": 1,
            "losses": 1,
            "goals_for_avg": 1.8,
            "goals_against_avg": 1.1,
            "form": "WWDLW",
        },
        "away_stats": {
            "wins": 2,
            "draws": 2,
            "losses": 1,
            "goals_for_avg": 1.4,
            "goals_against_avg": 1.3,
            "form": "DLWDW",
        },
        "h2h": [
            {
                "date": "2025-06-10",
                "home_team": "Atlas FC",
                "away_team": "Boreal United",
                "home_goals": 2,
                "away_goals": 1,
            },
            {
                "date": "2025-01-20",
                "home_team": "Boreal United",
                "away_team": "Atlas FC",
                "home_goals": 0,
                "away_goals": 0,
            },
            {
                "date": "2024-09-15",
                "home_team": "Atlas FC",
                "away_team": "Boreal United",
                "home_goals": 3,
                "away_goals": 2,
            },
        ],
    }

    synthetic_fight: dict[str, Any] = {
        "event": "BetAgent MMA Night",
        "event_date": "2026-04-05T23:00:00Z",
        "fighter_a": {
            "name": "Carlos Mendes",
            "record": "25-3-0",
            "slpm": 4.8,
            "sapm": 3.1,
            "td_avg": 2.4,
            "sub_avg": 0.4,
            "str_acc": "49%",
            "str_def": "58%",
            "td_acc": "44%",
            "td_def": "71%",
        },
        "fighter_b": {
            "name": "Rafael Costa",
            "record": "18-5-0",
            "slpm": 3.9,
            "sapm": 3.3,
            "td_avg": 1.7,
            "sub_avg": 0.2,
            "str_acc": "46%",
            "str_def": "55%",
            "td_acc": "38%",
            "td_def": "64%",
        },
    }

    football_result: dict[str, Any] | None = run(synthetic_fixture, sport="football")
    mma_result: dict[str, Any] | None = run(synthetic_fight, sport="mma")

    print("[BetAgent][probability] Football sample:")
    print(json.dumps(football_result, indent=2, ensure_ascii=False))
    print("[BetAgent][probability] MMA sample:")
    print(json.dumps(mma_result, indent=2, ensure_ascii=False))
