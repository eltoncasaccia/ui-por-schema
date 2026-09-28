"""O que acontece quando o MODELO falha — o caminho que nao tinha teste nenhum.

`test_adapter.py` tem 13 testes, todos sobre formato de schema, extracao de
JSON e identificacao do mock. Nenhum deles exercia a rota com o modelo fora do
ar, e e' justamente o caso que o usuario encontra primeiro: provedor lento,
chave vencida, modelo frio que estoura o timeout de 30 s.

Isto e' deterministico e NAO chama modelo nenhum. Se o modelo responde **bem**
e com que frequencia, e' outra pergunta — nao-deterministica, e medida pela
suite `estoque.eval` com limiar (ADR-0013, R-001). Teste pergunta "passou?";
medicao pergunta "com que frequencia?". Confundir os dois foi o erro da v1.

A regra da casa, aplicada aqui: para todo mecanismo de protecao, o teste que
prova que ele falha quando deveria falhar.
"""

from collections.abc import AsyncGenerator, Iterator, Mapping, Sequence
from typing import Any

import pytest
from borda import cliente, criar_sessao, descartar_pool

from estoque.assistant.adapter import AdaptadorMock, Resposta
from estoque.assistant.trace import Modo
from estoque.server.rotas import assistente


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


@pytest.fixture(autouse=True)
def _limite_limpo() -> Iterator[None]:
    """O `Limitador` e' modulo-global e vive entre testes (mesmo motivo do CS-06)."""
    assistente.LIMITE._por_chave.clear()
    yield
    assistente.LIMITE._por_chave.clear()


class AdaptadorForaDoAr:
    """O provedor nao respondeu: timeout, DNS, chave recusada.

    Reproduz o que `AdaptadorOpenRouter.compor` faz de verdade em
    `except httpx.HTTPError` — devolve `Resposta` VAZIA com `trace.erro`
    preenchido, em vez de levantar. E' esse contrato que a rota le'.
    """

    def __init__(self, erro: str = "ReadTimeout") -> None:
        self.chamadas = 0
        self._erro = erro

    async def compor(
        self, pergunta: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo = "restrito"
    ) -> Resposta:
        self.chamadas += 1
        r = await AdaptadorMock().compor(pergunta, catalogo, modo=modo)
        r.trace.erro = self._erro
        return Resposta("", r.trace)


class AdaptadorQueDevolveLixo:
    """Respondeu, mas nao em JSON. Caso diferente de "nao respondeu"."""

    async def compor(
        self, pergunta: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo = "restrito"
    ) -> Resposta:
        r = await AdaptadorMock().compor(pergunta, catalogo, modo=modo)
        return Resposta("Claro! Aqui esta o que voce pediu, em prosa.", r.trace)


def _sessao(ator: str = "falha-ivo") -> str:
    return criar_sessao(usuario_id=ator, papel="gerente", unidades=("cd-matriz",))


async def _perguntar(sid: str) -> tuple[int, str]:
    async with cliente(sid) as cli:
        r = await cli.post("/api/assistente/compor", json={"pergunta": "o que vence"})
    return r.status_code, r.text


# --- modelo fora do ar ------------------------------------------------------


async def test_modelo_fora_do_ar_avisa_com_mensagem_propria(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mensagem tem de falar do ASSISTENTE, nunca da entrada.

    `invalido` e' o mesmo codigo que serve para "entrada nao casa com o
    modelo", e a mensagem generica de la' ("Entrada invalida.") culparia o
    usuario por uma falha de infraestrutura — ele reescreveria a pergunta a
    noite inteira sem chegar a lugar nenhum.
    """
    monkeypatch.setattr(assistente, "_adaptador", lambda: AdaptadorForaDoAr())
    codigo, corpo = await _perguntar(_sessao())

    assert codigo == 422, corpo
    assert "assistente nao respondeu" in corpo.lower()
    assert "entrada invalida" not in corpo.lower()


async def test_falha_do_modelo_nao_vaza_o_erro_interno(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-0014: o detalhe fica no trace e no log, nunca na resposta.

    `ReadTimeout` conta ao cliente qual biblioteca o servidor usa e onde ele
    quebrou. E' pouco, e e' de graca para quem esta' sondando.
    """
    monkeypatch.setattr(assistente, "_adaptador", lambda: AdaptadorForaDoAr(erro="ReadTimeout"))
    _, corpo = await _perguntar(_sessao())

    assert "readtimeout" not in corpo.lower()
    assert "httpx" not in corpo.lower()
    assert "traceback" not in corpo.lower()


async def test_falha_do_modelo_nao_devolve_bloco_nenhum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tese, no caminho de erro: sem composicao valida, nada e' renderizado.

    Um bloco que escapasse aqui teria vindo de lugar nenhum — nao passou pelo
    catalogo do ator nem por `validar_schema` (ADR-0002).
    """
    monkeypatch.setattr(assistente, "_adaptador", lambda: AdaptadorForaDoAr())
    _, corpo = await _perguntar(_sessao())

    assert '"blocos"' not in corpo
    assert '"ok":true' not in corpo.replace(" ", "")


async def test_o_modelo_nao_e_chamado_de_novo_apos_falhar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**Nao existe retry, e isto trava o comportamento atual.**

    A cadeia `restrito -> ferramenta -> livre` do adaptador e' fallback de
    ENVELOPE, e so' dispara em HTTP 400 ("nao suporto esse formato"). Timeout e
    falha de rede desistem na primeira.

    Se alguem acrescentar retry, este teste fica vermelho — e tem de ficar: uma
    nova tentativa gasta token de novo, e o teto por ator (`CS-06`, ADR-0011)
    conta CHAMADA, nao pergunta. Retry silencioso multiplicaria a conta do
    cliente sem ninguem decidir isso.
    """
    fora = AdaptadorForaDoAr()
    monkeypatch.setattr(assistente, "_adaptador", lambda: fora)
    await _perguntar(_sessao())

    assert fora.chamadas == 1


async def test_a_tentativa_que_falhou_consome_cota(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falha do provedor gasta cota do ator, e isso e' deliberado.

    O teto existe para conter custo e laco automatico. Um laco que bate num
    provedor fora do ar continua custando — conexao, tempo de worker — e
    perdoar a falha daria exatamente a brecha que o teto fecha.
    """
    monkeypatch.setattr(assistente, "_adaptador", lambda: AdaptadorForaDoAr())
    ator = "falha-cota"
    sid = _sessao(ator)

    await _perguntar(sid)

    for _ in range(assistente.COMPOSICOES_POR_ATOR - 1):
        assistente.LIMITE.registrar_falha(conta=ator, ip="testclient")
    codigo, corpo = await _perguntar(sid)

    assert codigo == 429, f"a tentativa que falhou nao contou na cota: {corpo}"


# --- respondeu, mas nao em JSON ---------------------------------------------


async def test_resposta_em_prosa_nao_e_erro_de_infraestrutura(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dois casos distintos, e a tela precisa distingui-los.

    "Nao respondeu" pede tentar de novo. "Respondeu em prosa" e' o modelo
    falando quando devia compor: tentar de novo raramente ajuda, e o usuario
    precisa reformular. Trata-los igual manda a pessoa insistir no que nao vai
    funcionar.
    """
    monkeypatch.setattr(assistente, "_adaptador", lambda: AdaptadorQueDevolveLixo())
    codigo, corpo = await _perguntar(_sessao())

    assert codigo == 200, corpo
    assert "assistente nao respondeu" not in corpo.lower()
    # Composicao vazia: a tela mostra "nao consigo responder isso por aqui".
    assert '"blocos":[]' in corpo.replace(" ", "")


async def test_prosa_do_modelo_nao_chega_ao_cliente(monkeypatch: pytest.MonkeyPatch) -> None:
    """O texto cru do modelo nao e' eco'ado na resposta.

    Se fosse, uma injecao que fizesse o modelo responder em prosa teria um
    canal direto para a tela do usuario — texto escolhido pelo atacante,
    exibido pelo sistema (o vetor que o CS-01 e o A-42 tratam do outro lado).
    """
    monkeypatch.setattr(assistente, "_adaptador", lambda: AdaptadorQueDevolveLixo())
    _, corpo = await _perguntar(_sessao())

    assert "em prosa" not in corpo.lower()
