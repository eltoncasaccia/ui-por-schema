"""T-026 — o registro de recebimento, contra Postgres real.

**Nenhum teste passa por interface.** Cada um chama o pipeline direto, que é o
que uma requisição forjada faz — e é a única forma de provar `RN-A03` e o AC-1,
que fala de "requisição forjada" com todas as letras.

As personas que **não** podem registrar aparecem uma a uma (AC-7). Um `for` sobre
todas provaria menos: com duas recusadas e uma esquecida, o laço ainda fica
verde.

Pulam sem banco: `make db-local && make db-teste`.
"""

import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Any

import banco
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

import estoque.application.commands.indice  # noqa: F401  — registra os comandos
from estoque.application.commands import pipeline
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator

URL = banco.URL_APP_ASYNC
URL_SONDA = banco.URL_APP
URL_DONO = banco.URL_DONO

# Unidades com propriedades CONHECIDAS: são elas que fazem RN-P02 e RN-P03
# terem lados. `cd-matriz` é seca **com** cofre; `cd-refrigerado` é refrigerada
# **sem** cofre. Assim cada regra tem um destino que aceita e um que recusa.
SECA_COM_COFRE = "cd-matriz"
FRIA_SEM_COFRE = "cd-refrigerado"

COMUM = "t026-prod-comum"
TERMOLABIL = "t026-prod-vac"
CONTROLADO = "t026-prod-ctrl"


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
def _semear(personas: dict[str, Ator]) -> None:
    """Produtos das três classes e unidades com propriedades conhecidas.

    Roda como DONO: `estoque_app` não insere usuário (achado A-27), e o teste
    não pode emprestar privilégio à aplicação que ele está testando.
    """
    try:
        dono = sa.create_engine(URL_DONO, connect_args={"connect_timeout": 2})
        with dono.connect():
            pass
    except Exception:
        pytest.skip("sem banco")

    with dono.begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO unidade VALUES (:i,'Matriz','seco',true) "
                "ON CONFLICT (id) DO UPDATE SET tipo='seco', sala_cofre=true"
            ),
            {"i": SECA_COM_COFRE},
        )
        c.execute(
            sa.text(
                "INSERT INTO unidade VALUES (:i,'Refrigerado','refrigerado',false) "
                "ON CONFLICT (id) DO UPDATE SET tipo='refrigerado', sala_cofre=false"
            ),
            {"i": FRIA_SEM_COFRE},
        )
        for pid, ean, classe in (
            (COMUM, "7890000026001", "comum"),
            (TERMOLABIL, "7890000026002", "termolabil"),
            (CONTROLADO, "7890000026003", "controlado"),
        ):
            c.execute(
                sa.text(
                    "INSERT INTO produto VALUES "
                    "(:p,:e,'Produto 026','F','x',:cl,'A',true,1000) "
                    "ON CONFLICT (id) DO UPDATE SET classe = EXCLUDED.classe"
                ),
                {"p": pid, "e": ean, "cl": classe},
            )
        for a in personas.values():
            c.execute(
                sa.text(
                    "INSERT INTO usuario VALUES (:i,:n,:e,'x',:pp,true) ON CONFLICT DO NOTHING"
                ),
                {"i": a.id, "n": a.nome, "e": f"{a.id}@bertoni.test", "pp": a.papel},
            )


# ------------------------------------------------------------------ auxiliares
def _item(produto_id: str, **over: Any) -> dict[str, Any]:
    hoje = date.today()
    base: dict[str, Any] = {
        "produto_id": produto_id,
        "numero": f"L{secrets.token_hex(4)}",
        "fabricacao": (hoje - timedelta(days=30)).isoformat(),
        # Bem acima dos 6 meses: validade curta é caso do AC-2, não ruído aqui.
        "validade": (hoje + timedelta(days=400)).isoformat(),
        "quantidade": 10,
    }
    base.update(over)
    return base


async def _registrar(motor: AsyncEngine, ator: Ator, **over: Any) -> Any:
    corpo: dict[str, Any] = {
        "unidade_id": SECA_COM_COFRE,
        "nota_fiscal": f"NF-{secrets.token_hex(3)}",
        "fornecedor": "Distribuidora Teste",
        "itens": [_item(COMUM)],
    }
    corpo.update(over)
    return await pipeline.executar(
        "recebimento_registrar",
        corpo,
        ator=ator,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
    )


async def _lotes_do(motor: AsyncEngine, recebimento_id: str) -> list[dict[str, Any]]:
    """Os lotes que a resposta do comando aponta, lidos do banco."""
    async with motor.connect() as c:
        aud = (
            (
                await c.execute(
                    sa.text(
                        "SELECT valor_novo FROM auditoria WHERE entidade='recebimento' "
                        "AND entidade_id=:r ORDER BY id DESC LIMIT 1"
                    ),
                    {"r": recebimento_id},
                )
            )
            .mappings()
            .one()
        )
        valor = aud["valor_novo"]
        ids = [x["lote_id"] for x in valor["lotes"]]
        linhas = (
            (await c.execute(sa.select(m.lote).where(m.lote.c.id.in_(ids)))).mappings().all()
        )
    return [dict(r) for r in linhas]


# ============================================================ AC-1 · quarentena
async def test_ac1_todo_lote_nasce_em_quarentena(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    r = await _registrar(motor, personas["cleide"], itens=[_item(COMUM), _item(COMUM)])
    lotes = await _lotes_do(motor, r.dados["recebimento_id"])
    assert len(lotes) == 2
    assert {x["status"] for x in lotes} == {"quarentena"}


async def test_ac1_schema_forjado_com_status_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O AC diz "nem por requisição forjada". Este É o forjado.

    `extra="forbid"` no schema faz a recusa ser VISÍVEL. Sem ele o campo seria
    silenciosamente ignorado — o lote ainda nasceria em quarentena, mas por
    acidente, e ninguém teria como auditar que a tentativa aconteceu.
    """
    with pytest.raises(ErroDominio) as e:
        await _registrar(motor, personas["cleide"], status="liberado")
    assert e.value.codigo == "invalido"


async def test_ac1_status_forjado_dentro_do_item_tambem_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O par que faltaria: forjar no ITEM, e não no corpo. `ItemRecebido` tem o
    mesmo `extra="forbid"`, e sem ele o campo passaria pela borda de fora."""
    with pytest.raises(ErroDominio) as e:
        await _registrar(motor, personas["cleide"], itens=[_item(COMUM, status="liberado")])
    assert e.value.codigo == "invalido"


def test_ac1_o_schema_nao_tem_campo_de_status_em_lugar_nenhum() -> None:
    """A camada 2, e a única forma honesta de testá-la.

    Sabotar o `INSERT` (trocar o `"quarentena"` literal por `getattr(item,
    "status", ...)`) **não reprova nada** enquanto o `extra="forbid"` estiver de
    pé, porque o campo nunca chega. Isso é defesa em profundidade funcionando —
    e é também o motivo de a camada 2 não ser falsificável isoladamente.

    O que dá para afirmar é o que a sustenta: **não existe campo de status em
    schema nenhum**. No dia em que alguém acrescentar um, este teste cai antes
    de o `INSERT` ter chance de usá-lo.
    """
    from estoque.application.commands.entradas.recebimento import (
        EntradaRecebimento,
        ItemRecebido,
    )

    assert "status" not in EntradaRecebimento.model_fields
    assert "status" not in ItemRecebido.model_fields
    # E os dois recusam extra — é o que faz a forja ser visível, não ignorada.
    for modelo in (EntradaRecebimento, ItemRecebido):
        assert modelo.model_config.get("extra") == "forbid", modelo.__name__


async def test_ac1_receber_em_lote_ja_liberado_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """`RN-R01` pelo caminho menos óbvio, e o que o `UNIQUE` do banco força.

    A tripla (produto, número, unidade) É a identidade do lote. Se o lote já
    existe e saiu da quarentena, acrescentar mercadoria nele seria **entrada
    direta em estoque liberado** — a coisa que a regra nomeia e proíbe.
    """
    numero = f"L{secrets.token_hex(4)}"
    await _registrar(motor, personas["cleide"], itens=[_item(COMUM, numero=numero)])
    async with motor.begin() as c:
        await c.execute(
            sa.text("UPDATE lote SET status='liberado' WHERE numero=:n AND produto_id=:p"),
            {"n": numero, "p": COMUM},
        )

    with pytest.raises(ErroDominio) as e:
        await _registrar(motor, personas["cleide"], itens=[_item(COMUM, numero=numero)])
    assert e.value.codigo == "conflito"
    assert "liberado" in e.value.mensagem_publica


async def test_ac1_receber_de_novo_no_mesmo_lote_em_quarentena_soma(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O contraponto: em quarentena, receber mais do mesmo lote é legítimo — e
    NÃO cria lote duplicado, que o `UNIQUE` recusaria."""
    numero = f"L{secrets.token_hex(4)}"
    um = await _registrar(motor, personas["cleide"], itens=[_item(COMUM, numero=numero)])
    dois = await _registrar(motor, personas["cleide"], itens=[_item(COMUM, numero=numero)])
    assert (await _lotes_do(motor, um.dados["recebimento_id"]))[0]["id"] == (
        await _lotes_do(motor, dois.dados["recebimento_id"])
    )[0]["id"]


# ========================================================== AC-2 · validade curta
async def test_ac2_validade_abaixo_de_seis_meses_e_recusada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    curto = _item(COMUM, validade=(date.today() + timedelta(days=60)).isoformat())
    with pytest.raises(ErroDominio) as e:
        await _registrar(motor, personas["cleide"], itens=[curto])
    assert e.value.codigo == "invalido"
    assert "RN-L07" in e.value.mensagem_publica


async def test_ac2_com_autorizacao_do_rt_e_aceita_e_registrada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O "salvo" da regra. E a autorização é registrada **com o que foi
    autorizado** — "houve autorização" sem dizer de quê não é auditável."""
    curto = _item(COMUM, validade=(date.today() + timedelta(days=60)).isoformat())
    r = await _registrar(
        motor,
        personas["cleide"],
        itens=[curto],
        autorizacao_validade_rt="RT autorizou: campanha de escoamento até março",
    )
    async with motor.connect() as c:
        aud = (
            (
                await c.execute(
                    sa.text(
                        "SELECT valor_novo FROM auditoria WHERE entidade='recebimento' "
                        "AND entidade_id=:r ORDER BY id DESC LIMIT 1"
                    ),
                    {"r": r.dados["recebimento_id"]},
                )
            )
            .mappings()
            .one()
        )
    assert aud["valor_novo"]["validade_curta_autorizada"] == [curto["numero"]]
    assert "campanha de escoamento" in aud["valor_novo"]["autorizacao_validade_rt"]


# ====================================================== AC-3 · cadeia fria
async def test_ac3_termolabil_sem_temperatura_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    with pytest.raises(ErroDominio) as e:
        await _registrar(
            motor, personas["cleide"], unidade_id=FRIA_SEM_COFRE, itens=[_item(TERMOLABIL)]
        )
    assert e.value.codigo == "invalido"
    assert "RN-F01" in e.value.mensagem_publica


async def test_ac3_com_temperatura_passa(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    r = await _registrar(
        motor,
        personas["cleide"],
        unidade_id=FRIA_SEM_COFRE,
        itens=[_item(TERMOLABIL)],
        temperatura_chegada_c=4.5,
    )
    assert r.dados["recebimento_id"]


async def test_ac3_produto_comum_nao_precisa_de_temperatura(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Exigir de todos treinaria o conferente a digitar um número qualquer."""
    r = await _registrar(motor, personas["cleide"], itens=[_item(COMUM)])
    assert r.dados["recebimento_id"]


# ============================================ AC-4 e AC-5 · alocação (RN-P02/P03)
async def test_ac4_termolabil_em_unidade_seca_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    with pytest.raises(ErroDominio) as e:
        await _registrar(
            motor,
            personas["cleide"],
            unidade_id=SECA_COM_COFRE,
            itens=[_item(TERMOLABIL)],
            temperatura_chegada_c=4.5,
        )
    assert e.value.codigo == "conflito"
    assert "RN-P02" in e.value.mensagem_publica


async def test_ac5_controlado_em_unidade_sem_sala_cofre_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    with pytest.raises(ErroDominio) as e:
        await _registrar(
            motor,
            personas["cleide"],
            unidade_id=FRIA_SEM_COFRE,
            itens=[_item(CONTROLADO)],
            rt_id="u-helena",
        )
    assert e.value.codigo == "conflito"
    assert "RN-P03" in e.value.mensagem_publica


async def test_ac5_controlado_em_unidade_com_cofre_passa(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    r = await _registrar(motor, personas["cleide"], itens=[_item(CONTROLADO)], rt_id="u-helena")
    assert r.dados["recebimento_id"]


# ================================================ RN-R05 · dupla identificação
async def test_controlado_sem_rt_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    with pytest.raises(ErroDominio) as e:
        await _registrar(motor, personas["cleide"], itens=[_item(CONTROLADO)])
    assert e.value.codigo == "invalido"
    assert "RN-R05" in e.value.mensagem_publica


async def test_rt_igual_ao_conferente_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O par negativo que separa "dupla identificação" de "digitar o próprio
    nome duas vezes". É o mesmo cuidado do `CHECK` que a T-030 pôs no banco."""
    cleide = personas["cleide"]
    with pytest.raises(ErroDominio) as e:
        await _registrar(motor, cleide, itens=[_item(CONTROLADO)], rt_id=cleide.id)
    assert e.value.codigo == "invalido"
    assert "duas pessoas" in e.value.mensagem_publica


# ==================================================== AC-6 · divergência (RN-R04)
async def test_ac6_divergencia_conclui_e_cria_pendencia(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    r = await _registrar(
        motor, personas["cleide"], itens=[_item(COMUM, quantidade=8, quantidade_nota=10)]
    )
    assert r.dados["divergencia"] is True
    async with motor.connect() as c:
        linha = (
            (
                await c.execute(
                    sa.select(m.recebimento).where(
                        m.recebimento.c.id == r.dados["recebimento_id"]
                    )
                )
            )
            .mappings()
            .one()
        )
    # NÃO impede: o recebimento existe e está concluído, com a pendência marcada.
    assert linha["divergencia"] is True
    assert linha["status"] == "conferido"


async def test_ac6_sem_divergencia_a_pendencia_nao_e_criada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    r = await _registrar(
        motor, personas["cleide"], itens=[_item(COMUM, quantidade=10, quantidade_nota=10)]
    )
    assert r.dados["divergencia"] is False


# ======================================================= AC-7 · quem NÃO pode
@pytest.mark.parametrize("nome", ["marco", "rafael", "sandra"])
async def test_ac7_quem_nao_tem_recebimento_criar_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator], nome: str
) -> None:
    """Direto no pipeline — é o que uma requisição forjada alcança. Marco é o
    Diretor: papel não é nível, é conjunto (`RN-A03`)."""
    assert "recebimento.criar" not in personas[nome].permissoes
    with pytest.raises(ErroDominio) as e:
        await _registrar(motor, personas[nome])
    assert e.value.codigo == "nao_autorizado"


@pytest.mark.parametrize("nome", ["cleide", "ivo"])
async def test_ac7_quem_tem_a_permissao_passa(
    motor: AsyncEngine, personas: dict[str, Ator], nome: str
) -> None:
    """O contraponto. Sem ele, um comando que recusasse todo mundo deixaria os
    três testes acima verdes."""
    r = await _registrar(motor, personas[nome])
    assert r.dados["recebimento_id"]


async def test_unidade_fora_do_escopo_e_recusada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """`RN-A01` também na escrita. Odair alcança só Uberlândia, e a negativa de
    escopo DECLARADO é explícita (ADR-0014) — a unidade existe e ele sabe."""
    with pytest.raises(ErroDominio) as e:
        await _registrar(motor, personas["odair"], unidade_id=SECA_COM_COFRE)
    assert e.value.codigo == "nao_autorizado"


# ================================================== o efeito e a trilha
async def test_o_movimento_de_entrada_acompanha_o_lote(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Saldo é soma de movimento (`RN-M06`): um lote sem entrada nasceria com
    saldo zero, e a mercadoria estaria no chão e não no sistema."""
    r = await _registrar(motor, personas["cleide"], itens=[_item(COMUM, quantidade=7)])
    lote_id = (await _lotes_do(motor, r.dados["recebimento_id"]))[0]["id"]
    async with motor.connect() as c:
        mov = (
            (await c.execute(sa.select(m.movimento).where(m.movimento.c.lote_id == lote_id)))
            .mappings()
            .all()
        )
    assert len(mov) == 1
    assert mov[0]["tipo"] == "entrada"
    assert mov[0]["quantidade"] == 7
    assert mov[0]["motivo"] == "recebimento"
    assert mov[0]["status"] == "efetivado"


async def test_o_relogio_e_do_servidor(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    """`RN-M04`. `ctx.agora` vem do pipeline; um comando que lesse o próprio
    relógio teria uma noção de "agora" diferente da que a auditoria registrou."""
    antes = datetime.now(UTC)
    r = await _registrar(motor, personas["cleide"])
    async with motor.connect() as c:
        recebido = (
            await c.execute(
                sa.select(m.recebimento.c.recebido_em).where(
                    m.recebimento.c.id == r.dados["recebimento_id"]
                )
            )
        ).scalar_one()
    assert antes <= recebido <= datetime.now(UTC)
