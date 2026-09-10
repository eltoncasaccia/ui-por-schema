"""T-029 — o estorno, e a ausência de exclusão. AC-1 a AC-5 e AC-8.

Contra Postgres real, porque é lá que `RN-M02` existe: o papel da aplicação não
tem `UPDATE` nem `DELETE` em `movimento`, e um repositório falso provaria apenas
que o código de teste não chamou nenhum dos dois.

**AC-1 é sobre as ROTAS registradas, não sobre a interface** (a armadilha está
escrita na tarefa). Ausência de botão não é ausência de endpoint: a varredura
sai do `openapi()` do app real, para que uma rota nova de exclusão reprove por
padrão em vez de passar por ninguém ter olhado.

Pulam sem banco: `make db-local && make migrate`, e `make db-local` DE NOVO.
"""

import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

import estoque.application.commands.indice  # noqa: F401  — registra os comandos
from estoque.application.commands import pipeline
from estoque.application.commands.estorno import _etag_do_original
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
URL_DONO = os.environ.get(
    "DATABASE_URL_TESTE",
    "postgresql+psycopg://estoque:troque-isto@localhost:15432/estoque",
)

# Um produto por lote, como na T-028: o FEFO propõe entre os lotes do MESMO
# produto, e lotes irmãos fariam cada saída deste arquivo exigir justificativa
# de `RN-L03` — ruído que não é o que estes testes medem.
PROD = "t029-prod"
PROD_CTRL = "t029-ctrl"
LOTE = "t029-lote"
LOTE_CTRL = "t029-lote-ctrl"

VENDA: dict[str, Any] = {
    "motivo": "venda",
    "cliente_id": "cli-029",
    "nota_fiscal": "NF-029",
}
CORRECAO: dict[str, Any] = {
    "motivo": "erro_de_separacao",
    "complemento": "separou o lote errado na conferência da manhã",
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


@pytest.fixture(scope="module")
def dono() -> sa.Engine:
    """Papel DONO — só para criar sessão de teste, que `estoque_app` não pode
    (achado A-27). A aplicação sob teste continua conectando como `estoque_app`."""
    try:
        eng = sa.create_engine(URL_DONO, future=True, connect_args={"connect_timeout": 2})
        with eng.connect():
            pass
    except Exception:
        pytest.skip("sem banco: rode `make db-local && make migrate && make db-local`")
    return eng


@pytest.fixture(autouse=True)
async def _semear(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    """Estoque conhecido antes de cada teste.

    Não dá para "resetar" o saldo: o papel da aplicação não tem `DELETE` nem
    `UPDATE` em `movimento` (RN-M02), e é assim que tem de ser. Cada teste mede
    o saldo ANTES e afirma sobre a diferença — é o único jeito honesto de testar
    um livro-razão append-only.
    """
    hoje = datetime.now(UTC).date()
    async with motor.begin() as c:
        await c.execute(
            sa.text(
                "INSERT INTO unidade VALUES ('cd-matriz','Matriz','seco',true) "
                "ON CONFLICT DO NOTHING"
            )
        )
        for pid, ean, nome, classe in (
            (PROD, "7897001", "Amoxicilina 250mg", "comum"),
            (PROD_CTRL, "7897002", "Clonazepam 2mg", "controlado"),
        ):
            await c.execute(
                sa.text(
                    "INSERT INTO produto VALUES (:p,:e,:n,'F','pa',:c,'A',true,1100) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"p": pid, "e": ean, "n": nome, "c": classe},
            )
        for lote_id, prod in ((LOTE, PROD), (LOTE_CTRL, PROD_CTRL)):
            await c.execute(
                sa.text(
                    "INSERT INTO lote VALUES (:l,:p,:n,'cd-matriz',:f,:v,'liberado',null) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "l": lote_id,
                    "p": prod,
                    "n": lote_id[-6:].upper(),
                    "f": hoje - timedelta(days=100),
                    "v": hoje + timedelta(days=300),
                },
            )
            await c.execute(
                sa.text(
                    "UPDATE lote SET produto_id=:p, status='liberado', validade=:v WHERE id=:l"
                ),
                {"l": lote_id, "p": prod, "v": hoje + timedelta(days=300)},
            )
            # Uma entrada NOVA por teste, com id próprio: repor com id fixo
            # funcionaria uma vez só, e o teste que zera o lote deixaria os
            # seguintes sem saldo, na ordem em que o pytest resolvesse rodá-los.
            await c.execute(
                sa.text(
                    "INSERT INTO movimento (id,lote_id,unidade_id,tipo,quantidade,motivo,"
                    "autor_id,status,criado_em) VALUES "
                    "(:i,:l,'cd-matriz','entrada',10000,'recebimento',:a,'efetivado',now())"
                ),
                {
                    "i": f"t029-ent-{secrets.token_hex(6)}",
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
    """O que `_etag_do_original` e `_etag_da_saida` esperam: um objeto com o id."""

    def __init__(self, **campos: str) -> None:
        for nome, valor in campos.items():
            setattr(self, nome, valor)


async def saldo(motor: AsyncEngine, ator: Ator, lote_id: str) -> int:
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        return await _saldo(lote_id, ctx)


async def etag_saida(motor: AsyncEngine, ator: Ator, lote_id: str) -> str:
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        return await _etag_da_saida(_Alvo(lote_id=lote_id), ctx) or "fora-de-escopo"


async def etag_estorno(motor: AsyncEngine, ator: Ator, movimento_id: str) -> str:
    async with motor.connect() as c:
        ctx = ContextoComando(ator=ator, conn=c, agora=datetime.now(UTC), origem="tela")
        return (
            await _etag_do_original(_Alvo(movimento_id=movimento_id), ctx) or "fora-de-escopo"
        )


async def sair(motor: AsyncEngine, ator: Ator, lote_id: str, quantidade: int = 10) -> Any:
    return await pipeline.executar(
        "movimento_saida",
        {"lote_id": lote_id, "quantidade": quantidade, **VENDA},
        ator=ator,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await etag_saida(motor, ator, lote_id),
    )


async def estornar(motor: AsyncEngine, ator: Ator, movimento_id: str, **extra: Any) -> Any:
    corpo: dict[str, Any] = {"movimento_id": movimento_id, **CORRECAO}
    corpo.update(extra)
    return await pipeline.executar(
        "movimento_estorno",
        corpo,
        ator=ator,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await etag_estorno(motor, ator, movimento_id),
    )


async def linha(motor: AsyncEngine, movimento_id: str) -> dict[str, Any]:
    async with motor.connect() as c:
        r = (
            (await c.execute(sa.select(m.movimento).where(m.movimento.c.id == movimento_id)))
            .mappings()
            .first()
        )
    assert r is not None
    return dict(r)


async def saida_efetivada(motor: AsyncEngine, ator: Ator, quantidade: int = 10) -> str:
    r = await sair(motor, ator, LOTE, quantidade)
    return str(r.dados["movimento_id"])


# ---------------------------------------------- AC-3 · o original não é tocado
async def test_ac3_estorno_cria_movimento_novo(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    ivo = personas["ivo"]
    original = await saida_efetivada(motor, ivo)
    r = await estornar(motor, ivo, original)

    novo = await linha(motor, str(r.dados["movimento_id"]))
    assert novo["id"] != original
    assert novo["tipo"] == "estorno"
    assert novo["estorna_movimento_id"] == original
    assert novo["quantidade"] == 10  # a do original, não a que o cliente mandar
    assert novo["status"] == "efetivado"


async def test_ac3_o_original_fica_byte_a_byte_inalterado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """`RN-M02` não é uma checagem deste comando: é a ausência de caminho que o
    edite. A comparação é da linha INTEIRA — um campo novo na tabela entra na
    asserção sozinho, que é o ponto de comparar tudo em vez de campo a campo."""
    ivo = personas["ivo"]
    original = await saida_efetivada(motor, ivo)
    antes = await linha(motor, original)

    await estornar(motor, ivo, original)

    assert await linha(motor, original) == antes


# ------------------------------------------------------------- AC-4 · o saldo
async def test_ac4_saldo_apos_estorno_e_a_soma_dos_dois_movimentos(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """`RN-M06`: não existe campo de saldo editável. O estorno devolve o saldo
    somando um movimento, e não corrigindo um número."""
    ivo = personas["ivo"]
    inicial = await saldo(motor, ivo, LOTE)

    original = await saida_efetivada(motor, ivo, 40)
    assert await saldo(motor, ivo, LOTE) == inicial - 40

    await estornar(motor, ivo, original)
    assert await saldo(motor, ivo, LOTE) == inicial


async def test_ac4_a_trilha_registra_o_saldo_antes_e_depois(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-D01: a trilha tem de reconstruir o efeito, e o efeito de um estorno é
    no saldo do lote — o movimento original continua onde estava."""
    ivo = personas["ivo"]
    original = await saida_efetivada(motor, ivo, 25)
    antes = await saldo(motor, ivo, LOTE)

    r = await estornar(motor, ivo, original)

    async with motor.connect() as c:
        aud = (
            (
                await c.execute(
                    sa.select(m.auditoria)
                    .where(m.auditoria.c.entidade_id == r.dados["movimento_id"])
                    .order_by(m.auditoria.c.id.desc())
                )
            )
            .mappings()
            .first()
        )
    assert aud is not None
    assert aud["acao"] == "movimento_estorno"
    assert aud["valor_anterior"]["saldo"] == antes
    assert aud["valor_novo"]["saldo_apos"] == antes + 25
    assert aud["valor_novo"]["estorna_movimento_id"] == original


# ------------------------------------------- AC-5 · motivo de lista fechada
async def test_ac5_motivo_fora_da_lista_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-M05. `devolucao` é motivo plausível, existe no documento 02 §3 como
    TIPO de movimento, e não está na lista fechada do estorno."""
    ivo = personas["ivo"]
    original = await saida_efetivada(motor, ivo)
    antes = await saldo(motor, ivo, LOTE)

    with pytest.raises(ErroDominio) as e:
        await estornar(motor, ivo, original, motivo="devolucao")
    assert e.value.codigo == "invalido"
    assert await saldo(motor, ivo, LOTE) == antes


async def test_ac5_os_dois_motivos_da_lista_sao_aceitos(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """O par positivo: sem ele, um comando que recusasse todo motivo passaria."""
    ivo = personas["ivo"]
    for motivo in ("erro_de_separacao", "estorno"):
        original = await saida_efetivada(motor, ivo)
        r = await estornar(motor, ivo, original, motivo=motivo)
        assert (await linha(motor, str(r.dados["movimento_id"])))["motivo"] == motivo


async def test_ac5_complemento_curto_nao_serve(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Texto livre é complemento do enum, nunca substituto (RN-M05) — e um
    complemento de duas letras satisfaz a regra na letra e não no espírito."""
    ivo = personas["ivo"]
    original = await saida_efetivada(motor, ivo)
    with pytest.raises(ErroDominio) as e:
        await estornar(motor, ivo, original, complemento="ok")
    assert e.value.codigo == "invalido"


async def test_ac5_complemento_vazio_e_recusado_pelo_schema(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    ivo = personas["ivo"]
    original = await saida_efetivada(motor, ivo)
    with pytest.raises(ErroDominio) as e:
        await estornar(motor, ivo, original, complemento="")
    assert e.value.codigo == "invalido"


# ------------------------------------------------- o que NÃO se estorna
async def test_entrada_nao_se_estorna(motor: AsyncEngine, personas: dict[str, Ator]) -> None:
    """Achado A-38. O sinal do estorno é fixo e positivo na `saldo_lote`
    (migração 0001): estornar uma entrada SOMARIA de novo o que se queria
    desfazer. O caminho recusa em vez de gravar um saldo errado."""
    ivo = personas["ivo"]
    async with motor.connect() as c:
        entrada = (
            (
                await c.execute(
                    sa.select(m.movimento.c.id).where(
                        m.movimento.c.lote_id == LOTE, m.movimento.c.tipo == "entrada"
                    )
                )
            )
            .scalars()
            .first()
        )
    assert entrada is not None
    antes = await saldo(motor, ivo, LOTE)

    with pytest.raises(ErroDominio) as e:
        await estornar(motor, ivo, str(entrada))
    assert e.value.codigo == "conflito"
    assert await saldo(motor, ivo, LOTE) == antes


async def test_estorno_de_estorno_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    ivo = personas["ivo"]
    original = await saida_efetivada(motor, ivo)
    r = await estornar(motor, ivo, original)
    antes = await saldo(motor, ivo, LOTE)

    with pytest.raises(ErroDominio) as e:
        await estornar(motor, ivo, str(r.dados["movimento_id"]))
    assert e.value.codigo == "conflito"
    assert await saldo(motor, ivo, LOTE) == antes


async def test_o_mesmo_movimento_nao_se_estorna_duas_vezes(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Sem esta recusa, dois cliques devolveriam o dobro do saldo — e o
    livro-razão fecharia com mercadoria que nunca voltou para a prateleira."""
    ivo = personas["ivo"]
    original = await saida_efetivada(motor, ivo)
    await estornar(motor, ivo, original)
    antes = await saldo(motor, ivo, LOTE)

    with pytest.raises(ErroDominio) as e:
        await estornar(motor, ivo, original)
    assert e.value.codigo == "conflito"
    assert await saldo(motor, ivo, LOTE) == antes


async def test_controlado_pendente_nao_se_estorna(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-C01: a saída de controlado nasce `aguardando_autorizacao` e o saldo não
    se mexe. Estorná-la devolveria mercadoria que nunca saiu — o caminho dela é a
    recusa do RT (T-030)."""
    cleide = personas["cleide"]
    r = await pipeline.executar(
        "movimento_saida",
        {"lote_id": LOTE_CTRL, "quantidade": 5, **VENDA},
        ator=cleide,
        motor=motor,
        origem="tela",
        idempotency_key=secrets.token_hex(8),
        if_match=await etag_saida(motor, cleide, LOTE_CTRL),
    )
    assert r.dados["status"] == "aguardando_autorizacao"

    with pytest.raises(ErroDominio) as e:
        await estornar(motor, personas["ivo"], str(r.dados["movimento_id"]))
    assert e.value.codigo == "conflito"


# ------------------------------------------------------ escopo e permissão
async def test_estorno_fora_do_escopo_e_indistinguivel_de_inexistente(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-A01 e ADR-0014. Odair só alcança Uberlândia; o movimento é da Matriz."""
    original = await saida_efetivada(motor, personas["ivo"])

    with pytest.raises(ErroDominio) as e:
        await estornar(motor, personas["odair"], original)
    assert e.value.codigo == "nao_encontrado"

    with pytest.raises(ErroDominio) as inexistente:
        await estornar(motor, personas["odair"], "mov-nao-existe")
    assert inexistente.value.codigo == "nao_encontrado"
    assert e.value.mensagem_publica == inexistente.value.mensagem_publica


async def test_quem_nao_tem_a_permissao_e_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Cleide movimenta estoque e não corrige o livro-razão; Rafael não faz
    nem uma coisa nem outra. A recusa vem ANTES da validação do corpo, para o
    erro de schema não descrever o formulário a quem não pode usá-lo."""
    original = await saida_efetivada(motor, personas["ivo"])
    for nome in ("cleide", "rafael", "sandra"):
        with pytest.raises(ErroDominio) as e:
            await estornar(motor, personas[nome], original)
        assert e.value.codigo == "nao_autorizado", nome


async def test_estorno_e_auditado_inclusive_quando_recusado(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """RN-D01 vale para a tentativa recusada: auditoria que só registra sucesso
    descreve um sistema onde ninguém tentou o que não podia."""
    original = await saida_efetivada(motor, personas["ivo"])
    with pytest.raises(ErroDominio):
        await estornar(motor, personas["cleide"], original)

    async with motor.connect() as c:
        achou = (
            await c.execute(
                sa.select(sa.func.count())
                .select_from(m.auditoria)
                .where(
                    m.auditoria.c.acao == "movimento_estorno.recusado",
                    m.auditoria.c.ator_id == personas["cleide"].id,
                )
            )
        ).scalar_one()
    assert achou > 0


# --------------------------------------------------------- AC-8 · confirmação
def test_ac8_estorno_e_descarte_exigem_confirmacao() -> None:
    """Não existe componente `confirm_action` (achado A-05): confirmar é decisão
    do motor de render diante do `confirm`, não composição que o modelo escolhe.
    O que se verifica é a bandeira, dos dois lados da declaração."""
    from estoque.application.registry.registry import buscar

    for nome in ("movimento_estorno", "movimento_descarte"):
        executavel = pipeline.buscar(nome)
        assert executavel is not None and executavel.confirm is True, nome

        comp = buscar(nome)
        assert comp is not None
        assert comp.commands[nome].confirm is True, nome


def test_ac8_o_par_negativo_existe_no_registro() -> None:
    """Sem um comando `confirm=False` em algum lugar, o teste acima passaria
    mesmo que `confirm` fosse ignorado e valesse sempre True."""
    from pydantic import BaseModel

    from estoque.application.commands.tipos import Comando

    class Vazio(BaseModel):
        pass

    async def _nunca(entrada: Any, ctx: Any) -> Any:  # pragma: no cover
        raise AssertionError

    sem_confirmacao = Comando(
        nome="t029-sem-confirmacao",
        requires=("movimento.estornar",),
        schema=Vazio,
        aplicar=_nunca,
        confirm=False,
    )
    assert sem_confirmacao.confirm is False


# ==========================================================================
# AC-1 e AC-2 — a exclusão que não existe
# ==========================================================================
VERBOS_QUE_APAGAM = {"DELETE", "PUT", "PATCH"}


def test_ac1_nenhuma_rota_registrada_edita_ou_exclui() -> None:
    """AC-1, pela varredura do `openapi()` do app REAL.

    Não é sobre `movimento`: é sobre a borda inteira. Nenhuma rota deste sistema
    responde a um verbo que substitui ou apaga — o que existe é `POST` em
    `/api/comandos/{nome}`, que cria. Uma rota nova de exclusão reprova aqui por
    padrão, sem depender de alguém lembrar de escrever o teste dela.
    """
    from estoque.server.app import app

    achados = [
        f"{metodo} {caminho}"
        for caminho, item in app.openapi()["paths"].items()
        for metodo in (m.upper() for m in item)
        if metodo in VERBOS_QUE_APAGAM
    ]
    assert achados == [], f"rotas que apagam ou substituem: {achados}"


def test_ac1_a_varredura_enxerga_as_rotas_que_existem() -> None:
    """Par negativo: um `openapi()` vazio faria o teste acima passar por
    cegueira. A rota de escrita do sistema tem de estar lá, e ser `POST`."""
    from estoque.server.app import app

    caminhos = app.openapi()["paths"]
    assert "/api/comandos/{nome}" in caminhos
    assert sorted(m.upper() for m in caminhos["/api/comandos/{nome}"]) == ["POST"]


def test_ac1_nenhum_comando_registrado_exclui_ou_edita_movimento() -> None:
    """A segunda superfície de escrita é o registro de comandos, e ele é
    enumerado: a rota única `/api/comandos/{nome}` só executa o que está aqui."""
    registrados = set(pipeline.registrados())
    proibidos = {"excluir", "apagar", "deletar", "remover", "editar", "alterar"}
    for nome in registrados:
        assert not any(p in nome for p in proibidos), nome
    # A lista fechada, por nome: um comando novo obriga a passar por esta linha.
    assert {
        "lote_liberar_quarentena",
        "lote_status",
        "movimento_saida",
        "movimento_estorno",
        "movimento_descarte",
        "controlado_autorizar",
        "recebimento_registrar",
    } <= registrados


async def test_ac1_o_comando_de_exclusao_nao_existe(
    motor: AsyncEngine, personas: dict[str, Ator]
) -> None:
    """Pedir um comando que não existe é indistinguível de pedir um que existe e
    está fora do alcance (ADR-0014) — e nenhum dos dois apaga nada."""
    with pytest.raises(ErroDominio) as e:
        await pipeline.executar(
            "movimento_excluir",
            {"movimento_id": "qualquer"},
            ator=personas["marco"],
            motor=motor,
            origem="tela",
            idempotency_key=secrets.token_hex(8),
        )
    assert e.value.codigo == "nao_encontrado"


# ------------------------------------------------- AC-2 · nem o Diretor exclui
@pytest.fixture
def sessao_de(dono: sa.Engine) -> Any:
    """Sessão real no banco: o app resolve o ator a cada requisição, do banco
    (`RN-A06`), então não há como injetar um ator falso pela borda."""

    def criar(usuario_id: str, papel: str) -> str:
        sid = secrets.token_urlsafe(32)
        agora = datetime.now(UTC)
        with dono.begin() as c:
            c.execute(
                sa.text(
                    "INSERT INTO unidade VALUES ('cd-matriz','Matriz','seco',true) "
                    "ON CONFLICT DO NOTHING"
                )
            )
            c.execute(
                sa.text(
                    "INSERT INTO usuario VALUES (:u,:u,:e,'x',:p,true) "
                    "ON CONFLICT (id) DO UPDATE SET papel = EXCLUDED.papel"
                ),
                {"u": usuario_id, "e": f"{usuario_id}@bertoni.test", "p": papel},
            )
            c.execute(
                sa.text(
                    "INSERT INTO usuario_unidade VALUES (:u,'cd-matriz') ON CONFLICT DO NOTHING"
                ),
                {"u": usuario_id},
            )
            c.execute(
                sa.text("INSERT INTO sessao VALUES (:s,:u,:a,:e)"),
                {"s": sid, "u": usuario_id, "a": agora, "e": agora + timedelta(hours=12)},
            )
        return sid

    return criar


@pytest.fixture(autouse=True)
async def _pool_limpo() -> Any:
    """Descarta o pool do app entre testes: cada teste roda no próprio loop, e a
    conexão asyncpg reaproveitada falha com "attached to a different loop"."""
    yield
    from estoque.server.app import _engine

    await _engine.dispose()


def _cliente(sid: str) -> AsyncClient:
    from estoque.server.app import CFG, app

    tok = secrets.token_urlsafe(24)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://teste",
        cookies={"csrf": tok, "sessao": sid},
        headers={"Origin": CFG.cors_origin, "X-CSRF-Token": tok},
    )


TENTATIVAS: tuple[tuple[str, str], ...] = (
    ("DELETE", "/api/movimentos/t029-qualquer"),
    ("PATCH", "/api/movimentos/t029-qualquer"),
    ("PUT", "/api/movimentos/t029-qualquer"),
    ("DELETE", "/api/comandos/movimento_saida"),
)


async def test_ac2_o_diretor_nao_exclui_movimento_pela_borda(sessao_de: Any) -> None:
    """CA-08. Marco tem mais permissões que qualquer outro papel, e nenhuma
    delas apaga movimento: não há rota para apagar."""
    sid = sessao_de("t029-marco", "diretor")
    async with _cliente(sid) as c:
        for metodo, caminho in TENTATIVAS:
            r = await c.request(metodo, caminho)
            assert r.status_code in (404, 405), f"{metodo} {caminho} -> {r.status_code}"


async def test_ac2_a_recusa_do_diretor_e_igual_a_de_qualquer_papel(sessao_de: Any) -> None:
    """ "Recusado igual a qualquer outro papel" é comparação, e é assim que ela
    se faz: mesmo status, mesmo corpo. Um Diretor recusado com outra mensagem
    ensinaria que o caminho existe para alguém."""
    respostas = []
    for usuario, papel in (
        ("t029-marco", "diretor"),
        ("t029-ivo", "gerente"),
        ("t029-cleide", "conferente"),
    ):
        sid = sessao_de(usuario, papel)
        async with _cliente(sid) as c:
            r = await c.request("DELETE", "/api/movimentos/t029-qualquer")
        respostas.append((r.status_code, r.text))
    assert len(set(respostas)) == 1, respostas


async def test_ac2_o_diretor_tambem_nao_exclui_pelo_comando(sessao_de: Any) -> None:
    """A rota de escrita existe e responde — o que não existe é o comando. O
    404 aqui vem do registro de comandos, não de um caminho HTTP ausente."""
    sid = sessao_de("t029-marco", "diretor")
    async with _cliente(sid) as c:
        r = await c.post(
            "/api/comandos/movimento_excluir",
            json={"movimento_id": "t029-qualquer"},
            headers={"Idempotency-Key": secrets.token_hex(8)},
        )
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "nao_encontrado"


async def test_ac2_a_borda_de_escrita_responde_de_verdade(sessao_de: Any) -> None:
    """Par negativo do teste acima: se `/api/comandos/{nome}` estivesse quebrada,
    todo POST daria 404 e o teste passaria sem provar nada. Um comando que
    EXISTE responde com outra coisa — aqui, a recusa de permissão do conferente."""
    sid = sessao_de("t029-cleide", "conferente")
    async with _cliente(sid) as c:
        r = await c.post(
            "/api/comandos/movimento_estorno",
            json={"movimento_id": "t029-qualquer", **CORRECAO},
            headers={"Idempotency-Key": secrets.token_hex(8)},
        )
    assert r.status_code != 404
    assert r.json()["erro"]["codigo"] == "nao_autorizado"
