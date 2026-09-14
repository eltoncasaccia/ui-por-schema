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

**Dois caminhos, e só um tem duração real.**

`ao_vivo` (T-043, usado pela rota do assistente) abre a raiz ANTES do modelo e
envolve cada etapa enquanto ela acontece: a duração da span é o tempo do
trabalho. O SDK v4 não aceita `start_time`/`end_time` arbitrários, então este é
o único jeito de o painel de latência dizer a verdade.

`composicao` reconstrói a árvore DEPOIS do fato, para a eval, que só tem o
`Trace` pronto. Ali a duração nasce perto de zero, e o metadado
`duracao_da_span_e_artificial` marca a árvore; a latência real viaja como nota.
"""

import logging
import os
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from typing import Any

from estoque.assistant.observador import Etapa, EtapaNula, Observacao, ObservacaoNula
from estoque.assistant.trace import Trace

_log = logging.getLogger("estoque.observador")

# Recorte do JSON bruto guardado no trace. O suficiente para reproduzir uma
# composicao ruim, longe do teto de payload do LangFuse.
_LIMITE_BRUTO = 4000


def _saida_da_barreira(trace: Trace) -> dict[str, Any]:
    # Motivo junto: "rejeitou 2" nao diz nada; "rejeitou `custo_produto` porque
    # nao esta no catalogo de Cleide" e' a evidencia que o projeto precisa.
    return {
        "aceitos": trace.aceitos,
        "rejeitados": [{"componente": c, "motivo": m} for c, m in trace.rejeitados],
    }


def _detalhes_da_geracao(trace: Trace) -> dict[str, Any]:
    return {
        "model": trace.modelo,
        "input": trace.pergunta,
        "output": trace.resposta_bruta[:_LIMITE_BRUTO],
        "usage_details": {"input": trace.tokens_entrada, "output": trace.tokens_saida},
        **({"cost_details": {"total": trace.custo_usd}} if trace.custo_usd is not None else {}),
    }


def _notas(raiz: Any, trace: Trace) -> None:
    # A metrica que decide o projeto (PRD secao 9), presa AO TRACE — `create_score`
    # solto, sem `trace_id`, nao chegava a lugar nenhum (A-10).
    raiz.score_trace(
        name="schema_valido", value=1.0 if trace.schema_valido else 0.0, data_type="BOOLEAN"
    )
    raiz.score_trace(name="latencia_ms", value=float(trace.ms_total))
    if trace.ms_ate_primeiro_token:
        raiz.score_trace(name="ms_ate_primeiro_token", value=float(trace.ms_ate_primeiro_token))


class _EtapaViva:
    def __init__(self, obs: Any, tipo: str) -> None:
        self._obs = obs
        self._tipo = tipo

    def detalhar(self, *, trace: Trace) -> None:
        try:
            if self._tipo == "generation":
                self._obs.update(**_detalhes_da_geracao(trace))
            else:
                self._obs.update(
                    output=_saida_da_barreira(trace),
                    level="WARNING" if trace.rejeitados else "DEFAULT",
                    status_message=trace.erro,
                )
        except Exception:
            _log.warning("falha ao detalhar etapa no langfuse", exc_info=True)


class _ObservacaoViva:
    def __init__(self, cliente: Any, raiz: Any) -> None:
        self._c = cliente
        self._raiz = raiz

    @contextmanager
    def etapa(self, nome: str) -> Iterator[Etapa]:
        # `guardrail` para a validacao: e' literalmente a barreira da tese do
        # projeto (ADR-0002), e o tipo poe a rejeicao no grafo.
        tipo = "generation" if nome == "gerar-composicao" else "guardrail"
        try:
            cm = self._c.start_as_current_observation(as_type=tipo, name=nome)
            obs = cm.__enter__()
        except Exception:
            _log.warning("falha ao abrir etapa no langfuse", exc_info=True)
            yield EtapaNula()
            return
        try:
            yield _EtapaViva(obs, tipo)
        finally:
            try:
                cm.__exit__(None, None, None)
            except Exception:
                _log.warning("falha ao fechar etapa no langfuse", exc_info=True)

    def concluir(self, *, trace: Trace, catalogo: int) -> None:
        try:
            self._raiz.update(
                output={"aceitos": trace.aceitos, "erro": trace.erro},
                level="ERROR" if trace.erro else "DEFAULT",
                status_message=trace.erro,
                metadata={
                    "componentes_no_catalogo": catalogo,
                    "provedor_efetivo": trace.provedor_efetivo,
                    "modo_pedido": trace.modo,
                    "modo_efetivo": trace.modo_efetivo,
                    "origem": trace.origem,
                },
            )
            _notas(self._raiz, trace)
        except Exception:
            _log.warning("falha ao concluir observacao no langfuse", exc_info=True)


class ObservadorLangfuse:
    def __init__(self, cliente: Any, ambiente: str = "default") -> None:
        self._c = cliente
        self._ambiente = ambiente

    @contextmanager
    def ao_vivo(
        self, *, pergunta: str, ator_id: str, papel: str | None
    ) -> Iterator[Observacao]:
        """Falha ao ABRIR degrada para o nulo; excecao do CORPO atravessa intacta."""
        pilha = ExitStack()
        try:
            from langfuse import propagate_attributes

            # Entra primeiro, para a raiz ja' nascer com os atributos de trace.
            pilha.enter_context(
                propagate_attributes(
                    trace_name="compor-interface",
                    user_id=ator_id,
                    environment=self._ambiente,
                    tags=[f"papel:{papel or 'sem'}"],
                )
            )
            raiz = pilha.enter_context(
                self._c.start_as_current_observation(
                    as_type="agent",
                    name="compor-interface",
                    input=pergunta,
                    metadata={"papel": papel},
                )
            )
        except Exception:
            _log.warning("falha ao abrir observacao no langfuse", exc_info=True)
            try:
                pilha.close()
            except Exception:
                _log.warning("falha ao fechar observacao no langfuse", exc_info=True)
            yield ObservacaoNula()
            return
        try:
            yield _ObservacaoViva(self._c, raiz)
        finally:
            try:
                pilha.close()
            except Exception:
                _log.warning("falha ao fechar observacao no langfuse", exc_info=True)

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

        with (
            propagate_attributes(
                trace_name="compor-interface",
                user_id=ator_id,
                environment=self._ambiente,
                # Baixa cardinalidade: dimensao que se filtra num painel.
                tags=[trace.origem, f"modo:{trace.modo_efetivo}", f"papel:{papel or 'sem'}"],
            ),
            self._c.start_as_current_observation(
                as_type="agent",
                name="compor-interface",
                input=trace.pergunta,
                metadata={
                    "papel": papel,
                    "componentes_no_catalogo": catalogo,
                    "provedor_efetivo": trace.provedor_efetivo,
                    "modo_pedido": trace.modo,
                    "modo_efetivo": trace.modo_efetivo,
                    "ms_total": trace.ms_total,
                    "ms_ate_primeiro_token": trace.ms_ate_primeiro_token,
                    # Caminho pos-fato: sem esta marca, alguem abre o painel de
                    # latencia e acredita em zero.
                    "duracao_da_span_e_artificial": True,
                },
            ) as raiz,
        ):
            raiz.start_observation(
                as_type="generation", name="gerar-composicao", **_detalhes_da_geracao(trace)
            ).end()
            raiz.start_observation(
                as_type="guardrail",
                name="validar-schema",
                input={"componentes_no_catalogo": catalogo},
                output=_saida_da_barreira(trace),
                level="WARNING" if trace.rejeitados else "DEFAULT",
                status_message=trace.erro,
            ).end()
            raiz.update(
                output={"aceitos": trace.aceitos, "erro": trace.erro},
                level="ERROR" if trace.erro else "DEFAULT",
                status_message=trace.erro,
            )
            _notas(raiz, trace)

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
    """
    return (
        os.environ.get("LANGFUSE_HOST")
        or os.environ.get("LANGFUSE_BASE_URL")
        or "https://cloud.langfuse.com"
    )
