"""Coleta mencoes em redes sociais via Apify e resume sentimento por evento."""

from __future__ import annotations

import argparse
import json
from typing import Any

from apify_client import ApifyClient

from config.settings import APIFY_TOKEN


ACTORS = (
    "apidojo/tweet-scraper",
    "quacker/twitter-scraper",
)
ACTOR_TIMEOUT_SECS = 60
POSITIVE_TERMS = (
    "win",
    "vai ganhar",
    "favorito",
    "vence",
    "melhor",
)
NEGATIVE_TERMS = (
    "perde",
    "vai perder",
    "fraco",
    "ruim",
    "lesao",
    "machucado",
)


def _build_empty_result(event: str) -> dict[str, Any]:
    """Retorna a estrutura padrao vazia para o coletor social."""
    return {
        "event": event,
        "total_tweets": 0,
        "positive": 0,
        "negative": 0,
        "neutral": 0,
        "positive_pct": 0.0,
        "negative_pct": 0.0,
        "sample_tweets": [],
    }


def _extract_tweet_text(item: dict[str, Any]) -> str:
    """Extrai o texto mais provavel de um tweet vindo de actors distintos."""
    candidate_keys = (
        "text",
        "full_text",
        "fullText",
        "tweetText",
        "tweet_text",
        "content",
    )
    for key in candidate_keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    legacy_tweet = item.get("tweet")
    if isinstance(legacy_tweet, dict):
        for key in candidate_keys:
            value = legacy_tweet.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def _classify_sentiment(text: str) -> str:
    """Classifica o sentimento basico do tweet como positive, negative ou neutral."""
    normalized = text.lower()
    positive_hits = sum(1 for term in POSITIVE_TERMS if term in normalized)
    negative_hits = sum(1 for term in NEGATIVE_TERMS if term in normalized)

    if positive_hits > negative_hits:
        return "positive"
    if negative_hits > positive_hits:
        return "negative"
    return "neutral"


def _build_actor_input(actor_id: str, event: str) -> dict[str, Any]:
    """Monta o payload de entrada para cada actor suportado."""
    if actor_id == "apidojo/tweet-scraper":
        return {
            "searchTerms": [event],
            "maxItems": 100,
            "sort": "Latest",
        }

    return {
        "searchTerms": [event],
        "maxItems": 100,
    }


def _run_actor(client: ApifyClient, actor_id: str, event: str) -> tuple[list[dict[str, Any]], str | None]:
    """Executa um actor do Apify e retorna os itens do dataset e eventual aviso."""
    actor_input = _build_actor_input(actor_id, event)
    run = client.actor(actor_id).call(
        run_input=actor_input,
        timeout_secs=ACTOR_TIMEOUT_SECS,
        wait_secs=ACTOR_TIMEOUT_SECS,
        logger=None,
    )

    if run is None:
        return [], (
            f"Actor {actor_id} excedeu {ACTOR_TIMEOUT_SECS}s e foi abortado."
        )

    dataset_id = run.get("defaultDatasetId")
    status_message = " ".join(str(run.get("statusMessage") or "").split())
    if not dataset_id:
        return [], f"Actor {actor_id} terminou sem dataset de saida."

    items = client.dataset(dataset_id).list_items().items
    if not items:
        warning = status_message or f"Actor {actor_id} nao retornou tweets."
        return [], warning

    if len(items) == 1 and isinstance(items[0], dict) and items[0].get("noResults") is True:
        warning = status_message or f"Actor {actor_id} nao encontrou resultados."
        return [], warning

    return items, status_message or None


def _summarize_tweets(event: str, tweets: list[str]) -> dict[str, Any]:
    """Resume os tweets em contagens de sentimento e amostras de texto."""
    result = _build_empty_result(event)
    result["total_tweets"] = len(tweets)
    result["sample_tweets"] = tweets[:5]

    for tweet in tweets:
        sentiment = _classify_sentiment(tweet)
        result[sentiment] += 1

    total = result["total_tweets"]
    if total > 0:
        result["positive_pct"] = round(result["positive"] / total, 2)
        result["negative_pct"] = round(result["negative"] / total, 2)

    return result


def _print_summary(summary: dict[str, Any], actor_id: str | None = None, warning: str | None = None) -> None:
    """Printa um resumo legivel da coleta social."""
    print(f"[BetAgent][social] Evento: {summary['event']}")
    if actor_id:
        print(f"[BetAgent][social] Actor usado: {actor_id}")
    if warning:
        print(f"[BetAgent][social] Aviso: {warning}")
    print(
        "[BetAgent][social] Tweets: "
        f"{summary['total_tweets']} | positivos: {summary['positive']} "
        f"({summary['positive_pct']}) | negativos: {summary['negative']} "
        f"({summary['negative_pct']}) | neutros: {summary['neutral']}"
    )
    if summary["sample_tweets"]:
        print("[BetAgent][social] Exemplos:")
        for tweet in summary["sample_tweets"]:
            print(f"[BetAgent][social]   - {tweet}")


def run(event: str) -> dict[str, Any] | None:
    """Busca tweets sobre um evento no Apify e resume o sentimento basico."""
    try:
        if not APIFY_TOKEN:
            print("[BetAgent][social] APIFY_TOKEN ausente. Configure o .env antes de rodar.")
            return None

        client = ApifyClient(APIFY_TOKEN)
        warnings: list[str] = []

        for actor_id in ACTORS:
            try:
                print(f"[BetAgent][social] Tentando actor {actor_id} para '{event}'...")
                items, warning = _run_actor(client, actor_id, event)
                if warning:
                    warnings.append(f"{actor_id}: {warning}")

                tweets = [
                    text
                    for text in (_extract_tweet_text(item) for item in items)
                    if text
                ]
                if tweets:
                    summary = _summarize_tweets(event, tweets)
                    _print_summary(summary, actor_id=actor_id, warning=warning)
                    return summary

                print(
                    f"[BetAgent][social] Actor {actor_id} nao retornou tweets utilizaveis."
                )
            except Exception as exc:
                warnings.append(f"{actor_id}: {exc}")
                print(f"[BetAgent][social] Falha ao usar actor {actor_id}: {exc}")
                continue

        warning_message = (
            "Nenhum actor retornou tweets. "
            + " | ".join(warnings)
            if warnings
            else "Nenhum actor retornou tweets."
        )
        empty_result = _build_empty_result(event)
        _print_summary(empty_result, warning=warning_message)
        return empty_result
    except Exception as exc:
        print(f"[BetAgent][social] Falha total na coleta social: {exc}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.event), indent=2, ensure_ascii=False))
