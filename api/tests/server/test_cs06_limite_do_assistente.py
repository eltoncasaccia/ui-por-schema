"""CS-06 · T-011 AC-6 — rate limit POR ATOR no endpoint do assistente.

**Isto nao existia.** A T-040 entregou rate limit no *login* e o rotulou CS-06
(`auth/limite.py`, primeira linha do docstring), mas o CS-06 do PRD e o quadro
de CONTRATOS §8 pedem outra coisa: *"rate limit por ator no endpoint do
assistente"*. Sao duas protecoes com dois alvos — forca bruta de senha e custo
de token por ator. Achado A-34.

**Nenhum teste daqui chama modelo de verdade.** O adaptador entra por
`monkeypatch`; o caminho bloqueado nem chega la', que e' precisamente a
propriedade que se quer provar.
"""

from collections.abc import AsyncGenerator, Iterator, Mapping, Sequence
from typing import Any

import pytest
import sqlalchemy as sa
from borda import cliente, criar_sessao, descartar_pool, motor_dono

from estoque.assistant.adapter import AdaptadorMock, Resposta
from estoque.assistant.trace import Modo
from estoque.server.rotas import assistente


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


class AdaptadorEspiao:
    """Conta as chamadas. Se o teto deixar passar o que devia barrar, o contador
    denuncia — e' o que separa "respondeu 429" de "nao gastou token"."""

    def __init__(self) -> None:
        self.chamadas = 0
        self._real = AdaptadorMock()

    async def compor(
        self, pergunta: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo = "restrito"
    ) -> Resposta:
        self.chamadas += 1
        return await self._real.compor(pergunta, catalogo, modo=modo)


@pytest.fixture
def espiao(monkeypatch: pytest.MonkeyPatch) -> AdaptadorEspiao:
    espia = AdaptadorEspiao()
    monkeypatch.setattr(assistente, "_adaptador", lambda: espia)
    return espia


@pytest.fixture(autouse=True)
def _limite_limpo() -> Iterator[None]:
    """O `Limitador` e' modulo-global e vive entre testes.

    Mexer no `_por_chave` e' invadir o interior de proposito: nao ha API publica
    de reset, e um teste que herda a janela do anterior falha de forma que
    parece bug do servidor.
    """
    assistente.LIMITE._por_chave.clear()
    yield
    assistente.LIMITE._por_chave.clear()


async def _perguntar(sid: str) -> tuple[int, str]:
    async with cliente(sid) as cli:
        r = await cli.post("/api/assistente/compor", json={"pergunta": "o que vence"})
    return r.status_code, r.text


def _bloqueios(ator: str) -> int:
    with motor_dono().connect() as c:
        return int(
            c.execute(
                sa.text(
                    "SELECT count(*) FROM auditoria "
                    "WHERE acao='assistente_bloqueado' AND ator_id=:a"
                ),
                {"a": ator},
            ).scalar_one()
        )


# --- o teto existe e dispara `limite` --------------------------------------


async def test_ac6_estourar_o_teto_por_ator_devolve_limite(espiao: AdaptadorEspiao) -> None:
    ator = "cs06-ivo"
    sid = criar_sessao(usuario_id=ator, papel="gerente", unidades=("cd-matriz",))
    # Enche a janela sem falar com modelo nenhum: o que importa e' o estado do
    # contador, e gastar 30 chamadas de verdade tornaria o teste lento a toa.
    for _ in range(assistente.COMPOSICOES_POR_ATOR):
        assistente.LIMITE.registrar_falha(conta=ator, ip="testclient")

    codigo, corpo = await _perguntar(sid)
    assert codigo == 429, corpo
    assert "limite" in corpo


async def test_ac6_bloqueado_nao_chega_ao_modelo(espiao: AdaptadorEspiao) -> None:
    """A razao de o teto existir. Um 429 depois de chamar o modelo teria gasto
    o token que o limite existe para poupar (ADR-0011)."""
    ator = "cs06-ivo2"
    sid = criar_sessao(usuario_id=ator, papel="gerente", unidades=("cd-matriz",))
    for _ in range(assistente.COMPOSICOES_POR_ATOR):
        assistente.LIMITE.registrar_falha(conta=ator, ip="testclient")

    codigo, _ = await _perguntar(sid)
    assert codigo == 429
    assert espiao.chamadas == 0, "o modelo foi chamado numa requisicao bloqueada"


async def test_ac6_a_recusa_por_limite_e_auditada(espiao: AdaptadorEspiao) -> None:
    """O AC pede as duas coisas: "dispara `limite` **e e' registrado em
    auditoria**". Tentativa bloqueada e' sinal, nao ruido."""
    ator = "cs06-ivo3"
    sid = criar_sessao(usuario_id=ator, papel="gerente", unidades=("cd-matriz",))
    for _ in range(assistente.COMPOSICOES_POR_ATOR):
        assistente.LIMITE.registrar_falha(conta=ator, ip="testclient")

    antes = _bloqueios(ator)
    assert (await _perguntar(sid))[0] == 429
    assert _bloqueios(ator) == antes + 1


async def test_ac6_a_auditoria_da_recusa_sobrevive_ao_raise(espiao: AdaptadorEspiao) -> None:
    """O modo de falha silencioso deste desenho: registrar a recusa DENTRO da
    transacao que o `raise` reverte grava nada e ninguem percebe, porque a
    resposta 429 continua correta."""
    ator = "cs06-ivo4"
    sid = criar_sessao(usuario_id=ator, papel="gerente", unidades=("cd-matriz",))
    for _ in range(assistente.COMPOSICOES_POR_ATOR):
        assistente.LIMITE.registrar_falha(conta=ator, ip="testclient")
    assert (await _perguntar(sid))[0] == 429

    with motor_dono().connect() as c:
        linha = (
            c.execute(
                sa.text(
                    "SELECT ator_id, acao, origem FROM auditoria "
                    "WHERE ator_id=:a ORDER BY id DESC LIMIT 1"
                ),
                {"a": ator},
            )
            .mappings()
            .one()
        )
    assert linha["acao"] == "assistente_bloqueado"
    assert linha["ator_id"] == ator


# --- o contraponto: abaixo do teto passa ------------------------------------


async def test_ac6_abaixo_do_teto_a_pergunta_passa(espiao: AdaptadorEspiao) -> None:
    """Sem este, um teto de zero passaria em todos os testes acima."""
    sid = criar_sessao(usuario_id="cs06-helena", papel="rt", unidades=("cd-matriz",))
    codigo, corpo = await _perguntar(sid)
    assert codigo == 200, corpo
    assert espiao.chamadas == 1


async def test_ac6_a_chamada_bem_sucedida_tambem_gasta_cota(espiao: AdaptadorEspiao) -> None:
    """A diferenca para o rate limit do login, e a razao de o CS-06 ser outra
    protecao: la' so' a FALHA conta, porque errar a senha e' o ataque. Aqui o
    custo e' do token, entao a composicao que deu certo gasta igual."""
    ator = "cs06-helena2"
    sid = criar_sessao(usuario_id=ator, papel="rt", unidades=("cd-matriz",))
    assert (await _perguntar(sid))[0] == 200
    assert len(assistente.LIMITE._por_chave[f"c:{ator}"]) == 1


# --- o teto e' POR ATOR -----------------------------------------------------


async def test_ac6_bloquear_um_ator_nao_bloqueia_outro(espiao: AdaptadorEspiao) -> None:
    """Teto por ator que derruba o vizinho e' negacao de servico contra quem nao
    fez nada — o mesmo cuidado que a T-040 teve com conta e IP no login."""
    travado = "cs06-travado"
    livre = "cs06-livre"
    sid_travado = criar_sessao(usuario_id=travado, papel="gerente", unidades=("cd-matriz",))
    sid_livre = criar_sessao(usuario_id=livre, papel="gerente", unidades=("cd-matriz",))
    for _ in range(assistente.COMPOSICOES_POR_ATOR):
        assistente.LIMITE.registrar_falha(conta=travado, ip="outro-ip")

    assert (await _perguntar(sid_travado))[0] == 429
    assert (await _perguntar(sid_livre))[0] == 200


async def test_ac6_o_teto_por_ip_e_mais_alto_que_o_por_ator() -> None:
    """Um CD inteiro sai por um NAT so'. Tratar IP como pessoa derrubaria o
    turno por causa de um cliente com defeito."""
    assert assistente.COMPOSICOES_POR_IP > assistente.COMPOSICOES_POR_ATOR


async def test_ac6_sem_sessao_o_limite_nem_e_consultado(espiao: AdaptadorEspiao) -> None:
    """Ordem importa: identidade primeiro. Se o teto fosse conferido antes do
    ator, um anonimo gastaria a cota de alguem — ou de todos, pelo IP."""
    async with cliente(None) as cli:
        r = await cli.post("/api/assistente/compor", json={"pergunta": "x"})
    assert r.status_code == 401
    assert espiao.chamadas == 0
    assert not assistente.LIMITE._por_chave
