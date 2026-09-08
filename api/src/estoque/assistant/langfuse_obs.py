"""Observador LangFuse. Opcional por construção.

Sem `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`, `criar()` devolve `None` e o
sistema usa o observador nulo. Nada quebra, nada avisa em vermelho — porque
telemetria ausente é uma perda de diagnóstico, não um resultado falso.

O que é registrado, e por quê:

  entrada/saída       o prompt e o schema — para reproduzir uma composição ruim
  tokens              custo é linear neles e o catálogo é o que mais pesa
  custo               relatado PELO PROVEDOR, não estimado por tabela de preço
  modo efetivo        se caímos de `restrito` para `ferramenta`, o número
                      medido pertence ao modo efetivo
  papel do ator       a mesma pergunta compõe diferente por papel; sem isso a
                      métrica agregada mistura experimentos distintos
  aceitos/rejeitados  a taxa de schema válido, que é a pergunta do projeto

O que NÃO é registrado: nenhuma linha de dado do estoque. O prompt já não
contém dados (ADR-0012), e o viewmodel não passa por aqui. Mandar dado de
cliente para um serviço de terceiro seria uma decisão de outra ordem.
"""

import logging
import os
from typing import Any

from estoque.assistant.trace import Trace

_log = logging.getLogger("estoque.observador")


class ObservadorLangfuse:
    def __init__(self, cliente: Any) -> None:
        self._c = cliente

    def composicao(
        self, *, trace: Trace, ator_id: str, papel: str | None, catalogo: int
    ) -> None:
        try:
            span = self._c.start_observation(
                as_type="generation",
                name="compor",
                model=trace.modelo,
                input=trace.pergunta,
                output=trace.resposta_bruta[:4000],
                usage_details={
                    "input": trace.tokens_entrada,
                    "output": trace.tokens_saida,
                },
                metadata={
                    "origem": trace.origem,
                    "modo_pedido": trace.modo,
                    "modo_efetivo": trace.modo_efetivo,
                    "provedor_efetivo": trace.provedor_efetivo,
                    "papel": papel,
                    "componentes_no_catalogo": catalogo,
                    "aceitos": trace.aceitos,
                    "rejeitados": trace.rejeitados,
                    "ms_total": trace.ms_total,
                    "erro": trace.erro,
                },
                **({"cost_details": {"total": trace.custo_usd}} if trace.custo_usd else {}),
            )
            span.update_trace(user_id=ator_id, tags=[trace.origem, trace.modo_efetivo])
            span.end()
            # A metrica que decide o projeto, como nota — para a serie historica
            # existir no painel e nao so' num relatorio.
            self._c.create_score(
                name="schema_valido", value=1.0 if trace.schema_valido else 0.0
            )
        except Exception:
            _log.warning("falha ao registrar no langfuse", exc_info=True)

    def nota(self, *, nome: str, valor: float, comentario: str = "") -> None:
        try:
            self._c.create_score(name=nome, value=valor, comment=comentario or None)
        except Exception:
            _log.warning("falha ao registrar nota", exc_info=True)

    def descarregar(self) -> None:
        try:
            self._c.flush()
        except Exception:
            _log.warning("falha ao descarregar", exc_info=True)


def criar() -> ObservadorLangfuse | None:
    """`None` quando não há chave ou o pacote não está instalado."""
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return None
    try:
        from langfuse import Langfuse
    except ImportError:
        _log.info("langfuse não instalado; seguindo sem observador")
        return None
    return ObservadorLangfuse(
        Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    )
