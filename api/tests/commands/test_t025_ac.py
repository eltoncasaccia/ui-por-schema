"""T-025 AC-2 a AC-7 — o pipeline de escrita contra Postgres de verdade.

Estes testes NAO usam repositorio falso, e a escolha e' deliberada. O AC-7 diz
que comando recusado nao deixa efeito parcial; um armazenamento em memoria
"passaria" nesse teste sem nunca ter havido transacao — que e' exatamente o
aviso registrado em `data/porta.py`, na docstring de `Transacao`.

A conexao e' a do papel `estoque_app`, nao a do dono. E' o papel com que a
aplicacao roda de verdade, e o unico contra o qual os REVOKE da migracao 0001
significam alguma coisa.

Pulam sem banco: `make db-local && make migrate`, e `make db-local` DE NOVO.
"""

import os
import secrets
from typing import Any

import pytest
import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from estoque.commands import pipeline
from estoque.commands.tipos import Comando, ContextoComando, Efeito
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator

URL = os.environ.get(
    "DATABASE_URL_TESTE_APP_ASYNC",
    "postgresql+asyncpg://estoque_app:app@localhost:15432/estoque",
)
# Sonda sincrona so' para decidir entre rodar e pular — o driver async nao
# oferece jeito de perguntar "tem banco?" fora de um event loop.
URL_SONDA = os.environ.get(
    "DATABASE_URL_TESTE_APP",
    "postgresql+psycopg://estoque_app:app@localhost:15432/estoque",
)

UNIDADE = "cd-matriz"
LOTE = "t025-lote"
PRODUTO = "t025-prod"


# --------------------------------------------------------------- comandos de teste
# Comandos concretos sao T-026 a T-030. Estes tres existem para exercitar o
# pipeline, e cobrem as tres formas que ele precisa tratar: criacao nao
# idempotente, atualizacao com etag, e comando que falha depois de ja' ter
# escrito.
class EntradaSaida(BaseModel):
    lote_id: str
    quantidade: int = Field(gt=0)


async def _aplicar_saida(entrada: Any, ctx: ContextoComando) -> Efeito:
    mid = f"t025-mov-{secrets.token_hex(6)}"
    await ctx.conn.execute(
        sa.insert(m.movimento).values(
            id=mid,
            lote_id=entrada.lote_id,
            unidade_id=UNIDADE,
            tipo="saida",
            quantidade=entrada.quantidade,
            motivo="venda",
            autor_id=ctx.ator.id,
            status="efetivado",
            criado_em=ctx.agora,  # RN-M04 — do servidor, via ctx
        )
    )
    return Efeito(
        entidade="movimento",
        entidade_id=mid,
        valor_anterior=None,
        valor_novo={"quantidade": entrada.quantidade, "tipo": "saida"},
        dados={"movimento_id": mid, "criado_em": ctx.agora.isoformat()},
    )


class EntradaStatus(BaseModel):
    lote_id: str
    status: str


async def _etag_do_lote(entrada: Any, ctx: ContextoComando) -> str | None:
    linha = (
        (await ctx.conn.execute(sa.select(m.lote).where(m.lote.c.id == entrada.lote_id)))
        .mappings()
        .first()
    )
    return None if linha is None else pipeline.etag_de_valores(dict(linha))


async def _aplicar_status(entrada: Any, ctx: ContextoComando) -> Efeito:
    antes = (
        (
            await ctx.conn.execute(
                sa.select(m.lote.c.status).where(m.lote.c.id == entrada.lote_id)
            )
        )
        .mappings()
        .one()
    )
    await ctx.conn.execute(
        sa.update(m.lote).where(m.lote.c.id == entrada.lote_id).values(status=entrada.status)
    )
    return Efeito(
        entidade="lote",
        entidade_id=entrada.lote_id,
        valor_anterior={"status": antes["status"]},
        valor_novo={"status": entrada.status},
        dados={"lote_id": entrada.lote_id, "status": entrada.status},
    )


async def _aplicar_e_falhar(entrada: Any, ctx: ContextoComando) -> Efeito:
    """Escreve e SO' DEPOIS falha. Se o teste passasse com a falha antes da
    escrita, ele nao estaria provando rollback nenhum."""
    await _aplicar_saida(entrada, ctx)
    raise ErroDominio("invalido", "Regra de dominio recusou a operacao.")


class EntradaComRelogio(BaseModel):
    """Schema que ACEITA um `criado_em` do cliente.

    Existe para provar a limpeza de verdade: um comando que simplesmente ignora
    o campo passaria no teste sem o pipeline ter feito nada. Este ecoa o que
    recebeu, e o teste afirma que recebeu nada."""

    lote_id: str
    criado_em: str | None = None


async def _aplicar_eco(entrada: Any, ctx: ContextoComando) -> Efeito:
    return Efeito(
        entidade="lote",
        entidade_id=entrada.lote_id,
        valor_anterior=None,
        valor_novo={"eco": entrada.criado_em},
        dados={"recebido_do_cliente": entrada.criado_em, "do_servidor": ctx.agora.isoformat()},
    )


CMD_ECO = pipeline.registrar(
    Comando(
        nome="t025_eco",
        requires=("movimento.criar",),
        schema=EntradaComRelogio,
        aplicar=_aplicar_eco,
        idempotent=True,
    )
)

CMD_SAIDA = pipeline.registrar(
    Comando(
        nome="t025_saida",
        requires=("movimento.criar",),
        schema=EntradaSaida,
        aplicar=_aplicar_saida,
        idempotent=False,
    )
)
CMD_STATUS = pipeline.registrar(
    Comando(
        nome="t025_status",
        requires=("lote.status",),
        schema=EntradaStatus,
        aplicar=_aplicar_status,
        idempotent=True,
        etag_de=_etag_do_lote,
    )
)
CMD_FALHA = pipeline.registrar(
    Comando(
        nome="t025_falha",
        requires=("movimento.criar",),
        schema=EntradaSaida,
        aplicar=_aplicar_e_falhar,
        idempotent=False,
    )
)


# -------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def motor() -> AsyncEngine:
    """`NullPool` de proposito: cada teste roda no seu proprio event loop, e uma
    conexao asyncpg reaproveitada de um loop morto falha de um jeito que parece
    bug do pipeline. Sem pool, cada conexao nasce e morre no loop que a usa."""
    try:
        sonda = sa.create_engine(URL_SONDA, connect_args={"connect_timeout": 2})
        with sonda.connect():
            pass
    except Exception:
        pytest.skip("sem banco: rode `make db-local && make migrate && make db-local`")
    return create_async_engine(URL, future=True, poolclass=NullPool)


@pytest.fixture(autouse=True)
async def _semear(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    """Estado conhecido antes de cada teste.

    Limpa apenas o que estes testes criam. Nao usa TRUNCATE: o papel da
    aplicacao nao tem esse privilegio, e pedir mais privilegio para o teste
    passar seria testar um sistema que nao e' o que roda.
    """
    # Uma instrucao por `execute`: asyncpg usa prepared statement e recusa varias
    # instrucoes no mesmo comando.
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
                "(:p,'7890','Amoxicilina','F','amox','comum','A',true,1250) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PRODUTO},
        )
        await c.execute(
            sa.text(
                "INSERT INTO lote VALUES "
                "(:l,:p,'L-001','cd-matriz','2025-01-01','2027-01-01','quarentena',null) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PRODUTO, "l": LOTE},
        )
        for a in personas.values():
            await c.execute(
                sa.text(
                    "INSERT INTO usuario VALUES (:i,:n,:e,'x',:pp,true) ON CONFLICT DO NOTHING"
                ),
                {"i": a.id, "n": a.nome, "e": f"{a.id}@bertoni.test", "pp": a.papel},
            )
        # Estado inicial do lote. As chaves de idempotencia NAO sao limpas: o
        # papel da aplicacao nao tem DELETE nessa tabela, de proposito (migracao
        # 0003), e cada teste gera a sua chave aleatoria.
        await c.execute(sa.text("UPDATE lote SET status='quarentena' WHERE id=:l"), {"l": LOTE})


async def _movimentos(motor: AsyncEngine) -> int:
    async with motor.connect() as c:
        return (
            await c.execute(
                sa.select(sa.func.count())
                .select_from(m.movimento)
                .where(m.movimento.c.lote_id == LOTE)
            )
        ).scalar_one()


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


def _chave() -> str:
    return f"t025-{secrets.token_hex(8)}"


# ---------------------------------------------------- AC-2 · autorizacao no servidor
async def test_ac2_quem_pode_executa(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    r = await pipeline.executar(
        "t025_status",
        {"lote_id": LOTE, "status": "liberado"},
        ator=personas["helena"],
        motor=motor,
        origem="tela",
        if_match=await _etag_atual(motor),
    )
    assert r.dados["status"] == "liberado"


async def test_ac2_quem_nao_pode_e_recusado_no_servidor(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A03. Ivo e' gerente: nao tem `lote.status`. A interface ja' teria
    escondido o botao — e esconder nao e' controlar. Aqui ele chama o pipeline
    direto, que e' o que uma requisicao forjada faz."""
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "t025_status",
            {"lote_id": LOTE, "status": "liberado"},
            ator=personas["ivo"],
            motor=motor,
            origem="tela",
            if_match=await _etag_atual(motor),
        )
    assert e.value.codigo == "nao_autorizado"
    assert await _status_do_lote(motor) == "quarentena", "recusado nao pode ter aplicado"


async def test_ac2_ator_inativo_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A06: desligamento tem efeito imediato, inclusive com permissao na mao."""
    from dataclasses import replace

    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "t025_status",
            {"lote_id": LOTE, "status": "liberado"},
            ator=replace(personas["helena"], ativo=False),
            motor=motor,
            origem="tela",
            if_match=await _etag_atual(motor),
        )
    assert e.value.codigo == "nao_autorizado"


async def test_ac2_autorizacao_vem_antes_da_validacao(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Ivo manda corpo invalido para um comando que ele nao pode executar.

    A resposta precisa ser `nao_autorizado`, nunca `invalido`: um erro de schema
    ensinaria a quem nao pode executar o comando qual e' o formato dele."""
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "t025_status",
            {"lixo": True},
            ator=personas["ivo"],
            motor=motor,
            origem="tela",
        )
    assert e.value.codigo == "nao_autorizado"


# ------------------------------------------------------------ AC-3 · idempotencia
async def test_ac3_mesma_chave_produz_um_efeito_e_a_mesma_resposta(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    antes = await _movimentos(motor)
    chave = _chave()
    corpo = {"lote_id": LOTE, "quantidade": 3}

    um = await pipeline.executar(
        "t025_saida",
        corpo,
        ator=personas["ivo"],
        motor=motor,
        origem="tela",
        idempotency_key=chave,
    )
    dois = await pipeline.executar(
        "t025_saida",
        corpo,
        ator=personas["ivo"],
        motor=motor,
        origem="tela",
        idempotency_key=chave,
    )

    assert await _movimentos(motor) == antes + 1, "a repeticao gravou de novo"
    assert dois.dados == um.dados
    assert dois.repetido is True
    assert um.repetido is False


async def test_ac3_chave_diferente_produz_efeito_novo(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O par do teste acima: sem ele, um pipeline que nunca grava nada passaria."""
    antes = await _movimentos(motor)
    corpo = {"lote_id": LOTE, "quantidade": 3}
    for _ in range(2):
        await pipeline.executar(
            "t025_saida",
            corpo,
            ator=personas["ivo"],
            motor=motor,
            origem="tela",
            idempotency_key=_chave(),
        )
    assert await _movimentos(motor) == antes + 2


async def test_ac3_mesma_chave_com_corpo_outro_e_conflito(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    chave = _chave()
    await pipeline.executar(
        "t025_saida",
        {"lote_id": LOTE, "quantidade": 3},
        ator=personas["ivo"],
        motor=motor,
        origem="tela",
        idempotency_key=chave,
    )
    antes = await _movimentos(motor)
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "t025_saida",
            {"lote_id": LOTE, "quantidade": 99},
            ator=personas["ivo"],
            motor=motor,
            origem="tela",
            idempotency_key=chave,
        )
    assert e.value.codigo == "conflito"
    assert await _movimentos(motor) == antes


async def test_ac3_chave_de_outro_ator_nao_reproduz_a_resposta(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """A chave e' `(chave, ator)`. Chave global seria um canal para ler a
    resposta de outra pessoa apresentando a chave dela."""
    chave = _chave()
    corpo = {"lote_id": LOTE, "quantidade": 3}
    de_ivo = await pipeline.executar(
        "t025_saida",
        corpo,
        ator=personas["ivo"],
        motor=motor,
        origem="tela",
        idempotency_key=chave,
    )
    antes = await _movimentos(motor)
    de_cleide = await pipeline.executar(
        "t025_saida",
        corpo,
        ator=personas["cleide"],
        motor=motor,
        origem="tela",
        idempotency_key=chave,
    )
    assert de_cleide.repetido is False, "reproduziu a resposta de outro ator"
    assert de_cleide.dados["movimento_id"] != de_ivo.dados["movimento_id"]
    assert await _movimentos(motor) == antes + 1


async def test_ac3_escrita_nao_idempotente_exige_a_chave(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """CONTRATOS §8. Sem esta recusa, a idempotencia seria opcional — e opcional
    e' o mesmo que ausente no cliente que repete por causa de timeout."""
    antes = await _movimentos(motor)
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "t025_saida",
            {"lote_id": LOTE, "quantidade": 3},
            ator=personas["ivo"],
            motor=motor,
            origem="tela",
        )
    assert e.value.codigo == "invalido"
    assert await _movimentos(motor) == antes


# ------------------------------------------------------------- AC-4 · If-Match
async def _etag_atual(motor: AsyncEngine) -> str:
    async with motor.connect() as c:
        linha = (await c.execute(sa.select(m.lote).where(m.lote.c.id == LOTE))).mappings().one()
    return pipeline.etag_de_valores(dict(linha))


async def _status_do_lote(motor: AsyncEngine) -> str:
    async with motor.connect() as c:
        status = (
            await c.execute(sa.select(m.lote.c.status).where(m.lote.c.id == LOTE))
        ).scalar_one()
    return str(status)


async def test_ac4_etag_antigo_devolve_conflito_sem_aplicar(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    velho = await _etag_atual(motor)
    await pipeline.executar(
        "t025_status",
        {"lote_id": LOTE, "status": "bloqueado"},
        ator=personas["helena"],
        motor=motor,
        origem="tela",
        if_match=velho,
    )
    assert await _status_do_lote(motor) == "bloqueado"

    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "t025_status",
            {"lote_id": LOTE, "status": "liberado"},
            ator=personas["helena"],
            motor=motor,
            origem="tela",
            if_match=velho,
        )
    assert e.value.codigo == "conflito"
    assert await _status_do_lote(motor) == "bloqueado", "conflito nao pode ter aplicado"


async def test_ac4_etag_atual_aplica(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    await pipeline.executar(
        "t025_status",
        {"lote_id": LOTE, "status": "liberado"},
        ator=personas["helena"],
        motor=motor,
        origem="tela",
        if_match=await _etag_atual(motor),
    )
    assert await _status_do_lote(motor) == "liberado"


async def test_ac4_atualizacao_sem_if_match_e_recusada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """`If-Match` opcional e' `If-Match` ausente: o cliente que sobrescreve sem
    ler e' justamente o que omite o cabecalho."""
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "t025_status",
            {"lote_id": LOTE, "status": "liberado"},
            ator=personas["helena"],
            motor=motor,
            origem="tela",
        )
    assert e.value.codigo == "invalido"
    assert await _status_do_lote(motor) == "quarentena"


async def test_ac4_etag_muda_quando_a_entidade_muda(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Se o etag fosse constante, o teste de conflito acima passaria por acaso."""
    antes = await _etag_atual(motor)
    await pipeline.executar(
        "t025_status",
        {"lote_id": LOTE, "status": "liberado"},
        ator=personas["helena"],
        motor=motor,
        origem="tela",
        if_match=antes,
    )
    assert await _etag_atual(motor) != antes


async def test_ac4_alvo_inexistente_nao_distingue_de_fora_de_escopo(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """ADR-0014: a negativa e' constante, senao vira oraculo de enumeracao."""
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "t025_status",
            {"lote_id": "nao-existe", "status": "liberado"},
            ator=personas["helena"],
            motor=motor,
            origem="tela",
            if_match="qualquer",
        )
    assert e.value.codigo == "nao_encontrado"
    assert e.value.mensagem_publica == "Registro nao encontrado."


# ------------------------------------------------------------- AC-5 · auditoria
async def test_ac5_sucesso_grava_valor_anterior_e_novo(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-D01. Trilha que so' diz "mudou" nao reconstroi o que mudou — e
    reconstruir e' para o que ela existe."""
    antes = len(await _auditoria(motor, "t025_status"))
    await pipeline.executar(
        "t025_status",
        {"lote_id": LOTE, "status": "liberado"},
        ator=personas["helena"],
        motor=motor,
        origem="tela",
        if_match=await _etag_atual(motor),
    )
    linhas = await _auditoria(motor, "t025_status")
    assert len(linhas) == antes + 1
    ultima = linhas[-1]
    assert ultima["ator_id"] == personas["helena"].id
    assert ultima["valor_anterior"] == {"status": "quarentena"}
    assert ultima["valor_novo"] == {"status": "liberado"}
    assert ultima["entidade_id"] == LOTE
    assert ultima["origem"] == "tela"
    assert ultima["criado_em"] is not None


async def test_ac5_replay_nao_gera_segunda_auditoria(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Repetir uma chave nao e' uma segunda escrita. Registrar como se fosse
    inflaria a trilha com eventos que nunca aconteceram."""
    chave = _chave()
    corpo = {"lote_id": LOTE, "quantidade": 3}
    await pipeline.executar(
        "t025_saida",
        corpo,
        ator=personas["ivo"],
        motor=motor,
        origem="tela",
        idempotency_key=chave,
    )
    antes = len(await _auditoria(motor, "t025_saida"))
    await pipeline.executar(
        "t025_saida",
        corpo,
        ator=personas["ivo"],
        motor=motor,
        origem="tela",
        idempotency_key=chave,
    )
    assert len(await _auditoria(motor, "t025_saida")) == antes


# ------------------------------------------------- AC-6 · o relogio e' do servidor
async def test_ac6_timestamp_do_cliente_e_ignorado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-M04. O cliente manda 2020; o movimento nasce com a hora do servidor."""
    from datetime import UTC, datetime

    r = await pipeline.executar(
        "t025_saida",
        {"lote_id": LOTE, "quantidade": 3, "criado_em": "2020-01-01T00:00:00+00:00"},
        ator=personas["ivo"],
        motor=motor,
        origem="tela",
        idempotency_key=_chave(),
    )
    async with motor.connect() as c:
        gravado = (
            await c.execute(
                sa.select(m.movimento.c.criado_em).where(
                    m.movimento.c.id == r.dados["movimento_id"]
                )
            )
        ).scalar_one()
    assert gravado.year != 2020
    assert abs((datetime.now(UTC) - gravado).total_seconds()) < 60


async def test_ac6_o_campo_do_cliente_nao_chega_ao_comando(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-M04 na forma forte: nao e' que o comando escolha ignorar o campo — o
    campo nao chega. Um comando futuro que aceitasse `criado_em` no schema
    receberia `None` aqui, e nao ha como um autor de comando optar por confiar no
    relogio do cliente sem alterar o pipeline."""
    from datetime import UTC, datetime

    r = await pipeline.executar(
        "t025_eco",
        {"lote_id": LOTE, "criado_em": "2020-01-01T00:00:00+00:00"},
        ator=personas["ivo"],
        motor=motor,
        origem="tela",
    )
    assert r.dados["recebido_do_cliente"] is None
    assert datetime.fromisoformat(r.dados["do_servidor"]).year == datetime.now(UTC).year


async def test_ac6_relogio_do_cliente_nao_muda_a_impressao_da_chave(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O campo e' descartado ANTES do hash do corpo. Se nao fosse, dois envios da
    mesma operacao com relogios diferentes teriam impressoes diferentes e o
    replay viraria `conflito` — a idempotencia quebraria pelo campo que o
    servidor jurou ignorar."""
    chave = _chave()
    base = {"lote_id": LOTE, "quantidade": 3}
    um = await pipeline.executar(
        "t025_saida",
        {**base, "criado_em": "2020-01-01T00:00:00+00:00"},
        ator=personas["ivo"],
        motor=motor,
        origem="tela",
        idempotency_key=chave,
    )
    dois = await pipeline.executar(
        "t025_saida",
        {**base, "criado_em": "2031-05-05T05:05:05+00:00"},
        ator=personas["ivo"],
        motor=motor,
        origem="tela",
        idempotency_key=chave,
    )
    assert dois.repetido is True
    assert dois.dados == um.dados


# ------------------------------------------------- AC-7 · nenhum efeito parcial
async def test_ac7_falha_de_dominio_nao_deixa_efeito(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    antes = await _movimentos(motor)
    with pytest.raises(ErroDominio):
        await pipeline.executar(
            "t025_falha",
            {"lote_id": LOTE, "quantidade": 3},
            ator=personas["ivo"],
            motor=motor,
            origem="tela",
            idempotency_key=_chave(),
        )
    assert await _movimentos(motor) == antes, "o INSERT anterior a falha sobreviveu"


async def test_ac7_a_tentativa_recusada_fica_na_trilha(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Auditoria que so' registra sucesso descreve um sistema onde ninguem nunca
    tentou o que nao podia — que e' o que se quer investigar."""
    antes = len(await _auditoria(motor, "t025_falha.recusado"))
    with pytest.raises(ErroDominio):
        await pipeline.executar(
            "t025_falha",
            {"lote_id": LOTE, "quantidade": 3},
            ator=personas["ivo"],
            motor=motor,
            origem="tela",
            idempotency_key=_chave(),
        )
    linhas = await _auditoria(motor, "t025_falha.recusado")
    assert len(linhas) == antes + 1
    assert linhas[-1]["ator_id"] == personas["ivo"].id
    assert linhas[-1]["valor_novo"]["codigo"] == "invalido"


async def test_ac7_recusa_por_autorizacao_tambem_e_auditada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    antes = len(await _auditoria(motor, "t025_status.recusado"))
    with pytest.raises(ErroDominio):
        await pipeline.executar(
            "t025_status",
            {"lote_id": LOTE, "status": "liberado"},
            ator=personas["ivo"],
            motor=motor,
            origem="tela",
            if_match=await _etag_atual(motor),
        )
    linhas = await _auditoria(motor, "t025_status.recusado")
    assert len(linhas) == antes + 1
    assert linhas[-1]["valor_novo"]["codigo"] == "nao_autorizado"


async def test_ac7_chave_nao_e_gravada_quando_o_comando_falha(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Se a chave sobrevivesse ao rollback, a retentativa legitima do cliente
    receberia de volta uma resposta de uma escrita que nunca aconteceu."""
    chave = _chave()
    with pytest.raises(ErroDominio):
        await pipeline.executar(
            "t025_falha",
            {"lote_id": LOTE, "quantidade": 3},
            ator=personas["ivo"],
            motor=motor,
            origem="tela",
            idempotency_key=chave,
        )
    async with motor.connect() as c:
        achou = (
            await c.execute(
                sa.select(sa.func.count())
                .select_from(m.idempotencia)
                .where(m.idempotencia.c.chave == chave)
            )
        ).scalar_one()
    assert achou == 0


# ------------------------------------------------------------------- registro
async def test_comando_desconhecido_nao_distingue_de_proibido(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "nao_existe",
            {},
            ator=personas["marco"],
            motor=motor,
            origem="tela",
            idempotency_key=_chave(),
        )
    assert e.value.codigo == "nao_encontrado"
    assert e.value.mensagem_publica == "Registro nao encontrado."


def test_comando_sem_requires_e_recusado_no_registro() -> None:
    """ADR-0004: o tipo permite a tupla vazia; `registrar` e' o que a recusa.
    Sem isto, um comando novo sem `requires` seria brecha silenciosa."""
    with pytest.raises(ValueError, match="requires vazio"):
        pipeline.registrar(
            Comando(
                nome="t025_sem_requires",
                requires=(),
                schema=EntradaSaida,
                aplicar=_aplicar_saida,
            )
        )
