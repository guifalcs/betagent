from __future__ import annotations

from typing import Any


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_currency(value: Any) -> str:
    amount = _safe_float(value)
    if amount is None:
        amount = 0.0
    return f"R$ {amount:.2f}"


def _format_percent(value: Any) -> str:
    amount = _safe_float(value)
    if amount is None:
        amount = 0.0
    return f"{amount:.2f}%"


def _get_bets_from_section(section: Any) -> list[dict[str, Any]]:
    if isinstance(section, list):
        return [item for item in section if isinstance(item, dict)]

    if not isinstance(section, dict):
        return []

    for key in ("opportunities", "bets", "items"):
        value = section.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return []


def _build_opportunity_lines(title: str, bets: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = [f"## {title}"]

    if not bets:
        lines.append("Sem oportunidades.")
        return lines

    for bet in bets:
        outcome = str(bet.get("outcome") or "N/A")
        odd = bet.get("odd", "N/A")
        edge = _format_percent(bet.get("edge_percent", bet.get("edge")))
        stake = _format_currency(bet.get("stake"))
        lines.append(f"- {outcome} | odd {odd} | edge {edge} | stake {stake}")

    return lines


def _extract_result_label(bet: dict[str, Any]) -> str:
    won = bet.get("won")
    if isinstance(won, bool):
        return "✅ ganhou" if won else "❌ perdeu"

    result = str(bet.get("result") or "").strip().lower()
    if result in {"won", "win", "green", "ganhou", "won_bet"}:
        return "✅ ganhou"
    if result in {"lost", "loss", "red", "perdeu", "lost_bet"}:
        return "❌ perdeu"

    return "❌ perdeu"


def generate_daily(daily_result: dict[str, Any]) -> str | None:
    try:
        date = str(daily_result.get("date") or "N/A")
        football_bets = _get_bets_from_section(
            daily_result.get("football", daily_result.get("soccer"))
        )
        mma_bets = _get_bets_from_section(daily_result.get("mma"))
        total_opportunities = daily_result.get(
            "total_opportunities",
            len(football_bets) + len(mma_bets),
        )
        bankroll = _format_currency(daily_result.get("bankroll"))

        lines: list[str] = [f"📊 BetAgent — Relatório Diário {date}", ""]

        if not football_bets and not mma_bets:
            lines.append("✅ Nenhuma aposta com valor hoje.")
        else:
            lines.extend(_build_opportunity_lines("⚽ Oportunidades Futebol", football_bets))
            lines.append("")
            lines.extend(_build_opportunity_lines("🥊 Oportunidades MMA", mma_bets))

        lines.extend(
            [
                "",
                f"Total de oportunidades: {total_opportunities}",
                f"Bankroll: {bankroll}",
            ]
        )

        return "\n".join(lines)
    except Exception as exc:
        print(f"[BetAgent][report] Falha ao gerar relatório diário: {exc}")
        return None


def generate_post_mortem(pm_result: dict[str, Any]) -> str | None:
    try:
        date = str(pm_result.get("date") or "N/A")
        total_bets = pm_result.get("total_bets", 0)
        won = pm_result.get("won", pm_result.get("won_bets", 0))
        lost = pm_result.get("lost", pm_result.get("lost_bets", 0))
        roi = _format_percent(pm_result.get("roi_percent", pm_result.get("roi")))
        accuracy = _format_percent(
            pm_result.get("accuracy_percent", pm_result.get("accuracy"))
        )
        total_pnl = _format_currency(pm_result.get("total_pnl", pm_result.get("pnl")))

        raw_bets = pm_result.get("bets", pm_result.get("items", []))
        bets = [item for item in raw_bets if isinstance(item, dict)] if isinstance(raw_bets, list) else []

        lines: list[str] = [
            f"📋 BetAgent — Post-Mortem {date}",
            "",
            f"Total de apostas: {total_bets}",
            f"Vitórias: {won}",
            f"Derrotas: {lost}",
            f"ROI: {roi}",
            f"Accuracy: {accuracy}",
            "",
        ]

        if bets:
            for bet in bets:
                outcome = str(bet.get("outcome") or "N/A")
                result_label = _extract_result_label(bet)
                pnl = _format_currency(bet.get("pnl"))
                lines.append(f"- {outcome} | {result_label} | PnL {pnl}")
        else:
            lines.append("Nenhuma aposta liquidada no período.")

        lines.extend(["", f"PnL total: {total_pnl}"])

        return "\n".join(lines)
    except Exception as exc:
        print(f"[BetAgent][report] Falha ao gerar post-mortem: {exc}")
        return None


if __name__ == "__main__":
    print("Módulo report_generator disponível.")
