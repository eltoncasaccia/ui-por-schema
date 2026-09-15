"""T-027 AC-1, AC-3, AC-4, AC-5, AC-7 — a escrita, contra Postgres real.

**AC-1 é o critério central da tarefa**, e a armadilha que ele desarma está
escrita no arquivo dela: *"AC-1 com requisição direta ao endpoint é o que separa
esta tarefa de uma interface que apenas esconde botões."* Aqui nenhum teste passa
por interface. Cada um chama o pipeline direto, que é o que uma requisição
forjada faz — e é a única forma de provar `RN-A03`.

As seis personas que não são a Helena aparecem uma a uma. Um `for` sobre todas
provaria menos: com cinco recusadas e uma esquecida, o laço ainda fica verde.

Pulam sem banco: `make db-local && make db-teste`.
"""

import secrets
from dataclasses import replace
from datetime import date, timedelta
from typing import Any

import banco
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

import estoque.application.commands.indice  # noqa: F401  — registra os comandos do lote
from estoque.application.commands import pipeline
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator

URL = banco.URL_APP_ASYNC
URL_SONDA = banco.URL_APP

UNIDADE = "cd-matriz"
LOTE = "t027-lote"
LOTE_VAC = "t027-lote-vac"  # termolábil, para o item de temperatura de RN-R03
PRODUTO = "t027-prod"
PRODUTO_VAC = "t027-prod-vac"

JUSTIFICATIVA = "conferência completa, embalagem íntegra"


@pytest.fixture(scope="module")
def motor() -> AsyncEngine:
    try:
        sonda = sa.create_engine(URL_SONDA, connect_args={"connect_timeout": 2})
        with sonda.connect():
            pass
    except Exception:
        pytest.skip("sem banco: rode `make db-local && make db-teste`")
    return create_async_engine(URL, future=True, poolclass=NullPool)


@pytest.fixture(autouse=True)
async def _semear(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    """Dois lotes em quarentena antes de cada teste — um comum, um termolábil."""
    hoje = date.today()
    async with motor.begin() as c:
        await c.execute(
            sa.text(
                "INSERT INTO unidade VALUES ('cd-matriz','Matriz','seco',true) "
                "ON CONFLICT DO NOTHING"
            )
        )
        await c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'7893','Amoxicilina','F','amox','comum','A',true,1250) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PRODUTO},
        )
        await c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'7894','Vacina','B','influenza','termolabil','A',true,4800) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PRODUTO_VAC},
        )
        for lote_id, prod in ((LOTE, PRODUTO), (LOTE_VAC, PRODUTO_VAC)):
            await c.execute(
                sa.text(
                    "INSERT INTO lote VALUES "
                    "(:l,:p,'L-027','cd-matriz',:f,:v,'quarentena',null) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "l": lote_id,
                    "p": prod,
                    "f": hoje - timedelta(days=100),
                    "v": hoje + timedelta(days=400),
                },
            )
            # Estado inicial conhecido, mesmo depois de um teste ter mudado.
            await c.execute(
                sa.text("UPDATE lote SET status='quarentena', validade=:v WHERE id=:l"),
                {"l": lote_id, "v": hoje + timedelta(days=400)},
            )
        for a in personas.values():
            await c.execute(
                sa.text(
                    "INSERT INTO usuario VALUES (:i,:n,:e,'x',:pp,true) ON CONFLICT DO NOTHING"
                ),
                {"i": a.id, "n": a.nome, "e": f"{a.id}@bertoni.test", "pp": a.papel},
            )


# ------------------------------------------------------------------ auxiliares
async def _status(motor: AsyncEngine, lote_id: str = LOTE) -> str:
    async with motor.connect() as c:
        s = (
            await c.execute(sa.select(m.lote.c.status).where(m.lote.c.id == lote_id))
        ).scalar_one()
    return str(s)


async def _etag(motor: AsyncEngine, ator: Ator, lote_id: str = LOTE) -> str:
    """O etag como o comando o calcula, pelo mesmo caminho."""
    from datetime import UTC, datetime

    from estoque.application.commands.lote import _etag_do_lote
    from estoque.application.commands.tipos import ContextoComando

    class _E:
        lote_id = ""

    alvo = _E()
    alvo.lote_id = lote_id
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        etag = await _etag_do_lote(alvo, ctx)
    # `None` quando o lote está fora do escopo DESTE ator — o caso do Odair, que
    # só alcança Uberlândia. O valor devolvido aqui não importa nessa situação:
    # a autorização é conferida antes do `If-Match`, e é ela que recusa.
    return etag or "fora-de-escopo"


async def _liberar(motor: AsyncEngine, ator: Ator, *, lote_id: str = LOTE, **extra: Any) -> Any:
    corpo: dict[str, Any] = {
        "lote_id": lote_id,
        "decisao": "liberar",
        "justificativa": JUSTIFICATIVA,
        "integridade_conferida": True,
        "validade_conferida": True,
        "nota_fiscal_conferida": True,
    }
    corpo.update(extra)
    return await pipeline.executar(
        "lote_liberar_quarentena",
        corpo,
        ator=ator,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await _etag(motor, ator, lote_id),
    )


async def _auditoria(motor: AsyncEngine, acao: str) -> list[dict[str, Any]]:
    async with motor.connect() as c:
        linhas = (
            (
                await c.execute(
                    sa.select(m.auditoria)
                    .where(m.auditoria.c.acao == acao)
                    .order_by(m.auditoria.c.id)
                )
            )
            .mappings()
            .all()
        )
    return [dict(x) for x in linhas]


# ------------------------------------- AC-1 · só o RT, com requisição direta
async def test_ac1_helena_libera(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    r = await _liberar(motor, personas["helena"])
    assert r.dados["status"] == "liberado"
    assert await _status(motor) == "liberado"


@pytest.mark.parametrize("quem", ["marco", "ivo", "odair", "cleide", "rafael", "sandra"])
async def test_ac1_os_outros_seis_sao_recusados_no_servidor(
    motor: AsyncEngine, personas: dict[str, Ator], quem: str
) -> None:
    """RN-R02: "nenhum outro papel, em nenhuma circunstância".

    Marco é o Diretor — tem mais permissões que Helena e nenhuma delas é esta.
    Papel não é nível, é conjunto. A interface já teria escondido o botão, e
    esconder não é controlar (`RN-A03`): aqui a chamada é direta ao pipeline.
    """
    with pytest.raises(ErroDominio) as e:
        await _liberar(motor, personas[quem])
    assert e.value.codigo == "nao_autorizado"
    assert await _status(motor) == "quarentena", f"{quem} conseguiu mudar o estado"


async def test_ac1_rt_desativada_e_recusada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A06: desligamento tem efeito imediato, mesmo com a permissão na mão."""
    with pytest.raises(ErroDominio) as e:
        await _liberar(motor, replace(personas["helena"], ativo=False))
    assert e.value.codigo == "nao_autorizado"
    assert await _status(motor) == "quarentena"


async def test_ac1_a_tabela_41_recusa_papel_errado_mesmo_com_permissao(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """A SEGUNDA camada, e a razão de ela existir.

    Aqui o Diretor recebe `lote.liberar` de propósito — o erro de uma linha num
    dicionário de permissões. A primeira camada passa a deixá-lo entrar; a
    tabela §4.1 continua exigindo `papel == 'rt'` e recusa assim mesmo.

    Sem este teste, `RN-R02` dependeria da matriz de permissões continuar
    correta para sempre, o que não é uma garantia — é uma esperança.
    """
    diretor_com_permissao = replace(
        personas["marco"], permissoes=personas["marco"].permissoes | {"lote.liberar"}
    )
    with pytest.raises(ErroDominio) as e:
        await _liberar(motor, diretor_com_permissao)
    assert e.value.codigo == "conflito"
    assert await _status(motor) == "quarentena"


# ------------------------------------------------- AC-3 · checklist (RN-R03)
async def test_ac3_liberacao_sem_checklist_e_recusada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    with pytest.raises(ErroDominio) as e:
        await _liberar(motor, personas["helena"], integridade_conferida=False)
    assert e.value.codigo == "invalido"
    assert "integridade" in e.value.mensagem_publica
    assert await _status(motor) == "quarentena"


@pytest.mark.parametrize(
    "faltando", ["integridade_conferida", "validade_conferida", "nota_fiscal_conferida"]
)
async def test_ac3_cada_item_obrigatorio_sozinho_ja_recusa(
    motor: AsyncEngine, personas: dict[str, Ator], faltando: str
) -> None:
    """Um por vez. Testar só "nenhum marcado" deixaria passar a implementação
    que exige *pelo menos um* item em vez de todos."""
    with pytest.raises(ErroDominio) as e:
        await _liberar(motor, personas["helena"], **{faltando: False})  # type: ignore[arg-type]
    assert e.value.codigo == "invalido"
    assert await _status(motor) == "quarentena"


async def test_ac3_termolabil_exige_temperatura(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-R03: a temperatura de chegada entra no checklist só do termolábil."""
    with pytest.raises(ErroDominio) as e:
        await _liberar(motor, personas["helena"], lote_id=LOTE_VAC)
    assert e.value.codigo == "invalido"
    assert "temperatura" in e.value.mensagem_publica
    assert await _status(motor, LOTE_VAC) == "quarentena"


async def test_ac3_termolabil_com_temperatura_passa(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    r = await _liberar(motor, personas["helena"], lote_id=LOTE_VAC, temperatura_conferida=True)
    assert r.dados["status"] == "liberado"


async def test_ac3_produto_comum_nao_exige_temperatura(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O par negativo do teste acima: exigir de todos treinaria o RT a marcar
    tudo sem ler, e aí a conferência obrigatória não conferiria nada."""
    r = await _liberar(motor, personas["helena"])  # sem temperatura_conferida
    assert r.dados["status"] == "liberado"


async def test_ac3_justificativa_curta_e_recusada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    with pytest.raises(ErroDominio) as e:
        await _liberar(motor, personas["helena"], justificativa="ok")
    assert e.value.codigo == "invalido"
    assert await _status(motor) == "quarentena"


# ------------------------------------------------- AC-4 · reprovar → bloqueado
async def test_ac4_reprovacao_leva_a_bloqueado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """§4.1. Nunca a liberado, e não existe estado intermediário: um lote
    "liberado com pendência" seria mercadoria vendável que ninguém conferiu."""
    r = await pipeline.executar(
        "lote_liberar_quarentena",
        {
            "lote_id": LOTE,
            "decisao": "reprovar",
            "justificativa": "embalagem violada no transporte",
        },
        ator=personas["helena"],
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await _etag(motor, personas["helena"]),
    )
    assert r.dados["status"] == "bloqueado"
    assert await _status(motor) == "bloqueado"


async def test_ac4_reprovar_nao_exige_checklist(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Conferir é o que autoriza LIBERAR. Exigir a conferência para recusar
    criaria o incentivo errado: o caminho seguro ficaria mais caro que o outro."""
    assert await _status(motor) == "quarentena"
    await pipeline.executar(
        "lote_liberar_quarentena",
        {"lote_id": LOTE, "decisao": "reprovar", "justificativa": "suspeita de desvio"},
        ator=personas["helena"],
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await _etag(motor, personas["helena"]),
    )
    assert await _status(motor) == "bloqueado"


# ---------------------------------------- AC-5 · transição fora da §4.1 recusada
async def test_ac5_liberar_lote_ja_liberado_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    await _liberar(motor, personas["helena"])
    with pytest.raises(ErroDominio) as e:
        await _liberar(motor, personas["helena"])
    assert e.value.codigo == "conflito"
    assert await _status(motor) == "liberado"


async def test_ac5_desbloquear_lote_em_quarentena_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """`quarentena + desbloqueio` não está na tabela. A saída da quarentena é
    pelo formulário de liberação, com checklist — e ter dois caminhos para o
    mesmo estado, um deles sem conferência, é o buraco que isto fecha."""
    with pytest.raises(ErroDominio) as e:
        await _status_acao(motor, personas["helena"], "desbloquear")
    assert e.value.codigo == "conflito"
    assert await _status(motor) == "quarentena"


async def _status_acao(motor: AsyncEngine, ator: Ator, acao: str, **extra: Any) -> Any:
    corpo: dict[str, Any] = {
        "lote_id": LOTE,
        "acao": acao,
        "justificativa": "recall do fabricante, lote suspeito",
    }
    corpo.update(extra)
    return await pipeline.executar(
        "lote_status",
        corpo,
        ator=ator,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await _etag(motor, ator),
    )


async def test_ac5_bloquear_lote_em_quarentena_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    with pytest.raises(ErroDominio) as e:
        await _status_acao(motor, personas["helena"], "bloquear")
    assert e.value.codigo == "conflito"


async def test_ac5_o_ciclo_liberado_bloqueado_liberado_funciona(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O par positivo dos três testes acima. Sem ele, um comando que recusasse
    TUDO passaria em todos os negativos."""
    h = personas["helena"]
    await _liberar(motor, h)
    assert await _status(motor) == "liberado"
    await _status_acao(motor, h, "bloquear")
    assert await _status(motor) == "bloqueado"
    await _status_acao(motor, h, "desbloquear")
    assert await _status(motor) == "liberado"


@pytest.mark.parametrize("quem", ["marco", "ivo", "cleide", "sandra"])
async def test_ac5_status_e_recusado_para_quem_nao_e_rt(
    motor: AsyncEngine, personas: dict[str, Ator], quem: str
) -> None:
    with pytest.raises(ErroDominio) as e:
        await _status_acao(motor, personas[quem], "bloquear")
    assert e.value.codigo == "nao_autorizado"


# ------------------------------------------------------------ AC-6 · RN-L05
async def test_ac6_liberar_vencimento_fora_da_janela_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O lote do fixture vence em 400 dias: não há bloqueio por validade."""
    h = personas["helena"]
    await _liberar(motor, h)
    with pytest.raises(ErroDominio) as e:
        await _status_acao(motor, h, "liberar_vencimento")
    assert e.value.codigo == "invalido"


async def test_ac6_liberar_vencimento_dentro_da_janela_passa_e_nao_muda_status(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-L05 com ADR-0022: o bloqueio por validade é DERIVADO da data, então
    não há status a mudar. A autorização do RT fica na trilha — ver achado A-14.
    """
    h = personas["helena"]
    await _liberar(motor, h)
    async with motor.begin() as c:
        await c.execute(
            sa.text("UPDATE lote SET validade = :v WHERE id = :l"),
            {"v": date.today() + timedelta(days=20), "l": LOTE},
        )
    r = await _status_acao(motor, h, "liberar_vencimento")
    assert r.dados["acao"] == "liberar_vencimento"
    assert await _status(motor) == "liberado"

    trilha = await _auditoria(motor, "lote_status")
    assert trilha[-1]["valor_novo"]["venda_autorizada_no_vencimento"] is True
    assert trilha[-1]["valor_novo"]["justificativa"]


async def test_ac6_lote_vencido_nao_pode_ser_liberado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-L06 é mais forte que RN-L05: vencido não sai, exceto por descarte."""
    h = personas["helena"]
    await _liberar(motor, h)
    async with motor.begin() as c:
        await c.execute(
            sa.text("UPDATE lote SET validade = :v WHERE id = :l"),
            {"v": date.today() - timedelta(days=1), "l": LOTE},
        )
    with pytest.raises(ErroDominio) as e:
        await _status_acao(motor, h, "liberar_vencimento")
    assert e.value.codigo == "conflito"
    assert "RN-L06" in e.value.mensagem_publica


# ------------------------------------------------------- AC-7 · RN-F02, e a trilha
async def test_ac7_lote_bloqueado_so_sai_por_decisao_explicita_do_rt(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-F02: excursão de temperatura mantém o lote bloqueado até decisão do RT.

    O que se prova aqui é a metade que existe: **não há caminho automático** para
    fora de `bloqueado`. Nenhuma leitura, nenhum recálculo e nenhum outro papel
    o move — só `desbloquear`, do RT, com justificativa registrada.

    A detecção da excursão em si é T-023 (`temperatura_excursoes`), e o
    repositório de temperatura ainda não existe. O que T-027 garante é o destino:
    uma vez bloqueado, sai por decisão humana ou não sai.
    """
    h = personas["helena"]
    await pipeline.executar(
        "lote_liberar_quarentena",
        {"lote_id": LOTE, "decisao": "reprovar", "justificativa": "excursão de temperatura"},
        ator=h,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await _etag(motor, h),
    )
    assert await _status(motor) == "bloqueado"

    # Nenhum outro papel tira o lote de lá.
    for quem in ("marco", "ivo", "cleide"):
        with pytest.raises(ErroDominio):
            await _status_acao(motor, personas[quem], "desbloquear")
        assert await _status(motor) == "bloqueado", quem

    # E a leitura repetida não o move sozinha.
    assert await _status(motor) == "bloqueado"

    await _status_acao(motor, h, "desbloquear")
    assert await _status(motor) == "liberado"


async def test_a_trilha_guarda_o_checklist_e_a_justificativa(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-D01. A trilha precisa reconstruir o que foi conferido — é para isso
    que ela existe, e "liberou" sozinho não reconstrói nada."""
    antes = len(await _auditoria(motor, "lote_liberar_quarentena"))
    await _liberar(motor, personas["helena"])
    trilha = await _auditoria(motor, "lote_liberar_quarentena")
    assert len(trilha) == antes + 1
    ultima = trilha[-1]
    assert ultima["ator_id"] == personas["helena"].id
    assert ultima["valor_anterior"] == {"status": "quarentena"}
    assert ultima["valor_novo"]["status"] == "liberado"
    assert ultima["valor_novo"]["justificativa"] == JUSTIFICATIVA
    assert ultima["valor_novo"]["conferencia"]["integridade"] is True


async def test_a_recusa_de_quem_nao_pode_tambem_fica_na_trilha(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Auditoria que só registra sucesso descreve um sistema onde ninguém nunca
    tentou o que não podia — que é justamente o que se quer investigar."""
    antes = len(await _auditoria(motor, "lote_liberar_quarentena.recusado"))
    with pytest.raises(ErroDominio):
        await _liberar(motor, personas["ivo"])
    trilha = await _auditoria(motor, "lote_liberar_quarentena.recusado")
    assert len(trilha) == antes + 1
    assert trilha[-1]["ator_id"] == personas["ivo"].id
    assert trilha[-1]["valor_novo"]["codigo"] == "nao_autorizado"


# ------------------------------------------------------------------- escopo
async def test_lote_fora_do_escopo_nao_e_encontrado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A01 na ESCRITA. O comando vai pela mesma porta que a leitura: um RT
    com escopo restrito não libera lote de unidade que não alcança."""
    rt_de_uberlandia = replace(personas["helena"], unidades=frozenset({"filial-uberlandia"}))
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "lote_liberar_quarentena",
            {
                "lote_id": LOTE,
                "decisao": "liberar",
                "justificativa": JUSTIFICATIVA,
                "integridade_conferida": True,
                "validade_conferida": True,
                "nota_fiscal_conferida": True,
            },
            ator=rt_de_uberlandia,
            motor=motor,
            origem="tela",
            idempotency_key=secrets.token_hex(8),
            if_match="qualquer",
        )
    assert e.value.codigo == "nao_encontrado"
    assert e.value.mensagem_publica == "Registro nao encontrado."
    assert await _status(motor) == "quarentena"


# --------------------------------------------------- bijeção declarado ↔ executável
def test_os_dois_comandos_estao_registrados() -> None:
    registrados = pipeline.registrados()
    assert "lote_liberar_quarentena" in registrados
    assert "lote_status" in registrados
    assert registrados["lote_liberar_quarentena"].requires == ("lote.liberar",)
    assert registrados["lote_status"].requires == ("lote.status",)
