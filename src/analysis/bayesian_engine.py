from __future__ import annotations

import json
from typing import Any

from src.analysis import probability_engine


def _clamp_lr(lr: float) -> float:
    """Limita o fator de verossimilhança em uma faixa segura."""
    try:
        return max(0.70, min(1.35, lr))
    except Exception as exc:
        print(f"[BetAgent][bayesian] erro ao aplicar clamp de LR: {exc}")
        return 1.0


def _expert_lr(expert_data: dict[str, Any] | None) -> float:
    """Calcula o LR baseado no consenso de especialistas."""
    try:
        if not expert_data or "consensus_pct" not in expert_data:
            return 1.0

        consensus_pct = float(expert_data["consensus_pct"])
        lr = 0.80 + (0.45 * consensus_pct)
        return _clamp_lr(lr)
    except Exception as exc:
        print(f"[BetAgent][bayesian] erro ao calcular LR de especialistas: {exc}")
        return 1.0


def _sentiment_lr(sentiment_data: dict[str, Any] | None) -> float:
    """Calcula o LR a partir do sentimento e posicionamento do público."""
    try:
        if not sentiment_data or "public_pct_favorite" not in sentiment_data:
            return 1.0

        pct = float(sentiment_data["public_pct_favorite"])

        if pct > 0.80:
            lr = max(0.80, 1.0 - (pct - 0.80) * 2)
        elif 0.65 <= pct <= 0.80:
            lr = 1.0 - (pct - 0.65) * 0.33
        elif pct < 0.50:
            lr = min(1.10, 1.0 + (0.50 - pct) * 0.20)
        else:
            lr = 1.0

        return _clamp_lr(lr)
    except Exception as exc:
        print(f"[BetAgent][bayesian] erro ao calcular LR de sentimento: {exc}")
        return 1.0


def _news_lr(news_data: dict[str, Any] | None) -> float:
    """Calcula o LR com base no impacto qualitativo das notícias."""
    try:
        if not news_data or "impact" not in news_data:
            return 1.0

        impact_map = {
            "very_positive": 1.25,
            "positive": 1.10,
            "neutral": 1.0,
            "negative": 0.90,
            "very_negative": 0.75,
        }

        lr = impact_map.get(str(news_data["impact"]).lower(), 1.0)
        return _clamp_lr(lr)
    except Exception as exc:
        print(f"[BetAgent][bayesian] erro ao calcular LR de notícias: {exc}")
        return 1.0


def calculate_posterior(
    prior_prob: float,
    expert_data: dict[str, Any] | None,
    sentiment_data: dict[str, Any] | None,
    news_data: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Atualiza uma probabilidade prévia usando uma aproximação bayesiana por odds.

    A função converte a probabilidade inicial em odds, aplica fatores de
    verossimilhança derivados de consenso de especialistas, sentimento público
    e impacto de notícias, e depois reconverte o resultado para probabilidade.
    Isso permite ajustar o prior de forma multiplicativa, com clamps de segurança
    para evitar extremos artificiais.
    """
    try:
        if not 0 < prior_prob < 1:
            print(
                "[BetAgent][bayesian] erro: prior_prob deve estar estritamente entre 0 e 1"
            )
            return None

        lr_expert = _expert_lr(expert_data)
        lr_sentiment = _sentiment_lr(sentiment_data)
        lr_news = _news_lr(news_data)

        prior_odds = prior_prob / (1 - prior_prob)
        posterior_odds = prior_odds * lr_expert * lr_sentiment * lr_news
        posterior = posterior_odds / (1 + posterior_odds)
        posterior = max(0.01, min(0.99, posterior))

        return {
            "prior": round(prior_prob, 4),
            "posterior": round(posterior, 4),
            "lr_expert": round(lr_expert, 4),
            "lr_sentiment": round(lr_sentiment, 4),
            "lr_news": round(lr_news, 4),
            "method": "bayesian_update",
        }
    except Exception as exc:
        print(f"[BetAgent][bayesian] erro ao calcular posterior: {exc}")
        return None


if __name__ == "__main__":
    _ = probability_engine

    scenarios = [
        {
            "label": "cenario_1_todas_as_camadas",
            "prior": 0.58,
            "expert": {"consensus_pct": 0.80},
            "sentiment": {"public_pct_favorite": 0.72},
            "news": {"impact": "positive"},
        },
        {
            "label": "cenario_2_so_prior",
            "prior": 0.58,
            "expert": None,
            "sentiment": None,
            "news": None,
        },
        {
            "label": "cenario_3_fade_ativo",
            "prior": 0.55,
            "expert": {"consensus_pct": 0.50},
            "sentiment": {"public_pct_favorite": 0.85},
            "news": {"impact": "negative"},
        },
    ]

    for scenario in scenarios:
        result = calculate_posterior(
            prior_prob=scenario["prior"],
            expert_data=scenario["expert"],
            sentiment_data=scenario["sentiment"],
            news_data=scenario["news"],
        )

        payload = {
            "scenario": scenario["label"],
            "input": {
                "prior": scenario["prior"],
                "expert": scenario["expert"],
                "sentiment": scenario["sentiment"],
                "news": scenario["news"],
            },
            "result": result,
        }

        print(f"[BetAgent][bayesian] {scenario['label']}")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
