"""Centraliza a criacao singleton do client do Supabase para o projeto."""

from __future__ import annotations

from supabase import Client, create_client

from config.settings import SUPABASE_KEY, SUPABASE_URL


_client: Client | None = None


def get_client() -> Client:
    """Retorna uma instancia singleton do client do Supabase."""
    global _client

    if _client is None:
        try:
            _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as exc:
            raise RuntimeError(
                "Falha ao criar o client do Supabase com as configuracoes atuais."
            ) from exc

    return _client
