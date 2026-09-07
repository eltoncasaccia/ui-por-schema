"""Configuracao por ambiente."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Config:
    database_url: str
    sessao_secret: str
    modo_demo: bool
    cors_origin: str
    modelo: str
    modo_decodificacao: str

    @staticmethod
    def do_ambiente() -> "Config":
        return Config(
            database_url=os.environ.get(
                "DATABASE_URL",
                "postgresql+asyncpg://estoque:troque-isto@localhost:15432/estoque",
            ),
            sessao_secret=os.environ.get("SESSAO_SECRET", "dev-inseguro"),
            modo_demo=os.environ.get("MODO_DEMO", "true").lower() == "true",
            cors_origin=os.environ.get("CORS_ORIGIN", "http://localhost:5173"),
            modelo=os.environ.get("MODELO_ASSISTENTE", "anthropic/claude-haiku-4.5"),
            modo_decodificacao=os.environ.get("MODO_DECODIFICACAO", "restrito"),
        )
