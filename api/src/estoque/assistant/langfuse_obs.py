"""Observador LangFuse. Opcional por construção, e agora exercitado de verdade.

Sem `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`, `criar()` devolve `None` e o
sistema usa o observador nulo. Nada quebra, nada avisa em vermelho — porque
telemetria ausente é uma perda de diagnóstico, não um resultado falso.

O que é registrado, e por quê:

  entrada/saída       a pergunta e o schema — para reproduzir uma composição ruim
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

---

**A duração das observações NÃO é a latência real, e isto é deliberado.**

O observador é chamado DEPOIS que a composição terminou (`app.py` monta o
`Trace` e só então nos entrega). O SDK v4 não aceita `start_time`/`end_time`
arbitrários, então uma árvore reconstruída aqui nasce com duração perto de
zero. Preencher esses milissegundos com número inventado seria exatamente o
erro que este projeto audita — a POC v1 publicou números de um parser simulado.

Por isso a latência real viaja como **nota numérica** (`latencia_ms`,
`ms_ate_primeiro_token`), que o painel do LangFuse plota em série histórica, e
o metadado `duracao_da_span_e_artificial` marca a árvore para quem for olhar.
Instrumentação ao vivo exige envolver o pipeline em `app.py` — é a T-043.
"""

import logging
import os
from typing import Any

from estoque.assistant.trace import Trace

_log = logging.getLogger("estoque.observador")

# Recorte do JSON bruto guardado no trace. O suficiente para reproduzir uma
# composicao ruim, longe do teto de payload do LangFuse.
_LIMITE_BRUTO = 4000


class ObservadorLangfuse:
    def __init__(self, cliente: Any, ambiente: str = "default") -> None:
        self._c = cliente
        self._ambiente = ambiente

    def composicao(
        self, *, trace: Trace, ator_id: str, papel: str | None, catalogo: int
    ) -> None:
        try:
            self._registrar(trace=trace, ator_id=ator_id, papel=papel, catalogo=catalogo)
        except Exception:
            # A telemetria nao pode derrubar a requisicao que ela observa. Mas
            # `warning` com stack e' o minimo: foi um `except` largo e mudo que
            # escondeu, por semanas, que `span.update_trace()` nao existe na v4.
            _log.warning("falha ao registrar no langfuse", exc_info=True)

    def _registrar(
        self, *, trace: Trace, ator_id: str, papel: str | None, catalogo: int
    ) -> None:
        from langfuse import propagate_attributes

        # `propagate_attributes` e' o caminho v4 para atributo de TRACE: marca
        # o span ativo e desce para todo filho criado no contexto. A ordem no
        # `with` importa — ele entra primeiro, e so' entao a raiz nasce, ja'
        # com os atributos.
        with (
            propagate_attributes(
                trace_name="compor-interface",
                user_id=ator_id,
                environment=self._ambiente,
                # Baixa cardinalidade, como manda a documentacao: dimensao que
                # se filtra num painel, nunca id nem nome de modelo.
                tags=[
                    trace.origem,
                    f"modo:{trace.modo_efetivo}",
                    f"papel:{papel or 'sem'}",
                ],
            ),
            self._c.start_as_current_observation(
                as_type="agent",
                name="compor-interface",
                # A raiz e' o que aparece na tabela de traces e alimenta
                # avaliador: a pergunta do usuario, nao o payload inteiro.
                input=trace.pergunta,
                metadata={
                    "papel": papel,
                    "componentes_no_catalogo": catalogo,
                    "provedor_efetivo": trace.provedor_efetivo,
                    "modo_pedido": trace.modo,
                    "modo_efetivo": trace.modo_efetivo,
                    "ms_total": trace.ms_total,
                    "ms_ate_primeiro_token": trace.ms_ate_primeiro_token,
                    # Ver a docstring do modulo. Sem esta marca, alguem vai
                    # abrir o painel de latencia e acreditar em zero.
                    "duracao_da_span_e_artificial": True,
                },
            ) as raiz,
        ):
            geracao = raiz.start_observation(
                as_type="generation",
                name="gerar-composicao",
                model=trace.modelo,
                input=trace.pergunta,
                output=trace.resposta_bruta[:_LIMITE_BRUTO],
                usage_details={
                    "input": trace.tokens_entrada,
                    "output": trace.tokens_saida,
                },
                **(
                    {"cost_details": {"total": trace.custo_usd}}
                    if trace.custo_usd is not None
                    else {}
                ),
            )
            geracao.end()

            # `guardrail`, e nao `span`: validar o schema contra o catalogo
            # DESTE ator e' literalmente a barreira da tese do projeto —
            # a saida do modelo autoriza renderizar, nunca escrever
            # (ADR-0002). Tipar como guardrail poe a rejeicao no grafo, em
            # vez de enterra-la num campo de metadata.
            barreira = raiz.start_observation(
                as_type="guardrail",
                name="validar-schema",
                input={"componentes_no_catalogo": catalogo},
                output={
                    "aceitos": trace.aceitos,
                    # Motivo junto: "rejeitou 2" nao diz nada; "rejeitou
                    # `custo_produto` porque nao esta no catalogo de Cleide"
                    # e' a evidencia que o projeto precisa.
                    "rejeitados": [{"componente": c, "motivo": m} for c, m in trace.rejeitados],
                },
                level="WARNING" if trace.rejeitados else "DEFAULT",
                status_message=trace.erro,
            )
            barreira.end()

            raiz.update(
                output={"aceitos": trace.aceitos, "erro": trace.erro},
                level="ERROR" if trace.erro else "DEFAULT",
                status_message=trace.erro,
            )

            # A metrica que decide o projeto (PRD secao 9), presa AO TRACE.
            # Antes era `create_score` solto, sem `trace_id`, depois de o
            # span ja' ter encerrado: a nota nao chegava a lugar nenhum.
            raiz.score_trace(
                name="schema_valido",
                value=1.0 if trace.schema_valido else 0.0,
                data_type="BOOLEAN",
            )
            # Latencia como nota, porque a duracao da span nao e' real.
            raiz.score_trace(name="latencia_ms", value=float(trace.ms_total))
            if trace.ms_ate_primeiro_token:
                raiz.score_trace(
                    name="ms_ate_primeiro_token",
                    value=float(trace.ms_ate_primeiro_token),
                )

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
            host=_host(),
        ),
        ambiente=os.environ.get("LANGFUSE_ENVIRONMENT", "default"),
    )


def _host() -> str:
    """`LANGFUSE_HOST` ou `LANGFUSE_BASE_URL` — os dois nomes existem.

    A CLI e a documentação do LangFuse usam `LANGFUSE_BASE_URL`; o SDK Python
    lê `LANGFUSE_HOST`. Ler só um dos dois foi um bug real e silencioso: o
    `.env` deste projeto trazia `LANGFUSE_BASE_URL` apontando para a nuvem dos
    EUA, o código leu `LANGFUSE_HOST`, não achou, e caiu no padrão da Europa.
    Chave dos EUA contra servidor da Europa nunca autentica — e como o erro
    era engolido, o ramo inteiro parecia "escrito mas nunca executado".
    """
    return (
        os.environ.get("LANGFUSE_HOST")
        or os.environ.get("LANGFUSE_BASE_URL")
        or "https://cloud.langfuse.com"
    )
