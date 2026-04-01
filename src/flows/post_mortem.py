from __future__ import annotations

from typing import Any

from src.analysis import post_mortem_engine
from src.collectors import results_collector


def run(date: str, bets: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        print("[BetAgent][flow] Iniciando fluxo post_mortem.")

        results = results_collector.run(date, sport="all")
        if results is None:
            return None

        post_mortem = post_mortem_engine.run(bets, results)
        if not isinstance(post_mortem, dict):
            return None

        post_mortem["date"] = date

        print("[BetAgent][flow] Fluxo post_mortem concluido.")
        return post_mortem
    except Exception as exc:
        print(f"[BetAgent][flow] Falha no fluxo post_mortem: {exc}")
        return None


if __name__ == "__main__":
    print("Fluxo post_mortem disponível — use via src.main ou importe run().")
