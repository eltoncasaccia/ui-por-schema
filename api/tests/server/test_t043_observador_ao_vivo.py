"""T-043 — instrumentacao ao vivo: a duracao das spans e' a do trabalho real.

O LangFuse entra por um cliente FALSO que mede enter/exit com relogio real —
nada sai da maquina (ADR-0026). O que prende o falso ao SDK de verdade e' o
AC-7: os metodos e parametros usados existem na versao instalada. Assinatura
inventada que compila e so' quebra em execucao ja' custou tres defeitos (A-10).
"""

import asyncio
import inspect
import logging
import time
from collections.abc import AsyncGenerator, Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

import pytest
from borda import cliente, criar_sessao, descartar_pool

from estoque.assistant import langfuse_obs
from estoque.assistant.adapter import AdaptadorMock, Resposta
from estoque.assistant.langfuse_obs import ObservadorLangfuse
from estoque.assistant.trace import Modo, Trace
from estoque.server.rotas import assistente

ATRASO_S = 0.05


class ObsFalsa:
    def __init__(
        self, as_type: str, name: str, pai: "ObsFalsa | None", kw: dict[str, Any]
    ) -> None:
        self.as_type = as_type
        self.name = name
        self.pai = pai
        self.kw = kw
        self.inicio = 0.0
        self.fim = 0.0
        self.updates: list[dict[str, Any]] = []
        self.notas: list[dict[str, Any]] = []

    @property
    def duracao(self) -> float:
        return self.fim - self.inicio

    def update(self, **kw: Any) -> None:
        self.updates.append(kw)

    def score_trace(self, **kw: Any) -> None:
        self.notas.append(kw)

    def start_observation(self, *, as_type: str, name: str, **kw: Any) -> "ObsFalsa":
        return ObsFalsa(as_type, name, self, kw)

    def end(self) -> None:
        return


class ObsQueQuebra(ObsFalsa):
    def update(self, **kw: Any) -> None:
        raise RuntimeError("payload recusado")

    def score_trace(self, **kw: Any) -> None:
        raise RuntimeError("payload recusado")


class LangfuseFalso:
    """Imita `start_as_current_observation`: aninha pelo contexto, mede com relogio real."""

    def __init__(self) -> None:
        self.registro: list[ObsFalsa] = []
        self.scores_soltos: list[dict[str, Any]] = []
        self._pilha: list[ObsFalsa] = []

    @contextmanager
    def start_as_current_observation(
        self, *, as_type: str, name: str, **kw: Any
    ) -> Iterator[ObsFalsa]:
        obs = self._nova(as_type, name, kw)
        self._pilha.append(obs)
        obs.inicio = time.perf_counter()
        try:
            yield obs
        finally:
            obs.fim = time.perf_counter()
            self._pilha.pop()

    def _nova(self, as_type: str, name: str, kw: dict[str, Any]) -> ObsFalsa:
        obs = ObsFalsa(as_type, name, self._pilha[-1] if self._pilha else None, kw)
        self.registro.append(obs)
        return obs

    def create_score(self, **kw: Any) -> None:
        self.scores_soltos.append(kw)

    def flush(self) -> None:
        return

    def por_nome(self) -> dict[str, ObsFalsa]:
        return {o.name: o for o in self.registro}


class LangfuseQueQuebraNoMeio(LangfuseFalso):
    def _nova(self, as_type: str, name: str, kw: dict[str, Any]) -> ObsFalsa:
        obs = ObsQueQuebra(as_type, name, self._pilha[-1] if self._pilha else None, kw)
        self.registro.append(obs)
        return obs


class LangfuseFora:
    def start_as_current_observation(self, **kw: Any) -> Any:
        raise RuntimeError("langfuse fora do ar")


class AdaptadorLento:
    async def compor(
        self, pergunta: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo = "restrito"
    ) -> Resposta:
        await asyncio.sleep(ATRASO_S)
        return await AdaptadorMock().compor(pergunta, catalogo, modo=modo)


class AdaptadorQueFalha:
    async def compor(
        self, pergunta: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo = "restrito"
    ) -> Resposta:
        r = await AdaptadorMock().compor(pergunta, catalogo, modo=modo)
        r.trace.erro = "ReadTimeout"
        return r


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


@pytest.fixture(autouse=True)
def _limite_limpo() -> Iterator[None]:
    assistente.LIMITE._por_chave.clear()
    yield
    assistente.LIMITE._por_chave.clear()


async def _compor(monkeypatch: pytest.MonkeyPatch, lf: Any, adaptador: Any) -> tuple[int, str]:
    monkeypatch.setattr(assistente, "OBS", ObservadorLangfuse(lf))
    monkeypatch.setattr(assistente, "_adaptador", lambda: adaptador)
    sid = criar_sessao(usuario_id="t043-helena", papel="rt")
    async with cliente(sid) as cli:
        r = await cli.post("/api/assistente/compor", json={"pergunta": "o que vence"})
    return r.status_code, r.text


# ---------------------------------------------------------------- AC-1
async def test_ac1_a_geracao_dura_o_tempo_real_da_chamada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lf = LangfuseFalso()
    codigo, corpo = await _compor(monkeypatch, lf, AdaptadorLento())
    assert codigo == 200, corpo

    por = lf.por_nome()
    raiz, geracao, barreira = (
        por["compor-interface"],
        por["gerar-composicao"],
        por["validar-schema"],
    )
    assert (raiz.as_type, geracao.as_type, barreira.as_type) == (
        "agent",
        "generation",
        "guardrail",
    )
    assert geracao.pai is raiz
    assert barreira.pai is raiz
    assert geracao.duracao >= ATRASO_S
    assert barreira.duracao < ATRASO_S
    assert raiz.duracao >= geracao.duracao + barreira.duracao


# ---------------------------------------------------------------- AC-2
async def test_ac2_o_caminho_ao_vivo_nao_se_diz_artificial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lf = LangfuseFalso()
    await _compor(monkeypatch, lf, AdaptadorLento())
    assert "artificial" not in repr([(o.kw, o.updates) for o in lf.registro])


def test_ac2_contraponto_o_caminho_pos_fato_continua_marcado() -> None:
    """Sem ele, uma busca por "artificial" que nunca achasse nada passaria acima."""
    lf = LangfuseFalso()
    ObservadorLangfuse(lf).composicao(
        trace=Trace(origem="mock", modelo="mock", pergunta="x"),
        ator_id="a",
        papel="rt",
        catalogo=1,
    )
    assert lf.por_nome()["compor-interface"].kw["metadata"]["duracao_da_span_e_artificial"]


# ---------------------------------------------------------------- AC-3
async def test_ac3_detalhes_e_notas_ficam_onde_o_painel_procura(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lf = LangfuseFalso()
    await _compor(monkeypatch, lf, AdaptadorLento())
    por = lf.por_nome()

    geracao = por["gerar-composicao"].updates[-1]
    assert geracao["model"] == "mock"
    assert set(geracao["usage_details"]) == {"input", "output"}
    assert set(por["validar-schema"].updates[-1]["output"]) == {"aceitos", "rejeitados"}

    notas = {n["name"]: n for n in por["compor-interface"].notas}
    assert notas["schema_valido"]["data_type"] == "BOOLEAN"
    assert "latencia_ms" in notas
    # A-10: nota presa ao trace, nenhuma solta
    assert lf.scores_soltos == []


# ---------------------------------------------------------------- AC-4
async def test_ac4_langfuse_fora_do_ar_nao_derruba(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="estoque.observador")
    codigo, corpo = await _compor(monkeypatch, LangfuseFora(), AdaptadorLento())
    assert codigo == 200, corpo
    assert '"blocos"' in corpo
    assert "falha ao abrir observacao" in caplog.text


async def test_ac4_falha_no_meio_nao_derruba(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="estoque.observador")
    codigo, corpo = await _compor(monkeypatch, LangfuseQueQuebraNoMeio(), AdaptadorLento())
    assert codigo == 200, corpo
    assert "falha ao detalhar etapa" in caplog.text
    assert "falha ao concluir observacao" in caplog.text


# ---------------------------------------------------------------- AC-5
async def test_ac5_erro_do_modelo_atravessa_e_a_arvore_fecha_em_erro(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lf = LangfuseFalso()
    codigo, corpo = await _compor(monkeypatch, lf, AdaptadorQueFalha())
    assert codigo == 422, corpo
    raiz = lf.por_nome()["compor-interface"]
    assert raiz.fim > 0
    assert raiz.updates[-1]["level"] == "ERROR"
    assert "validar-schema" not in lf.por_nome()


# ---------------------------------------------------------------- AC-6
def test_ac6_host_le_base_url_quando_falta_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
    assert langfuse_obs._host() == "https://us.cloud.langfuse.com"


def test_ac6_sem_chave_o_observador_e_nulo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    assert langfuse_obs.criar() is None


# ---------------------------------------------------------------- AC-7
def test_ac7_o_falso_nao_diverge_do_sdk() -> None:
    from langfuse import Langfuse, propagate_attributes
    from langfuse._client import span as sdk

    abrir = set(inspect.signature(Langfuse.start_as_current_observation).parameters)
    assert {"as_type", "name", "input", "metadata"} <= abrir
    propagar = set(inspect.signature(propagate_attributes).parameters)
    assert {"trace_name", "user_id", "environment", "tags"} <= propagar
    usados = {
        "output",
        "level",
        "status_message",
        "metadata",
        "model",
        "usage_details",
        "cost_details",
    }
    for classe in (sdk.LangfuseAgent, sdk.LangfuseGeneration, sdk.LangfuseGuardrail):
        assert usados <= set(inspect.signature(classe.update).parameters), classe.__name__
        nota = set(inspect.signature(classe.score_trace).parameters)
        assert {"name", "value", "data_type"} <= nota, classe.__name__
