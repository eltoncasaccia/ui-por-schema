"""Execution Trace. O que a v1 mais acertou: tornar visivel o que foi rejeitado.

Um componente nao registrado e' rejeitado e APARECE AQUI. Um filtro que falta
apenas alarga a resposta em silencio — por isso a auditoria de enums da suite de
avaliacao existe (risco R-5 do PRD).
"""

from dataclasses import dataclass, field
from typing import Literal

Origem = Literal["openrouter", "anthropic", "compativel", "mock"]

# Tres formas de restringir a saida, em ordem de suporte crescente:
#
#   restrito    `response_format: json_schema` — o melhor, nem todo provedor tem
#   ferramenta  tool calling — suporte mais amplo, uma indirecao a mais
#   livre       JSON solto — funciona em qualquer lugar, e e' o que mede a
#               pergunta original da v1: com que frequencia o modelo acerta
#               sozinho
Modo = Literal["restrito", "ferramenta", "livre"]


@dataclass(slots=True)
class Trace:
    """Registro de uma composicao, do prompt ao schema validado."""

    origem: Origem
    modelo: str
    pergunta: str
    modo: Modo = "restrito"
    # Modo REALMENTE usado. Se o provedor recusa `json_schema` e caimos para
    # ferramenta, o numero medido pertence ao modo efetivo — publicar sob o
    # modo pedido seria atribuir o resultado ao experimento errado.
    modo_efetivo: Modo = "restrito"
    provedor_efetivo: str = ""
    # Custo relatado PELO PROVEDOR, em USD. Nao estimamos por tabela de preco:
    # tabela envelhece e o roteador pode servir por caminhos de preco diferente.
    custo_usd: float | None = None
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
            "modo_efetivo": self.modo_efetivo,
            "provedor_efetivo": self.provedor_efetivo,
            "tokens_saida": self.tokens_saida,
            "custo_usd": self.custo_usd,
            "ms_total": self.ms_total,
            "schema_valido": self.schema_valido,
            "aceitos": self.aceitos,
            "rejeitados": self.rejeitados,
            "tokens_entrada": self.tokens_entrada,
            "ms_ate_primeiro_token": self.ms_ate_primeiro_token,
            "erro": self.erro,
        }
