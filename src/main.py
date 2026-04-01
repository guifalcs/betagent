"""Expõe a entrada principal de linha de comando para os fluxos do projeto."""

from __future__ import annotations

import argparse
import datetime
import json
from typing import Sequence

from src.collectors import (
    news_collector,
    odds_collector,
    social_collector,
    stats_collector,
)
from src.flows import daily_report, post_mortem, revalidate


def run_daily() -> None:
    """Executa o fluxo de relatório diário."""
    print("[BetAgent] Fluxo diário iniciado.")

    try:
        result = daily_report.run()
        if result:
            football_opportunities = result.get("football_opportunities") or []
            mma_opportunities = result.get("mma_opportunities") or []
            print("\n" + "=" * 60)
            print("[BetAgent] RESUMO DO FLUXO DIÁRIO")
            print("=" * 60)
            print(f"  Data:                 {result.get('date', '-')}")
            print(f"  Oportunidades totais: {result.get('total_opportunities', 0)}")
            print(f"  Futebol:              {len(football_opportunities)}")
            print(f"  MMA:                  {len(mma_opportunities)}")
            print(f"  Bankroll:             {result.get('bankroll', 0)}")
            print(f"  Kelly scale:          {result.get('kelly_scale', 0)}")
            print("=" * 60)
        else:
            print("[BetAgent] Falha ao executar o fluxo diário.")
    except Exception as exc:
        print(f"[BetAgent] Falha no fluxo diário: {exc}")


def run_check(event: str) -> None:
    """Executa a revalidação pré-aposta para um evento."""
    try:
        result = revalidate.run(event_name=event, probs={}, bankroll=1000.0)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"[BetAgent] Falha na revalidação para {event}: {exc}")


def run_postmortem(date: str = datetime.date.today().isoformat()) -> None:
    """Executa o fluxo de post-mortem automático."""
    try:
        result = post_mortem.run(date=date, bets=[])
        if result:
            print(json.dumps(result.get("metrics"), ensure_ascii=False, indent=2))
        else:
            print(f"[BetAgent] Falha ao executar o post-mortem para {date}.")
    except Exception as exc:
        print(f"[BetAgent] Falha no post-mortem para {date}: {exc}")


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
    parser.add_argument(
        "--date",
        metavar="DATE",
        type=str,
        help="Data de referência para o post-mortem no formato ISO (YYYY-MM-DD).",
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

    if args.postmortem:
        run_postmortem(args.date or datetime.date.today().isoformat())
        return 0

    parser.print_usage()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
