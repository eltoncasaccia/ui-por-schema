"""T-028 AC-2 a AC-8 — a saída de estoque, contra Postgres real.

Aqui o banco não é cenário, é o teste: `RN-M01` (saldo nunca negativo) e o AC-6
(controlado não muda saldo) dependem de a soma dos movimentos ser a fonte, e um
repositório falso provaria apenas que a soma em memória fecha.

**AC-6 é a base do CA-04**, e a armadilha está escrita na tarefa: se o saldo
mudar na submissão e "voltar" caso a autorização não venha, a dupla identificação
virou teatro — a mercadoria já saiu do estoque contábil com uma identificação só.

Pulam sem banco: `make db-local && make migrate`, e `make db-local` DE NOVO.
"""

import os
import secrets
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

import estoque.application.commands.indice  # noqa: F401  — registra os comandos
from estoque.application.commands import pipeline
from estoque.application.commands.saida import _etag_da_saida, _saldo
from estoque.application.commands.tipos import ContextoComando
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator

URL = os.environ.get(
    "DATABASE_URL_TESTE_APP_ASYNC",
    "postgresql+asyncpg://estoque_app:app@localhost:15432/estoque",
)
URL_SONDA = os.environ.get(
    "DATABASE_URL_TESTE_APP",
    "postgresql+psycopg://estoque_app:app@localhost:15432/estoque",
)

PROD = "t028-prod"  # comum
PROD_CTRL = "t028-ctrl"  # controlado
# Produto SÓ do lote perto do vencimento. A liberação do RT (RN-L05) é gravada na
# trilha, que é append-only e não se limpa entre testes: deixar `PERTO` no mesmo
# produto faria a autorização de um teste mudar a proposta do FEFO de todos os
# seguintes. Isolar é o único jeito de o livro-razão não virar estado global.
PROD_PERTO = "t028-prod-perto"
# E um SEGUNDO par, que nunca recebe autorização.
#
# O teste negativo de RN-L05 depende da AUSÊNCIA de um registro na trilha — e a
# trilha é append-only. Usar o mesmo lote nos dois casos faria o teste negativo
# passar uma vez na vida, contra banco novo, e falhar em toda execução seguinte.
# Um lote que nunca é liberado é o único jeito de a ausência continuar sendo
# ausência.
PROD_SEM = "t028-prod-sem"
CEDO = "t028-lote-cedo"  # vence antes — é o que o FEFO propõe
TARDE = "t028-lote-tarde"  # vence depois
PERTO = "t028-lote-perto"  # dentro dos 30 dias de RN-L05, LIBERADO pelo RT
SEM_LIBERACAO = "t028-lote-sem"  # dentro dos 30 dias, e nunca liberado
VENCIDO = "t028-lote-venc"
QUARENTENA = "t028-lote-quar"
CTRL = "t028-lote-ctrl"

VENDA: dict[str, Any] = {
    "motivo": "venda",
    "cliente_id": "cli-042",
    "nota_fiscal": "NF-99887",
}


@pytest.fixture(scope="module")
def motor() -> AsyncEngine:
    try:
        sonda = sa.create_engine(URL_SONDA, connect_args={"connect_timeout": 2})
        with sonda.connect():
            pass
    except Exception:
        pytest.skip("sem banco: rode `make db-local && make migrate && make db-local`")
    return create_async_engine(URL, future=True, poolclass=NullPool)


@pytest.fixture(autouse=True)
async def _semear(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    """Estoque conhecido antes de cada teste.

    Os movimentos de teste são apagados... e NÃO são: o papel da aplicação não
    tem DELETE em `movimento` (RN-M02, migração 0001). Em vez disso cada lote é
    recriado com id novo por execução? Também não — isso multiplicaria lixo.

    A saída é somar o que já existe: cada teste mede o saldo ANTES e afirma sobre
    a diferença. É mais chato de escrever e é o único jeito honesto de testar um
    livro-razão append-only.
    """
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
                "(:p,'7895','Amoxicilina 500mg','F','amox','comum','A',true,1250) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PROD},
        )
        await c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'7896','Ritalina','N','metilfenidato','controlado','A',true,3200) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PROD_CTRL},
        )
        await c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'7897','Dipirona 500mg','F','dipirona','comum','B',true,900) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PROD_PERTO},
        )
        await c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'7898','Ibuprofeno 400mg','F','ibuprofeno','comum','C',true,700) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PROD_SEM},
        )
        lotes = (
            (CEDO, PROD, 120, "liberado"),
            (TARDE, PROD, 400, "liberado"),
            (PERTO, PROD_PERTO, 20, "liberado"),
            (SEM_LIBERACAO, PROD_SEM, 15, "liberado"),
            (VENCIDO, PROD, -5, "liberado"),
            (QUARENTENA, PROD, 300, "quarentena"),
            (CTRL, PROD_CTRL, 300, "liberado"),
        )
        for lote_id, prod, dias, status in lotes:
            await c.execute(
                sa.text(
                    "INSERT INTO lote VALUES (:l,:p,:n,'cd-matriz',:f,:v,:s,null) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "l": lote_id,
                    "p": prod,
                    "n": lote_id[-6:].upper(),
                    "f": hoje - timedelta(days=200),
                    "v": hoje + timedelta(days=dias),
                    "s": status,
                },
            )
            # O UPDATE inclui `produto_id`: o INSERT acima é `ON CONFLICT DO
            # NOTHING`, então um lote criado por execução anterior mantém os
            # valores velhos. Semear sem reafirmar o estado deixa o teste
            # dependendo de qual versão do fixture rodou primeiro.
            await c.execute(
                sa.text("UPDATE lote SET produto_id=:p, status=:s, validade=:v WHERE id=:l"),
                {"l": lote_id, "p": prod, "s": status, "v": hoje + timedelta(days=dias)},
            )
            # Uma entrada NOVA por teste, com id próprio.
            #
            # Não dá para "resetar" o saldo: o papel da aplicação não tem DELETE
            # nem UPDATE em `movimento` (RN-M02), e é assim que tem de ser. O
            # jeito de um livro-razão append-only voltar a ter estoque é o mesmo
            # da vida real — outra entrada. Um `ON CONFLICT DO NOTHING` com id
            # fixo repunha uma vez só, e o teste que zera o lote deixava todos os
            # seguintes sem saldo, na ordem em que o pytest resolvesse rodá-los.
            await c.execute(
                sa.text(
                    "INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,"
                    "autor_id,status,criado_em) VALUES "
                    "(:i,:l,'cd-matriz','entrada',100000,'recebimento',:a,'efetivado',now())"
                ),
                {
                    "i": f"t028-ent-{secrets.token_hex(6)}",
                    "l": lote_id,
                    "a": personas["ivo"].id,
                },
            )
        for a in personas.values():
            await c.execute(
                sa.text(
                    "INSERT INTO usuario VALUES (:i,:n,:e,'x',:pp,true) ON CONFLICT DO NOTHING"
                ),
                {"i": a.id, "n": a.nome, "e": f"{a.id}@bertoni.test", "pp": a.papel},
            )


# ------------------------------------------------------------------ auxiliares
async def _ctx(motor: AsyncEngine, ator: Ator) -> Any:
    class _Ctx:
        pass

    return _Ctx()


async def saldo(motor: AsyncEngine, ator: Ator, lote_id: str) -> int:
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        return await _saldo(lote_id, ctx)


async def etag(motor: AsyncEngine, ator: Ator, lote_id: str) -> str:
    class _E:
        lote_id = ""

    alvo = _E()
    alvo.lote_id = lote_id
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        e = await _etag_da_saida(alvo, ctx)
    # `None` quando o lote está fora do escopo do ator; nesse caso a autorização
    # ou o `nao_encontrado` recusam antes de o etag importar.
    return e or "fora-de-escopo"


async def sair(
    motor: AsyncEngine, ator: Ator, lote_id: str, quantidade: int = 10, **extra: Any
) -> Any:
    corpo: dict[str, Any] = {"lote_id": lote_id, "quantidade": quantidade, **VENDA}
    corpo.update(extra)
    return await pipeline.executar(
        "movimento_saida",
        corpo,
        ator=ator,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await etag(motor, ator, lote_id),
    )


async def movimentos(motor: AsyncEngine, lote_id: str) -> list[dict[str, Any]]:
    async with motor.connect() as c:
        linhas = (
            (
                await c.execute(
                    sa.select(m.movimento)
                    .where(m.movimento.c.lote_id == lote_id, m.movimento.c.tipo == "saida")
                    .order_by(m.movimento.c.criado_em)
                )
            )
            .mappings()
            .all()
        )
    return [dict(x) for x in linhas]


# ------------------------------------------------------- AC-2 · FEFO ignorado
async def test_ac2_escolher_outro_lote_sem_justificativa_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-L03. `TARDE` vence depois de `CEDO`: não é a proposta do FEFO."""
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, TARDE)
    with pytest.raises(ErroDominio) as e:
        await sair(motor, ivo, TARDE)
    assert e.value.codigo == "invalido"
    assert "menor validade" in e.value.mensagem_publica
    assert await saldo(motor, ivo, TARDE) == antes


async def test_ac2_com_justificativa_passa(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O par positivo — sem ele, um comando que recusasse toda troca passaria."""
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, TARDE)
    r = await sair(
        motor, ivo, TARDE, justificativa_fefo="pedido exige validade longa, cliente hospitalar"
    )
    assert r.dados["status"] == "efetivado"
    assert await saldo(motor, ivo, TARDE) == antes - 10


async def test_ac2_justificativa_curta_nao_serve(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Uma justificativa de duas letras satisfaria a regra na letra e não no
    espírito: `RN-L03` quer o motivo registrado, não o campo preenchido."""
    with pytest.raises(ErroDominio) as e:
        await sair(motor, personas["ivo"], TARDE, justificativa_fefo="ok")
    assert e.value.codigo == "invalido"


async def test_ac2_o_lote_proposto_nao_exige_justificativa(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, CEDO)
    await sair(motor, ivo, CEDO)
    assert await saldo(motor, ivo, CEDO) == antes - 10


async def test_ac2_a_proposta_e_recalculada_no_servidor(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O cliente NÃO manda qual foi a proposta. Se mandasse, bastaria enviar
    `proposta = lote_escolhido` para a justificativa nunca ser exigida — e a
    regra existe exatamente para quem quer pular a fila."""
    with pytest.raises(ErroDominio):
        await sair(motor, personas["ivo"], TARDE, proposta=TARDE)


# ------------------------------------------------- AC-3 · lote que não pode sair
async def test_ac3_lote_vencido_nao_sai(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    """RN-L06: por nenhum motivo, exceto descarte."""
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, VENCIDO)
    with pytest.raises(ErroDominio) as e:
        await sair(motor, ivo, VENCIDO, justificativa_fefo="tentativa de saída de vencido")
    assert e.value.codigo == "conflito"
    assert "vencido" in e.value.mensagem_publica
    assert await saldo(motor, ivo, VENCIDO) == antes


async def test_ac3_lote_em_quarentena_nao_sai(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, QUARENTENA)
    with pytest.raises(ErroDominio) as e:
        await sair(motor, ivo, QUARENTENA, justificativa_fefo="tentativa em quarentena")
    assert e.value.codigo == "conflito"
    assert await saldo(motor, ivo, QUARENTENA) == antes


async def test_ac3_lote_bloqueado_nao_sai(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    ivo = personas["ivo"]
    async with motor.begin() as c:
        await c.execute(sa.text("UPDATE lote SET status='bloqueado' WHERE id=:l"), {"l": TARDE})
    try:
        antes = await saldo(motor, ivo, TARDE)
        with pytest.raises(ErroDominio) as e:
            await sair(motor, ivo, TARDE, justificativa_fefo="tentativa em bloqueado")
        assert e.value.codigo == "conflito"
        assert await saldo(motor, ivo, TARDE) == antes
    finally:
        async with motor.begin() as c:
            await c.execute(
                sa.text("UPDATE lote SET status='liberado' WHERE id=:l"), {"l": TARDE}
            )


# ------------------------------------- RN-L05 via trilha (achado A-14, com T-027)
async def test_lote_perto_do_vencimento_nao_sai_sem_liberacao_do_rt(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-L05: lote a ≤ 30 dias é bloqueado automaticamente para venda.

    O bloqueio é DERIVADO da data (ADR-0022) e não tem coluna — a autorização do
    RT vive na trilha de auditoria, gravada por T-027. É o achado A-14, e este
    teste é o que liga as duas pontas.
    """
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, SEM_LIBERACAO)
    with pytest.raises(ErroDominio) as e:
        await sair(motor, ivo, SEM_LIBERACAO)
    assert e.value.codigo == "conflito"
    assert "RN-L05" in e.value.mensagem_publica
    assert await saldo(motor, ivo, SEM_LIBERACAO) == antes


async def test_com_a_liberacao_do_rt_na_trilha_a_saida_passa(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O par positivo, e a prova de que a leitura da trilha funciona: a mesma
    saída recusada acima passa depois de o RT liberar por `lote_status`."""
    ivo, helena = personas["ivo"], personas["helena"]
    await pipeline.executar(
        "lote_status",
        {
            "lote_id": PERTO,
            "acao": "liberar_vencimento",
            "justificativa": "cliente ciente da validade curta, pedido urgente",
        },
        ator=helena,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await _etag_do_lote_para_status(motor, helena, PERTO),
    )
    antes = await saldo(motor, ivo, PERTO)
    r = await sair(motor, ivo, PERTO, justificativa_fefo="liberado pelo RT nesta data")
    assert r.dados["status"] == "efetivado"
    assert await saldo(motor, ivo, PERTO) == antes - 10


async def _etag_do_lote_para_status(motor: AsyncEngine, ator: Ator, lote_id: str) -> str:
    from estoque.application.commands.lote import _etag_do_lote

    class _E:
        lote_id = ""

    alvo = _E()
    alvo.lote_id = lote_id
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        e = await _etag_do_lote(alvo, ctx)
    assert e is not None
    return e


# ---------------------------------------------------------- AC-4 · saldo negativo
async def test_ac4_saida_maior_que_o_saldo_e_recusada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-M01. Pede um a mais do que existe — a fronteira exata."""
    ivo = personas["ivo"]
    atual = await saldo(motor, ivo, CEDO)
    with pytest.raises(ErroDominio) as e:
        await sair(motor, ivo, CEDO, quantidade=atual + 1)
    assert e.value.codigo == "conflito"
    assert "insuficiente" in e.value.mensagem_publica
    assert await saldo(motor, ivo, CEDO) == atual


async def test_ac4_saida_exatamente_do_saldo_passa(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """A outra metade da fronteira: zerar é permitido, negativar não. Sem este
    teste, um `>=` no lugar de `>` passaria despercebido."""
    ivo = personas["ivo"]
    atual = await saldo(motor, ivo, CEDO)
    await sair(motor, ivo, CEDO, quantidade=atual)
    assert await saldo(motor, ivo, CEDO) == 0


# -------------------------------------------------- AC-6 · controlado (base do CA-04)
async def test_ac6_saida_de_controlado_nao_altera_o_saldo(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-C01. **A armadilha da tarefa.** Se o saldo mudasse aqui e "voltasse"
    caso a autorização não viesse, a dupla identificação seria teatro."""
    cleide = personas["cleide"]  # conferente: tem `controlado.movimentar`
    antes = await saldo(motor, cleide, CTRL)
    r = await sair(motor, cleide, CTRL)
    assert r.dados["status"] == "aguardando_autorizacao"
    assert r.dados["controlado"] is True
    assert await saldo(motor, cleide, CTRL) == antes, "o saldo mudou antes da autorização"


async def test_ac6_o_movimento_pendente_existe_e_esta_sem_autorizador(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Não mudar o saldo não pode significar não gravar nada: o movimento tem de
    existir para T-030 encontrá-lo. E `autorizador_id` fica NULO — preenchê-lo
    com o próprio autor violaria o CHECK do banco (RN-A04)."""
    cleide = personas["cleide"]
    r = await sair(motor, cleide, CTRL)
    achado = next(
        x for x in await movimentos(motor, CTRL) if x["id"] == r.dados["movimento_id"]
    )
    assert achado["status"] == "aguardando_autorizacao"
    assert achado["autorizador_id"] is None
    assert achado["autor_id"] == cleide.id


async def test_ac6_saida_comum_efetiva_na_hora(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O par negativo do AC-6: se TODA saída nascesse pendente, o teste acima
    passaria sem o sistema distinguir controlado de comum."""
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, CEDO)
    r = await sair(motor, ivo, CEDO)
    assert r.dados["status"] == "efetivado"
    assert r.dados["controlado"] is False
    assert await saldo(motor, ivo, CEDO) == antes - 10


# ---------------------------------------------------------- AC-7 · imutabilidade
async def test_ac7_o_movimento_criado_nao_pode_ser_editado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-M02, e é o BANCO que recusa — não um `if` no servidor.

    A aplicação conecta como `estoque_app`, papel sem UPDATE nem DELETE em
    `movimento` (migração 0001). Nenhuma rota precisa lembrar de proibir, porque
    não existe privilégio para permitir.
    """
    r = await sair(motor, personas["ivo"], CEDO)
    mid = r.dados["movimento_id"]
    with pytest.raises(Exception, match="permission denied"):
        async with motor.begin() as c:
            await c.execute(
                sa.text("UPDATE movimento SET quantidade = 1 WHERE id = :i"), {"i": mid}
            )
    with pytest.raises(Exception, match="permission denied"):
        async with motor.begin() as c:
            await c.execute(sa.text("DELETE FROM movimento WHERE id = :i"), {"i": mid})


# --------------------------------------------------- AC-8 · cliente, nota, recall
async def test_ac8_cliente_e_nota_ficam_gravados(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-D03/CA-01: é o que responde "quem recebeu este lote?"."""
    r = await sair(motor, personas["ivo"], CEDO)
    achado = next(
        x for x in await movimentos(motor, CEDO) if x["id"] == r.dados["movimento_id"]
    )
    assert achado["cliente_id"] == "cli-042"
    assert achado["nota_fiscal"] == "NF-99887"
    assert achado["motivo"] == "venda"


async def test_ac8_o_movimento_e_recuperavel_por_lote(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """A consulta que `rastreabilidade` (T-021) vai fazer: do lote para os
    clientes. Aqui só se prova que o dado existe e é indexável por lote."""
    r = await sair(motor, personas["ivo"], CEDO)
    async with motor.connect() as c:
        clientes = [
            row[0]
            for row in await c.execute(
                sa.select(m.movimento.c.cliente_id).where(
                    m.movimento.c.lote_id == CEDO,
                    m.movimento.c.tipo == "saida",
                    m.movimento.c.status == "efetivado",
                )
            )
        ]
    assert "cli-042" in clientes
    assert r.dados["movimento_id"]


# ----------------------------------------------------------- RN-M04 e auditoria
async def test_criado_em_e_do_servidor(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    """RN-M04. O cliente manda 2019; o movimento nasce com a hora do servidor —
    o pipeline descarta o campo antes mesmo de validar."""
    r = await sair(motor, personas["ivo"], CEDO, criado_em="2019-01-01T00:00:00+00:00")
    achado = next(
        x for x in await movimentos(motor, CEDO) if x["id"] == r.dados["movimento_id"]
    )
    assert achado["criado_em"].year != 2019
    assert abs((datetime.now(UTC) - achado["criado_em"]).total_seconds()) < 60


async def test_a_trilha_guarda_o_saldo_antes_e_depois(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-D01. Movimento é append-only, então não há "valor anterior" dele — o
    que muda é o saldo do lote, e é ele que a trilha precisa reconstruir."""
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, CEDO)
    r = await sair(motor, ivo, CEDO)
    async with motor.connect() as c:
        linha = (
            (
                await c.execute(
                    sa.select(m.auditoria).where(
                        m.auditoria.c.acao == "movimento_saida",
                        m.auditoria.c.entidade_id == r.dados["movimento_id"],
                    )
                )
            )
            .mappings()
            .one()
        )
    assert linha["ator_id"] == ivo.id
    assert linha["valor_anterior"]["saldo"] == antes
    assert linha["valor_novo"]["saldo_apos"] == antes - 10
    assert linha["valor_novo"]["cliente_id"] == "cli-042"


# ------------------------------------------------------- autorização e escopo
@pytest.mark.parametrize("quem", ["marco", "helena", "rafael", "sandra"])
async def test_quem_nao_tem_movimento_criar_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator], quem: str
) -> None:
    """RN-A03, com chamada direta ao pipeline — o que uma requisição forjada faz.

    Marco é o Diretor e Helena é a RT: nenhum dos dois cria movimento. Papel não
    é nível, é conjunto.
    """
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, CEDO)
    with pytest.raises(ErroDominio) as e:
        await sair(motor, personas[quem], CEDO)
    assert e.value.codigo == "nao_autorizado"
    assert await saldo(motor, ivo, CEDO) == antes


async def test_lote_fora_do_escopo_nao_e_encontrado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A01 na escrita. Odair só alcança Uberlândia."""
    with pytest.raises(ErroDominio) as e:
        await sair(motor, personas["odair"], CEDO)
    assert e.value.codigo == "nao_encontrado"
    assert e.value.mensagem_publica == "Registro nao encontrado."


async def test_ator_inativo_e_recusado(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    with pytest.raises(ErroDominio) as e:
        await sair(motor, replace(personas["ivo"], ativo=False), CEDO)
    assert e.value.codigo == "nao_autorizado"


# ------------------------------------------------------------- idempotência
async def test_repetir_a_chave_nao_duplica_a_saida(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """T-025 AC-3 valendo aqui: repetir uma saída por causa de timeout de rede
    não pode tirar o dobro do estoque."""
    ivo = personas["ivo"]
    chave = secrets.token_hex(8)
    corpo = {"lote_id": CEDO, "quantidade": 7, **VENDA}
    antes = await saldo(motor, ivo, CEDO)
    e = await etag(motor, ivo, CEDO)
    um = await pipeline.executar(
        "movimento_saida",
        corpo,
        ator=ivo,
        motor=motor,
        origem="tela",
        idempotency_key=chave,
        if_match=e,
    )
    dois = await pipeline.executar(
        "movimento_saida",
        corpo,
        ator=ivo,
        motor=motor,
        origem="tela",
        idempotency_key=chave,
        if_match=e,
    )
    assert dois.repetido is True
    assert dois.dados == um.dados
    assert await saldo(motor, ivo, CEDO) == antes - 7


async def test_sem_idempotency_key_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, CEDO)
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "movimento_saida",
            {"lote_id": CEDO, "quantidade": 5, **VENDA},
            ator=ivo,
            motor=motor,
            origem="tela",
            if_match=await etag(motor, ivo, CEDO),
        )
    assert e.value.codigo == "invalido"
    assert await saldo(motor, ivo, CEDO) == antes


async def test_etag_velho_devolve_conflito_sem_aplicar(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O etag cobre o SALDO, não só o status: se outra pessoa deu saída entre a
    leitura da tela e o envio, a quantidade que o operador viu já não existe."""
    ivo = personas["ivo"]
    velho = await etag(motor, ivo, CEDO)
    await sair(motor, ivo, CEDO, quantidade=3)
    depois = await saldo(motor, ivo, CEDO)
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "movimento_saida",
            {"lote_id": CEDO, "quantidade": 5, **VENDA},
            ator=ivo,
            motor=motor,
            origem="tela",
            idempotency_key=secrets.token_hex(8),
            if_match=velho,
        )
    assert e.value.codigo == "conflito"
    assert await saldo(motor, ivo, CEDO) == depois
