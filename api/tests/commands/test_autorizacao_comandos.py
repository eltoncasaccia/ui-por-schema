"""T-030 AC-1 a AC-5 — o fluxo de duas pessoas, ponta a ponta, contra Postgres.

Cada teste percorre o caminho inteiro do `CA-04`: Cleide submete pela T-028, o
movimento fica pendente e o saldo NÃO muda, Helena decide aqui. Testar as duas
metades separadas provaria menos — o critério do cliente é a costura entre elas.

**AC-3 é o critério central**, e a armadilha está escrita na tarefa: tem de ser
testado com requisição DIRETA, não pela interface. A interface esconde o botão; o
servidor é quem precisa recusar. E abaixo dele o banco recusa de novo.

Pulam sem banco: `make db-local && make db-teste`.
"""

import secrets
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

import banco
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

import estoque.application.commands.indice  # noqa: F401  — registra os comandos
from estoque.application.commands import pipeline
from estoque.application.commands.autorizacao import _etag_do_movimento
from estoque.application.commands.saida import _etag_da_saida, _saldo
from estoque.application.commands.tipos import ContextoComando
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator

URL = banco.URL_APP_ASYNC
URL_SONDA = banco.URL_APP

PROD = "t030-prod"  # controlado
LOTE = "t030-lote"

MOTIVO = "receituário conferido e arquivado"


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
                "(:p,'7899','Clonazepam 2mg','N','clonazepam','controlado','A',true,2100) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PROD},
        )
        await c.execute(
            sa.text(
                "INSERT INTO lote VALUES (:l,:p,'CLO-01','cd-matriz',:f,:v,'liberado',null) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "l": LOTE,
                "p": PROD,
                "f": hoje - timedelta(days=200),
                "v": hoje + timedelta(days=500),
            },
        )
        await c.execute(
            sa.text(
                "UPDATE lote SET produto_id=:p, status='liberado', validade=:v WHERE id=:l"
            ),
            {"l": LOTE, "p": PROD, "v": hoje + timedelta(days=500)},
        )
        # Entrada nova a cada teste: o razão é append-only e não se limpa.
        await c.execute(
            sa.text(
                "INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,"
                "autor_id,status,criado_em) VALUES "
                "(:i,:l,'cd-matriz','entrada',100000,'recebimento',:a,'efetivado',now())"
            ),
            {"i": f"t030-ent-{secrets.token_hex(6)}", "l": LOTE, "a": personas["cleide"].id},
        )
        for a in personas.values():
            await c.execute(
                sa.text(
                    "INSERT INTO usuario VALUES (:i,:n,:e,'x',:pp,true) ON CONFLICT DO NOTHING"
                ),
                {"i": a.id, "n": a.nome, "e": f"{a.id}@bertoni.test", "pp": a.papel},
            )


# ------------------------------------------------------------------ auxiliares
class _Alvo:
    def __init__(self, **kw: Any) -> None:
        for k, v in kw.items():
            setattr(self, k, v)


async def saldo(motor: AsyncEngine, ator: Ator) -> int:
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        return await _saldo(LOTE, ctx)


async def _etag(motor: AsyncEngine, ator: Ator, *, lote: bool, ident: str) -> str:
    alvo = _Alvo(lote_id=ident) if lote else _Alvo(movimento_id=ident)
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        e = await (_etag_da_saida(alvo, ctx) if lote else _etag_do_movimento(alvo, ctx))
    return e or "fora-de-escopo"


async def submeter(motor: AsyncEngine, quem: Ator, quantidade: int = 12) -> str:
    """Cleide submete a saída de controlado (T-028). Devolve o movimento pendente."""
    r = await pipeline.executar(
        "movimento_saida",
        {
            "lote_id": LOTE,
            "quantidade": quantidade,
            "motivo": "venda",
            "cliente_id": "cli-777",
            "nota_fiscal": "NF-30030",
        },
        ator=quem,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await _etag(motor, quem, lote=True, ident=LOTE),
    )
    assert r.dados["status"] == "aguardando_autorizacao"
    return str(r.dados["movimento_id"])


async def decidir(
    motor: AsyncEngine, quem: Ator, movimento_id: str, decisao: str = "autorizar", **extra: Any
) -> Any:
    corpo: dict[str, Any] = {
        "movimento_id": movimento_id,
        "decisao": decisao,
        "motivo": MOTIVO,
    }
    corpo.update(extra)
    return await pipeline.executar(
        "controlado_autorizar",
        corpo,
        ator=quem,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await _etag(motor, quem, lote=False, ident=movimento_id),
    )


async def movimento(motor: AsyncEngine, mid: str) -> dict[str, Any]:
    async with motor.connect() as c:
        linha = (
            (await c.execute(sa.select(m.movimento).where(m.movimento.c.id == mid)))
            .mappings()
            .one()
        )
    return dict(linha)


# ------------------------------------------------- AC-1 · pendente não muda saldo
async def test_ac1_o_pendente_nao_altera_o_saldo(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """`CA-04`, `AC-06.1`. É a metade que T-028 entregou; aqui ela é reafirmada
    no começo do fluxo completo, porque tudo o mais depende dela ser verdade."""
    cleide, helena = personas["cleide"], personas["helena"]
    antes = await saldo(motor, cleide)
    mid = await submeter(motor, cleide)
    assert await saldo(motor, cleide) == antes, "o saldo mudou antes da autorização"
    assert (await movimento(motor, mid))["status"] == "aguardando_autorizacao"
    assert await saldo(motor, helena) == antes


# ---------------------------------------- AC-2 · duas identidades, distintas
async def test_ac2_apos_autorizar_grava_as_duas_identidades(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-C01. As duas, e DISTINTAS — é a definição de dupla identificação."""
    cleide, helena = personas["cleide"], personas["helena"]
    antes = await saldo(motor, cleide)
    mid = await submeter(motor, cleide)

    r = await decidir(motor, helena, mid)
    assert r.dados["status"] == "efetivado"

    mov = await movimento(motor, mid)
    assert mov["autor_id"] == cleide.id
    assert mov["autorizador_id"] == helena.id
    assert mov["autor_id"] != mov["autorizador_id"]
    # Efetivação atômica: o saldo muda no mesmo instante.
    assert await saldo(motor, cleide) == antes - 12


async def test_ac2_a_efetivacao_e_atomica(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Status e saldo mudam juntos. Se o status virasse `efetivado` sem o saldo
    acompanhar, o livro-razão e o estoque contábil discordariam — que é a
    divergência de 3,8% que o projeto existe para não repetir."""
    cleide, helena = personas["cleide"], personas["helena"]
    antes = await saldo(motor, cleide)
    mid = await submeter(motor, cleide, quantidade=7)
    await decidir(motor, helena, mid)
    assert (await movimento(motor, mid))["status"] == "efetivado"
    assert await saldo(motor, cleide) == antes - 7


# -------------------------------------- AC-3 · a mesma pessoa não faz as duas
async def test_ac3_quem_submeteu_nao_autoriza_nem_por_requisicao_direta(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A04, **o critério central da tarefa**.

    Aqui não há interface: é o pipeline chamado direto, que é o que uma
    requisição forjada faz. Se um dia Cleide ganhar `controlado.autorizar` por
    engano numa linha da matriz, é esta recusa que continua valendo.
    """
    cleide = personas["cleide"]
    antes = await saldo(motor, cleide)
    mid = await submeter(motor, cleide)

    # Cleide COM a permissão de autorizar — o erro de uma linha no dicionário.
    cleide_poderosa = replace(cleide, permissoes=cleide.permissoes | {"controlado.autorizar"})
    with pytest.raises(ErroDominio) as e:
        await decidir(motor, cleide_poderosa, mid)
    assert e.value.codigo == "invalido"
    assert "pessoas diferentes" in e.value.mensagem_publica

    assert (await movimento(motor, mid))["status"] == "aguardando_autorizacao"
    assert await saldo(motor, cleide) == antes


async def test_ac3_o_banco_recusa_a_mesma_pessoa_por_baixo(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """A terceira camada. Mesmo que todo o código acima fosse contornado, o
    CHECK da migração 0001 não deixa `autorizador_id = autor_id` existir.

    Separação de funções com peso regulatório não pode depender de um `if` no
    servidor — um caminho novo esqueceria a checagem.
    """
    cleide = personas["cleide"]
    mid = await submeter(motor, cleide)
    with pytest.raises(Exception, match="movimento_check"):
        async with motor.begin() as c:
            await c.execute(
                sa.text(
                    "UPDATE movimento SET status='efetivado', autorizador_id=:a WHERE id=:i"
                ),
                {"a": cleide.id, "i": mid},
            )
    assert (await movimento(motor, mid))["status"] == "aguardando_autorizacao"


async def test_ac3_outra_pessoa_autoriza_normalmente(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O par positivo — sem ele, um comando que recusasse todo mundo passaria em
    todos os negativos acima."""
    mid = await submeter(motor, personas["cleide"])
    r = await decidir(motor, personas["helena"], mid)
    assert r.dados["status"] == "efetivado"


# ------------------------------------------------------- AC-4 · só o RT, direto
@pytest.mark.parametrize("quem", ["marco", "ivo", "odair", "cleide", "rafael", "sandra"])
async def test_ac4_ninguem_alem_do_rt_autoriza(
    motor: AsyncEngine, personas: dict[str, Ator], quem: str
) -> None:
    """RN-C01 pela matriz. Marco é o Diretor: tem mais permissões que Helena e
    nenhuma delas é `controlado.autorizar`."""
    cleide = personas["cleide"]
    antes = await saldo(motor, cleide)
    mid = await submeter(motor, cleide)
    with pytest.raises(ErroDominio) as e:
        await decidir(motor, personas[quem], mid)
    assert e.value.codigo == "nao_autorizado"
    assert (await movimento(motor, mid))["status"] == "aguardando_autorizacao"
    assert await saldo(motor, cleide) == antes


async def test_ac4_rt_desativada_nao_autoriza(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A06: desligamento com efeito imediato, mesmo com a permissão na mão."""
    mid = await submeter(motor, personas["cleide"])
    with pytest.raises(ErroDominio) as e:
        await decidir(motor, replace(personas["helena"], ativo=False), mid)
    assert e.value.codigo == "nao_autorizado"


# ------------------------------------------------- AC-5 · recusa não apaga nada
async def test_ac5_recusa_nao_altera_saldo_e_fica_registrada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-M02: nada é apagado. O movimento recusado FICA, com quem recusou e por
    quê, e continua fora do saldo porque só `efetivado` conta."""
    cleide, helena = personas["cleide"], personas["helena"]
    antes = await saldo(motor, cleide)
    mid = await submeter(motor, cleide)
    r = await decidir(motor, helena, mid, decisao="recusar")

    assert r.dados["status"] == "recusado"
    assert await saldo(motor, cleide) == antes

    mov = await movimento(motor, mid)
    assert mov["status"] == "recusado"
    assert mov["autorizador_id"] == helena.id
    assert mov["quantidade"] == 12, "a recusa não pode ter mexido no que foi pedido"


async def test_ac5_a_recusa_guarda_o_motivo_na_trilha(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-D01. "Recusado" sozinho não reconstrói a decisão, e reconstruir é para
    o que a trilha existe."""
    cleide, helena = personas["cleide"], personas["helena"]
    mid = await submeter(motor, cleide)
    await decidir(motor, helena, mid, decisao="recusar", motivo="receituário sem assinatura")

    async with motor.connect() as c:
        linha = (
            (
                await c.execute(
                    sa.select(m.auditoria).where(
                        m.auditoria.c.acao == "controlado_autorizar",
                        m.auditoria.c.entidade_id == mid,
                    )
                )
            )
            .mappings()
            .one()
        )
    assert linha["ator_id"] == helena.id
    assert linha["valor_anterior"]["status"] == "aguardando_autorizacao"
    assert linha["valor_novo"]["status"] == "recusado"
    assert linha["valor_novo"]["motivo"] == "receituário sem assinatura"
    assert linha["valor_novo"]["autor_id"] == cleide.id


async def test_ac5_movimento_ja_resolvido_nao_e_decidido_de_novo(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Autorizar duas vezes tiraria o dobro do estoque; recusar depois de
    autorizar apagaria o efeito. As duas são recusadas — e o gatilho do banco
    recusa de novo, por baixo."""
    cleide, helena = personas["cleide"], personas["helena"]
    mid = await submeter(motor, cleide)
    await decidir(motor, helena, mid)
    depois = await saldo(motor, cleide)

    for decisao in ("autorizar", "recusar"):
        with pytest.raises(ErroDominio) as e:
            await decidir(motor, helena, mid, decisao=decisao)
        assert e.value.codigo == "conflito"
    assert await saldo(motor, cleide) == depois


async def test_ac5_o_gatilho_do_banco_recusa_desfazer_um_efetivado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """A camada de baixo, sozinha. Migração 0004: o GRANT por coluna permitiria
    virar um `efetivado` em `recusado` — apagar o efeito de um movimento é
    reescrever história com outro nome, e o gatilho é o que impede."""
    cleide, helena = personas["cleide"], personas["helena"]
    mid = await submeter(motor, cleide)
    await decidir(motor, helena, mid)
    with pytest.raises(Exception, match="definitivo"):
        async with motor.begin() as c:
            await c.execute(
                sa.text(
                    "UPDATE movimento SET status='recusado', autorizador_id=:a WHERE id=:i"
                ),
                {"a": helena.id, "i": mid},
            )


# -------------------------------------------- RN-M02 · o que continua imutável
async def test_a_autorizacao_nao_abriu_a_porta_para_editar_o_movimento(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O GRANT da migração 0004 é POR COLUNA, e este é o teste que prova.

    Se um dia alguém trocar por `GRANT UPDATE ON movimento`, a suíte inteira
    continua verde — menos este.
    """
    mid = await submeter(motor, personas["cleide"])
    for coluna, valor in (
        ("quantidade", "999"),
        ("lote_id", "'outro'"),
        ("autor_id", "'u-marco'"),
        ("criado_em", "now()"),
    ):
        with pytest.raises(Exception, match="permission denied"):
            async with motor.begin() as c:
                await c.execute(
                    # S608: `coluna` e `valor` são literais desta lista, não
                    # entrada externa — o teste PRECISA montar o SQL para provar
                    # que o GRANT é por coluna.
                    sa.text(f"UPDATE movimento SET {coluna} = {valor} WHERE id = :i"),  # noqa: S608
                    {"i": mid},
                )
    with pytest.raises(Exception, match="permission denied"):
        async with motor.begin() as c:
            await c.execute(sa.text("DELETE FROM movimento WHERE id = :i"), {"i": mid})


async def test_o_gatilho_exige_a_segunda_identidade(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Sem isto, `status` mudaria sozinho e a dupla identificação ficaria com uma
    identidade só — que é exatamente o que `CA-04` proíbe."""
    mid = await submeter(motor, personas["cleide"])
    with pytest.raises(Exception, match="segunda identidade"):
        async with motor.begin() as c:
            await c.execute(
                sa.text("UPDATE movimento SET status='efetivado' WHERE id=:i"), {"i": mid}
            )


# ------------------------------------------------------ escopo, motivo, saldo
async def test_movimento_fora_do_escopo_nao_e_encontrado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A01 e ADR-0014: uma RT com escopo restrito não decide o que não alcança,
    e a negativa é indistinguível de inexistente."""
    mid = await submeter(motor, personas["cleide"])
    rt_de_uberlandia = replace(personas["helena"], unidades=frozenset({"filial-uberlandia"}))
    with pytest.raises(ErroDominio) as fora:
        await decidir(motor, rt_de_uberlandia, mid)
    with pytest.raises(ErroDominio) as inexistente:
        await decidir(motor, personas["helena"], "m-nao-existe")
    assert fora.value.codigo == "nao_encontrado"
    assert fora.value.mensagem_publica == inexistente.value.mensagem_publica


async def test_motivo_curto_e_recusado(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    mid = await submeter(motor, personas["cleide"])
    with pytest.raises(ErroDominio) as e:
        await decidir(motor, personas["helena"], mid, motivo="ok")
    assert e.value.codigo == "invalido"
    assert (await movimento(motor, mid))["status"] == "aguardando_autorizacao"


async def test_saldo_e_reconferido_na_efetivacao(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Entre a submissão e a autorização podem passar dias. Efetivar sem
    reconferir levaria o saldo a negativo em nome de uma decisão tomada sobre um
    estoque que não existe mais — `RN-M01` vale no instante em que o movimento
    passa a contar."""
    cleide, helena = personas["cleide"], personas["helena"]
    atual = await saldo(motor, cleide)
    mid = await submeter(motor, cleide, quantidade=atual)

    # Alguém esvazia o lote enquanto o pedido espera.
    async with motor.begin() as c:
        await c.execute(
            sa.text(
                "INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,"
                "autor_id,status,criado_em) VALUES "
                "(:i,:l,'cd-matriz','saida',:q,'avaria',:a,'efetivado',now())"
            ),
            {"i": f"t030-drena-{secrets.token_hex(4)}", "l": LOTE, "q": atual, "a": cleide.id},
        )

    with pytest.raises(ErroDominio) as e:
        await decidir(motor, helena, mid)
    assert e.value.codigo == "conflito"
    assert "insuficiente" in e.value.mensagem_publica
    assert (await movimento(motor, mid))["status"] == "aguardando_autorizacao"


async def test_repetir_a_chave_nao_autoriza_duas_vezes(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    cleide, helena = personas["cleide"], personas["helena"]
    antes = await saldo(motor, cleide)
    mid = await submeter(motor, cleide, quantidade=9)
    chave = secrets.token_hex(8)
    corpo = {"movimento_id": mid, "decisao": "autorizar", "motivo": MOTIVO}
    etag = await _etag(motor, helena, lote=False, ident=mid)
    um = await pipeline.executar(
        "controlado_autorizar",
        corpo,
        ator=helena,
        motor=motor,
        origem="tela",
        idempotency_key=chave,
        if_match=etag,
    )
    dois = await pipeline.executar(
        "controlado_autorizar",
        corpo,
        ator=helena,
        motor=motor,
        origem="tela",
        idempotency_key=chave,
        if_match=etag,
    )
    assert dois.repetido is True
    assert dois.dados == um.dados
    assert await saldo(motor, cleide) == antes - 9
