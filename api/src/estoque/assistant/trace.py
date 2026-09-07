"""Execution Trace. O que a v1 mais acertou: tornar visivel o que foi rejeitado.

Um componente nao registrado e' rejeitado e APARECE AQUI. Um filtro que falta
apenas alarga a resposta em silencio — por isso a auditoria de enums da suite de
avaliacao existe (risco R-5 do PRD).
"""

from dataclasses import dataclass, field
from typing import Literal

Origem = Literal["openrouter", "anthropic", "mock"]
Modo = Literal["restrito", "livre"]


@dataclass(slots=True)
class Trace:
    """Registro de uma composicao, do prompt ao schema validado."""

    origem: Origem
    modelo: str
    pergunta: str
    modo: Modo = "restrito"
    provedor_efetivo: str = ""
    tokens_entrada: int = 0
    tokens_saida: int = 0
    ms_ate_primeiro_token: int = 0
    ms_total: int = 0
    resposta_bruta: str = ""
    aceitos: list[str] = field(default_factory=list)
    rejeitados: list[tuple[str, str]] = field(default_factory=list)
    erro: str | None = None

    @property
    def schema_valido(self) -> bool:
        """A metrica que decide o projeto (PRD secao 9)."""
        return self.erro is None and bool(self.aceitos)

    def resumo(self) -> dict[str, object]:
        return {
            "origem": self.origem,
            "modelo": self.modelo,
            "modo": self.modo,
            "provedor_efetivo": self.provedor_efetivo,
            "schema_valido": self.schema_valido,
            "aceitos": self.aceitos,
            "rejeitados": self.rejeitados,
            "tokens_entrada": self.tokens_entrada,
            "ms_ate_primeiro_token": self.ms_ate_primeiro_token,
            "erro": self.erro,
        }
