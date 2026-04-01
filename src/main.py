"""Expõe a entrada principal de linha de comando para os fluxos do projeto."""

from __future__ import annotations

import argparse
from typing import Sequence


def run_daily() -> None:
    """Executa o fluxo de relatório diário."""
    print("[BetAgent] Fluxo diário iniciado. Nenhum coletor implementado ainda.")


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
