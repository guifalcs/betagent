"""Expõe a entrada principal de linha de comando para os fluxos do projeto."""

from __future__ import annotations

import argparse
from typing import Sequence

from src.collectors import (
    news_collector,
    odds_collector,
    social_collector,
    stats_collector,
)


def run_daily() -> None:
    """Executa o fluxo de relatório diário."""
    print("[BetAgent] Fluxo diário iniciado.")

    odds: list[dict[str, object]] | None = None
    football_stats: list[dict[str, object]] | None = None
    mma_stats: list[dict[str, object]] | None = None
    sentiments: list[dict[str, object]] = []
    news_football: list[dict[str, object]] | None = None
    news_mma: list[dict[str, object]] | None = None

    try:
        odds = odds_collector.run()
    except Exception as exc:
        print(f"[BetAgent] Aviso: falha no odds_collector: {exc}")

    try:
        football_stats = stats_collector.run(sport="football")
    except Exception as exc:
        print(f"[BetAgent] Aviso: falha no stats_collector (football): {exc}")

    try:
        mma_stats = stats_collector.run(sport="mma")
    except Exception as exc:
        print(f"[BetAgent] Aviso: falha no stats_collector (mma): {exc}")

    if odds:
        for event in odds[:5]:
            try:
                home_team = str(event.get("home_team", ""))
                away_team = str(event.get("away_team", ""))
                match_name = f"{home_team} {away_team}".strip()
                if not match_name:
                    continue

                sentiment = social_collector.run(event=match_name)
                if sentiment:
                    sentiments.append(sentiment)
            except Exception as exc:
                print(f"[BetAgent] Aviso: falha no social_collector para evento: {exc}")

    try:
        news_football = news_collector.run(event="futebol", sport="football")
    except Exception as exc:
        print(f"[BetAgent] Aviso: falha no news_collector (football): {exc}")

    try:
        news_mma = news_collector.run(event="UFC", sport="mma")
    except Exception as exc:
        print(f"[BetAgent] Aviso: falha no news_collector (mma): {exc}")

    print("\n" + "=" * 60)
    print("[BetAgent] RESUMO DO FLUXO DIÁRIO")
    print("=" * 60)
    print(f"  Odds coletadas: {len(odds) if odds else 0} eventos")
    print(f"  Stats futebol:  {len(football_stats) if football_stats else 0} fixtures")
    print(f"  Stats MMA:      {len(mma_stats) if mma_stats else 0} lutas")
    print(f"  Sentimento:     {len(sentiments)} consultas")
    print(f"  Notícias:       {len(news_football or []) + len(news_mma or [])} artigos")
    print("=" * 60)
    print("[BetAgent] Fluxo diário concluído. Modelo de probabilidades ainda não implementado.")


def run_check(event: str) -> None:
    """Executa a revalidação pré-aposta para um evento."""
    print(
        f"[BetAgent] Revalidação iniciada para: {event}. "
        "Nenhum coletor implementado ainda."
    )


def run_postmortem() -> None:
    """Executa o fluxo de post-mortem automático."""
    print("[BetAgent] Fluxo de post-mortem iniciado. Nenhum coletor implementado ainda.")


def build_parser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos da CLI."""
    parser = argparse.ArgumentParser(prog="python -m src.main")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--daily", action="store_true", help="Executa o fluxo diário.")
    group.add_argument(
        "--check",
        metavar="EVENT",
        type=str,
        help="Executa a revalidação para um evento específico.",
    )
    group.add_argument(
        "--postmortem",
        action="store_true",
        help="Executa o fluxo de post-mortem.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Processa os argumentos da CLI e executa o modo selecionado."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not any((args.daily, args.check, args.postmortem)):
        parser.print_usage()
        return 1

    if args.daily:
        run_daily()
        return 0

    if args.check:
        run_check(args.check)
        return 0

    run_postmortem()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
