"""T-029 — o descarte. AC-6, AC-7 e AC-8, contra Postgres real.

Duas afirmações que só o banco sustenta: o lote vai a `descartado` de verdade, e
o `CHECK (autorizador_id <> autor_id)` da migração 0001 é a terceira camada da
dupla identificação — a que não depende de nenhum caminho de código ter lembrado.

**O par negativo é o teste.** Que Ivo e Helena consigam descartar um lote vencido
prova pouco. Que Marco (Diretor, com a permissão) não consiga, que dois gerentes
juntos não consigam, e que um lote liberado e válido não vire descarte, é o que
prova a §4.1.

Pulam sem banco: `make db-local && make db-teste`.

Ver `test_estorno_comandos.py` para AC-1 a AC-5 e para a ausência de exclusão.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import banco
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

import estoque.application.commands.indice  # noqa: F401  — registra os comandos
from estoque.application.commands import pipeline
from estoque.application.commands.descarte import _etag_do_lote
from estoque.application.commands.saida import _saldo
from estoque.application.commands.tipos import ContextoComando
from estoque.data import modelos as m
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator

URL = banco.URL_APP_ASYNC
URL_SONDA = banco.URL_APP

PROD = "t029d-prod"
VENCIDO = "t029d-lote-venc"  # liberado no banco, VENCIDO de fato (ADR-0022)
BLOQUEADO = "t029d-lote-bloq"  # decisão humana registrada
LIBERADO = "t029d-lote-ok"  # liberado E válido — o caso do AC-6
SEM_SALDO = "t029d-lote-zero"  # vencido, e nunca teve entrada

DESCARTE: dict[str, Any] = {
    "motivo": "vencimento",
    "justificativa": "lote vencido na conferência do mês, destruição programada",
}


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
    """Cada teste recomeça com os quatro lotes no estado declarado.

    O `UPDATE` de status existe porque o descarte é TERMINAL: sem ele, o segundo
    teste encontraria o lote em `descartado` e passaria (ou falharia) pelo motivo
    errado, na ordem em que o pytest resolvesse rodá-los.
    """
    hoje = datetime.now(UTC).date()
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
                "(:p,'7897010','Cefalexina 500mg','F','cefalexina','comum','B',true,1500) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PROD},
        )
        lotes = (
            (VENCIDO, -30, "liberado", True),
            (BLOQUEADO, 300, "bloqueado", True),
            (LIBERADO, 300, "liberado", True),
            (SEM_SALDO, -30, "liberado", False),
        )
        for lote_id, dias, status, com_saldo in lotes:
            await c.execute(
                sa.text(
                    "INSERT INTO lote VALUES (:l,:p,:n,'cd-matriz',:f,:v,:s,null) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "l": lote_id,
                    "p": PROD,
                    "n": lote_id[-6:].upper(),
                    "f": hoje - timedelta(days=400),
                    "v": hoje + timedelta(days=dias),
                    "s": status,
                },
            )
            await c.execute(
                sa.text("UPDATE lote SET status=:s, validade=:v WHERE id=:l"),
                {"l": lote_id, "s": status, "v": hoje + timedelta(days=dias)},
            )
            if com_saldo:
                # Entrada NOVA por teste: o descarte leva o saldo a zero, e um id
                # fixo com `ON CONFLICT DO NOTHING` reporia uma vez só.
                await c.execute(
                    sa.text(
                        "INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,"
                        "autor_id,status,criado_em) VALUES "
                        "(:i,:l,'cd-matriz','entrada',500,'recebimento',:a,'efetivado',now())"
                    ),
                    {
                        "i": f"t029d-ent-{secrets.token_hex(6)}",
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
class _Alvo:
    def __init__(self, lote_id: str) -> None:
        self.lote_id = lote_id


async def saldo(motor: AsyncEngine, ator: Ator, lote_id: str) -> int:
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        return await _saldo(lote_id, ctx)


async def etag(motor: AsyncEngine, ator: Ator, lote_id: str) -> str:
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        return await _etag_do_lote(_Alvo(lote_id), ctx) or "fora-de-escopo"


async def descartar(
    motor: AsyncEngine, ator: Ator, lote_id: str, segundo: str, **extra: Any
) -> Any:
    corpo: dict[str, Any] = {
        "lote_id": lote_id,
        "segunda_identificacao_id": segundo,
        **DESCARTE,
    }
    corpo.update(extra)
    return await pipeline.executar(
        "movimento_descarte",
        corpo,
        ator=ator,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await etag(motor, ator, lote_id),
    )


async def status_do_lote(motor: AsyncEngine, lote_id: str) -> str:
    async with motor.connect() as c:
        return str(
            (
                await c.execute(sa.select(m.lote.c.status).where(m.lote.c.id == lote_id))
            ).scalar_one()
        )


async def movimento(motor: AsyncEngine, movimento_id: str) -> dict[str, Any]:
    async with motor.connect() as c:
        r = (
            (await c.execute(sa.select(m.movimento).where(m.movimento.c.id == movimento_id)))
            .mappings()
            .first()
        )
    assert r is not None
    return dict(r)


# ------------------------------------------- o caminho que funciona (o par +)
async def test_gerente_com_rt_descarta_lote_vencido(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-L06: vencido não sai por nenhum outro caminho. §4.1: Gerente + RT."""
    ivo, helena = personas["ivo"], personas["helena"]
    antes = await saldo(motor, ivo, VENCIDO)
    assert antes > 0

    r = await descartar(motor, ivo, VENCIDO, helena.id)

    mov = await movimento(motor, str(r.dados["movimento_id"]))
    assert mov["tipo"] == "descarte"
    assert mov["quantidade"] == antes  # o lote inteiro, lido no servidor
    assert mov["autor_id"] == ivo.id
    assert mov["autorizador_id"] == helena.id  # a segunda identidade
    assert mov["status"] == "efetivado"
    assert await saldo(motor, ivo, VENCIDO) == 0
    assert await status_do_lote(motor, VENCIDO) == "descartado"


async def test_rt_com_gerente_tambem_descarta(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """A §4.1 diz "Gerente + RT" e não diz quem assina primeiro. O inverso vale,
    e testá-lo impede que a regra vire "só o gerente registra"."""
    helena, ivo = personas["helena"], personas["ivo"]
    r = await descartar(motor, helena, BLOQUEADO, ivo.id, motivo="avaria")
    mov = await movimento(motor, str(r.dados["movimento_id"]))
    assert mov["autor_id"] == helena.id
    assert mov["autorizador_id"] == ivo.id
    assert await status_do_lote(motor, BLOQUEADO) == "descartado"


async def test_a_trilha_registra_as_duas_identidades_com_papel(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-D01. Quem audita depois precisa ver que a §4.1 foi cumprida, e a
    trilha é onde isso fica — não há coluna de papel no movimento."""
    ivo, helena = personas["ivo"], personas["helena"]
    await descartar(motor, ivo, VENCIDO, helena.id)

    async with motor.connect() as c:
        aud = (
            (
                await c.execute(
                    sa.select(m.auditoria)
                    .where(
                        m.auditoria.c.acao == "movimento_descarte",
                        m.auditoria.c.entidade_id == VENCIDO,
                    )
                    .order_by(m.auditoria.c.id.desc())
                )
            )
            .mappings()
            .first()
        )
    assert aud is not None
    assert aud["valor_anterior"]["status_efetivo"] == "vencido"
    assert aud["valor_novo"]["status"] == "descartado"
    assert aud["valor_novo"]["autor_papel"] == "gerente"
    assert aud["valor_novo"]["segunda_identificacao_papel"] == "rt"
    assert aud["valor_novo"]["saldo_apos"] == 0


# ------------------------------------ AC-6 · descarte não é atalho de saída
async def test_ac6_lote_liberado_e_valido_nao_e_descartado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-L06 pelo avesso. Desviar mercadoria boa para "descarte" seria furto
    com formulário: a saída dela tem cliente e nota fiscal."""
    ivo, helena = personas["ivo"], personas["helena"]
    antes = await saldo(motor, ivo, LIBERADO)

    with pytest.raises(ErroDominio) as e:
        await descartar(motor, ivo, LIBERADO, helena.id)

    assert e.value.codigo == "conflito"
    assert "vencido ou bloqueado" in e.value.mensagem_publica
    assert await saldo(motor, ivo, LIBERADO) == antes
    assert await status_do_lote(motor, LIBERADO) == "liberado"


async def test_ac6_lote_em_quarentena_tambem_nao_e_descartado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """§4.1 só tem descarte saindo de Vencido e de Bloqueado. Quarentena espera
    decisão do RT (T-027), e o atalho tornaria a quarentena decorativa."""
    ivo, helena = personas["ivo"], personas["helena"]
    async with motor.begin() as c:
        await c.execute(
            sa.text("UPDATE lote SET status='quarentena' WHERE id=:l"), {"l": LIBERADO}
        )
    with pytest.raises(ErroDominio) as e:
        await descartar(motor, ivo, LIBERADO, helena.id)
    assert e.value.codigo == "conflito"
    assert await status_do_lote(motor, LIBERADO) == "quarentena"


async def test_lote_vencido_sem_saldo_nao_gera_movimento(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """`quantidade > 0` é CHECK da migração 0001. Recusar com mensagem é melhor
    do que deixar o banco recusar com erro de restrição."""
    with pytest.raises(ErroDominio) as e:
        await descartar(motor, personas["ivo"], SEM_SALDO, personas["helena"].id)
    assert e.value.codigo == "conflito"
    assert "saldo" in e.value.mensagem_publica


async def test_descarte_repetido_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """`descartado` é terminal e vence tudo em `status_efetivo` (ADR-0022)."""
    ivo, helena = personas["ivo"], personas["helena"]
    await descartar(motor, ivo, VENCIDO, helena.id)
    with pytest.raises(ErroDominio) as e:
        await descartar(motor, ivo, VENCIDO, helena.id)
    assert e.value.codigo == "conflito"


# ------------------------------------------- AC-7 · as duas identificações
async def test_ac7_sem_segunda_identificacao_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O campo é obrigatório no schema: um descarte com uma assinatura só não
    chega a ser avaliado."""
    ivo = personas["ivo"]
    antes = await saldo(motor, ivo, VENCIDO)
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "movimento_descarte",
            {"lote_id": VENCIDO, **DESCARTE},
            ator=ivo,
            motor=motor,
            origem="tela",
            idempotency_key=secrets.token_hex(8),
            if_match=await etag(motor, ivo, VENCIDO),
        )
    assert e.value.codigo == "invalido"
    assert await saldo(motor, ivo, VENCIDO) == antes
    assert await status_do_lote(motor, VENCIDO) == "liberado"


async def test_ac7_a_mesma_pessoa_duas_vezes_nao_e_dupla_identificacao(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """A camada do servidor, com a identidade real. O `CHECK` da migração 0001
    recusaria de novo — são duas camadas, e nenhuma confia na outra."""
    ivo = personas["ivo"]
    with pytest.raises(ErroDominio) as e:
        await descartar(motor, ivo, VENCIDO, ivo.id)
    assert e.value.codigo == "invalido"
    assert "duas pessoas" in e.value.mensagem_publica
    assert await status_do_lote(motor, VENCIDO) == "liberado"


async def test_ac7_dois_gerentes_nao_descartam(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O teste que separa "duas pessoas" de "Gerente + RT". Ivo e Odair são duas
    pessoas distintas, as duas com `movimento.descartar`, e a §4.1 continua não
    sendo satisfeita: o RT está na linha porque a decisão técnica de destruir
    medicamento é dele."""
    ivo, odair = personas["ivo"], personas["odair"]
    with pytest.raises(ErroDominio) as e:
        await descartar(motor, ivo, VENCIDO, odair.id)
    assert e.value.codigo == "invalido"
    assert "mesmo papel" in e.value.mensagem_publica
    assert await status_do_lote(motor, VENCIDO) == "liberado"


async def test_ac7_a_segunda_identidade_precisa_poder_assinar(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Cleide (conferente) e Rafael (comprador) não estão na §4.1. Digitar o id
    de quem estava por perto não é dupla identificação."""
    ivo = personas["ivo"]
    for nome in ("cleide", "rafael", "sandra"):
        with pytest.raises(ErroDominio) as e:
            await descartar(motor, ivo, VENCIDO, personas[nome].id)
        assert e.value.codigo == "invalido", nome
    assert await status_do_lote(motor, VENCIDO) == "liberado"


async def test_ac7_segunda_identidade_inexistente_ou_inativa_e_recusada(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A06: desativado não assina. Inexistente e desativado devolvem a mesma
    coisa — quem preenche o campo não descobre quem existe."""
    ivo = personas["ivo"]
    with pytest.raises(ErroDominio) as inexistente:
        await descartar(motor, ivo, VENCIDO, "u-nao-existe")

    async with motor.begin() as c:
        await c.execute(
            sa.text(
                "INSERT INTO usuario VALUES "
                "('t029d-rt-inativo','RT Inativo','rt.inativo@bertoni.test','x','rt',false) "
                "ON CONFLICT (id) DO UPDATE SET ativo = false"
            )
        )
    with pytest.raises(ErroDominio) as inativo:
        await descartar(motor, ivo, VENCIDO, "t029d-rt-inativo")

    assert inexistente.value.codigo == inativo.value.codigo == "invalido"
    assert inexistente.value.mensagem_publica == inativo.value.mensagem_publica


# ---------------------------------------- nem o Diretor: papel não é nível
async def test_o_diretor_nao_descarta(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    """A matriz do §6 dá `movimento.descartar` ao Diretor; a §4.1 não o inclui na
    transição. Vale a §4.1 — e é a mesma tensão que `commands/lote.py` resolve do
    mesmo jeito: a permissão deixa entrar, a tabela de estados recusa."""
    marco, helena = personas["marco"], personas["helena"]
    assert "movimento.descartar" in marco.permissoes

    with pytest.raises(ErroDominio) as e:
        await descartar(motor, marco, VENCIDO, helena.id)
    assert e.value.codigo == "nao_autorizado"
    assert await status_do_lote(motor, VENCIDO) == "liberado"


async def test_quem_nao_tem_a_permissao_e_recusado_antes(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """A recusa de permissão vem ANTES da validação do corpo: erro de schema
    devolvido a quem não pode executar o comando descreveria o formulário dele."""
    for nome in ("cleide", "rafael", "sandra"):
        with pytest.raises(ErroDominio) as e:
            await descartar(motor, personas[nome], VENCIDO, personas["helena"].id)
        assert e.value.codigo == "nao_autorizado", nome


async def test_descarte_fora_do_escopo_e_indistinguivel_de_inexistente(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A01 e ADR-0014. Odair é gerente, tem a permissão, e só alcança
    Uberlândia."""
    odair, helena = personas["odair"], personas["helena"]
    with pytest.raises(ErroDominio) as fora:
        await descartar(motor, odair, VENCIDO, helena.id)
    with pytest.raises(ErroDominio) as inexistente:
        await descartar(motor, odair, "t029d-nao-existe", helena.id)
    assert fora.value.codigo == inexistente.value.codigo == "nao_encontrado"
    assert fora.value.mensagem_publica == inexistente.value.mensagem_publica


# ---------------------------------------------------- motivo e justificativa
async def test_motivo_fora_da_lista_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-M05. `furto` é motivo de SAÍDA, e não de descarte."""
    with pytest.raises(ErroDominio) as e:
        await descartar(motor, personas["ivo"], VENCIDO, personas["helena"].id, motivo="furto")
    assert e.value.codigo == "invalido"


async def test_justificativa_curta_nao_serve(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    with pytest.raises(ErroDominio) as e:
        await descartar(
            motor, personas["ivo"], VENCIDO, personas["helena"].id, justificativa="ok"
        )
    assert e.value.codigo == "invalido"
    assert await status_do_lote(motor, VENCIDO) == "liberado"


async def test_if_match_velho_recusa_o_descarte(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Concorrência otimista: se alguém deu saída entre a leitura da tela e o
    envio, o saldo mudou e o descarte que chega descreve outro lote."""
    ivo, helena = personas["ivo"], personas["helena"]
    velho = await etag(motor, ivo, VENCIDO)
    async with motor.begin() as c:
        await c.execute(
            sa.text(
                "INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,"
                "autor_id,status,criado_em) VALUES "
                "(:i,:l,'cd-matriz','entrada',7,'recebimento',:a,'efetivado',now())"
            ),
            {"i": f"t029d-ent-{secrets.token_hex(6)}", "l": VENCIDO, "a": ivo.id},
        )
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "movimento_descarte",
            {"lote_id": VENCIDO, "segunda_identificacao_id": helena.id, **DESCARTE},
            ator=ivo,
            motor=motor,
            origem="tela",
            idempotency_key=secrets.token_hex(8),
            if_match=velho,
        )
    assert e.value.codigo == "conflito"
    assert await status_do_lote(motor, VENCIDO) == "liberado"
