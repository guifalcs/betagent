"""Coleta noticias esportivas recentes via Apify com filtro de relevancia por evento."""

from __future__ import annotations

import argparse
import json
from typing import Any

from apify_client import ApifyClient

from config.settings import APIFY_TOKEN


ACTOR_ID = "apify/website-content-crawler"
ACTOR_TIMEOUT_SECS = 60
SPORT_SITES = {
    "football": [
        "https://ge.globo.com/futebol/",
        "https://www.espn.com.br/futebol/",
    ],
    "mma": [
        "https://www.mmafighting.com/",
        "https://mmajunkie.usatoday.com/",
    ],
}


def _get_sites_for_sport(sport: str) -> list[str]:
    """Retorna as URLs iniciais para o esporte informado."""
    return SPORT_SITES.get(sport, [])


def _build_actor_input(start_url: str) -> dict[str, Any]:
    """Monta o payload de entrada do website-content-crawler."""
    return {
        "startUrls": [{"url": start_url}],
        "maxCrawlPages": 5,
        "maxCrawlDepth": 1,
        "proxyConfiguration": {"useApifyProxy": True},
        "crawlerType": "cheerio",
        "htmlTransformer": "readableText",
    }


def _truncate_text(text: str, limit: int = 500) -> str:
    """Limita o texto retornado a um tamanho maximo amigavel para leitura."""
    normalized = " ".join(text.split())
    return normalized[:limit]


def _is_relevant(event: str, title: str, text: str) -> bool:
    """Determina se o termo do evento aparece no titulo ou no texto."""
    event_term = event.lower().strip()
    return event_term in title.lower() or event_term in text.lower()


def _normalize_article(item: dict[str, Any], event: str) -> dict[str, Any]:
    """Normaliza uma pagina crawleada para a estrutura esperada pelo projeto."""
    metadata = item.get("metadata", {})
    title = str(metadata.get("title") or "")
    url = str(item.get("url") or "")
    text = _truncate_text(str(item.get("text") or ""))
    relevance = _is_relevant(event, title, text)

    return {
        "title": title,
        "url": url,
        "text": text,
        "relevance": relevance,
    }


def _run_actor(client: ApifyClient, start_url: str) -> list[dict[str, Any]]:
    """Executa o actor de crawling para um site e retorna os itens do dataset."""
    run = client.actor(ACTOR_ID).call(
        run_input=_build_actor_input(start_url),
        timeout_secs=ACTOR_TIMEOUT_SECS,
        wait_secs=ACTOR_TIMEOUT_SECS,
        logger=None,
    )
    if run is None:
        raise TimeoutError(
            f"Actor {ACTOR_ID} excedeu {ACTOR_TIMEOUT_SECS}s ao processar {start_url}."
        )

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise ValueError(f"Actor {ACTOR_ID} terminou sem dataset para {start_url}.")

    return client.dataset(dataset_id).list_items().items


def _print_article(article: dict[str, Any]) -> None:
    """Printa titulo e trecho de um artigo relevante."""
    print(f"[BetAgent][news] {article['title']}")
    print(f"[BetAgent][news] URL: {article['url']}")
    print(f"[BetAgent][news] Trecho: {article['text']}")


def run(event: str, sport: str = "football") -> list[dict[str, Any]] | None:
    """Coleta noticias recentes e filtra artigos relevantes para o evento."""
    try:
        if not APIFY_TOKEN:
            print("[BetAgent][news] APIFY_TOKEN ausente. Configure o .env antes de rodar.")
            return None

        sites = _get_sites_for_sport(sport)
        if not sites:
            print(f"[BetAgent][news] Nenhum site configurado para o esporte '{sport}'.")
            return []

        client = ApifyClient(APIFY_TOKEN)
        relevant_articles: list[dict[str, Any]] = []

        for start_url in sites:
            try:
                print(f"[BetAgent][news] Crawling em {start_url} para '{event}'...")
                items = _run_actor(client, start_url)
                articles = [_normalize_article(item, event) for item in items]
                matches = [article for article in articles if article["relevance"]]
                relevant_articles.extend(matches)
                print(
                    f"[BetAgent][news] {len(matches)} artigo(s) relevante(s) encontrado(s) em {start_url}."
                )
            except Exception as exc:
                print(f"[BetAgent][news] Falha ao processar {start_url}: {exc}")
                continue

        if not relevant_articles:
            print(f"[BetAgent][news] Nenhum artigo relevante encontrado para '{event}'.")
            return []

        print(
            f"[BetAgent][news] Total de artigos relevantes para '{event}': "
            f"{len(relevant_articles)}"
        )
        for article in relevant_articles:
            _print_article(article)

        return relevant_articles
    except Exception as exc:
        print(f"[BetAgent][news] Falha total na coleta de noticias: {exc}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--sport", default="football")
    args = parser.parse_args()
    print(json.dumps(run(args.event, args.sport), indent=2, ensure_ascii=False))
