from __future__ import annotations

from typing import Any

import requests

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.reporting import report_generator


def send(text: str) -> bool:
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("[BetAgent][telegram] TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID ausentes.")
            return False

        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
            },
            timeout=15,
        )

        if response.status_code != 200:
            print(
                f"[BetAgent][telegram] Falha no envio. Status HTTP: {response.status_code}"
            )
            return False

        payload = response.json()
        success = bool(payload.get("ok"))

        if not success:
            print("[BetAgent][telegram] Telegram retornou ok=False.")

        return success
    except Exception as exc:
        print(f"[BetAgent][telegram] Erro ao enviar mensagem: {exc}")
        return False


def send_daily_report(daily_result: dict[str, Any]) -> bool:
    try:
        text = report_generator.generate_daily(daily_result)
        if not text:
            print("[BetAgent][telegram] Relatório diário vazio ou inválido.")
            return False
        return send(text)
    except Exception as exc:
        print(f"[BetAgent][telegram] Falha ao enviar relatório diário: {exc}")
        return False


def send_post_mortem_report(pm_result: dict[str, Any]) -> bool:
    try:
        text = report_generator.generate_post_mortem(pm_result)
        if not text:
            print("[BetAgent][telegram] Post-mortem vazio ou inválido.")
            return False
        return send(text)
    except Exception as exc:
        print(f"[BetAgent][telegram] Falha ao enviar post-mortem: {exc}")
        return False


if __name__ == "__main__":
    print("Módulo telegram_sender disponível.")
