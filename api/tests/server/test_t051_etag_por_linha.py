"""T-051 AC-1, AC-2, AC-3 — etag na leitura, contra Postgres real.

Dois formatos:

  - `controlado_autorizar` — etag por BLOCO, como a T-050 já fez para
    `quarentena_liberar`: `alvo_id` é fixo por `params.movimento_id`.
  - `movimento_saida`, `movimento_descarte`, `movimento_estorno` — etag por
    LINHA: a pessoa escolhe o candidato depois de ler. O AC-3 é o que prova
    isso em cada um — escrever com o etag da linha ERRADA (não a escolhida)
    tem que dar `conflito`, não só "etag velho".

Pulam sem banco: `make db-local && make migrate`, e `make db-local` DE NOVO.
"""

import secrets
from collections.abc import AsyncGenerator
from datetime import date, timedelta
from typing import Any, cast

import pytest
import sqlalchemy as sa
from borda import cliente, criar_sessao, descartar_pool, motor_dono

PRODUTO = "t051-prod"
UNIDADE = "cd-matriz"

MOV_CONTROLADO = "t051-mov-ctrl"
LOTE_CONTROLADO = "t051-lote-ctrl"
PRODUTO_CONTROLADO = "t051-prod-ctrl"

LOTE_A = "t051-lote-a"  # validade mais curta — a proposta do FEFO
LOTE_B = "t051-lote-b"  # validade mais longa — a alternativa

LOTE_DESC_A = "t051-lote-desc-a"  # bloqueado
LOTE_DESC_B = "t051-lote-desc-b"  # vencido
PRODUTO_DESC = "t051-prod-desc"
GERENTE = "t051-ivo"

LOTE_ESTORNO = "t051-lote-est"
PRODUTO_ESTORNO = "t051-prod-est"
SAIDA_1 = "t051-saida-1"
SAIDA_2 = "t051-saida-2"


@pytest.fixture(autouse=True)
async def _pool_limpo() -> AsyncGenerator[None]:
    yield
    await descartar_pool()


@pytest.fixture(autouse=True)
def _semear() -> None:
    hoje = date.today()
    with motor_dono().begin() as c:
        # --- controlado_autorizar: um movimento aguardando autorização ----
        c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'9990000000601','T051 Controlado','F','x','controlado','A',true,500) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PRODUTO_CONTROLADO},
        )
        c.execute(
            sa.text(
                "INSERT INTO lote VALUES "
                "(:l,:p,'L-051C','cd-matriz',:f,:v,'liberado',null) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "l": LOTE_CONTROLADO,
                "p": PRODUTO_CONTROLADO,
                "f": hoje - timedelta(days=100),
                "v": hoje + timedelta(days=400),
            },
        )
        c.execute(
            sa.text(
                "INSERT INTO usuario VALUES "
                "('t051-cleide','Cleide t051','t051-cleide@bertoni.test','x','conferente',"
                "true) ON CONFLICT (id) DO NOTHING"
            )
        )
        c.execute(
            sa.text(
                "INSERT INTO usuario_unidade VALUES ('t051-cleide','cd-matriz') "
                "ON CONFLICT DO NOTHING"
            )
        )
        # Saldo para a autorização poder efetivar (5 pedidos, ao menos 5 em caixa).
        c.execute(
            sa.text(
                "INSERT INTO movimento VALUES "
                "(:m,:l,'cd-matriz','entrada',20,'recebimento',null,'t051-cleide',null,"
                "'efetivado',now(),null,null,null) ON CONFLICT (id) DO NOTHING"
            ),
            {"m": f"{LOTE_CONTROLADO}-entrada", "l": LOTE_CONTROLADO},
        )
        # Um gatilho recusa transição para o MESMO status (RN-C01) — apagar e
        # reinserir, em vez de UPSERT, é o que deixa este teste repetível.
        c.execute(sa.text("DELETE FROM movimento WHERE id=:m"), {"m": MOV_CONTROLADO})
        c.execute(
            sa.text(
                "INSERT INTO movimento VALUES "
                "(:m,:l,'cd-matriz','saida',5,'venda',null,'t051-cleide',null,"
                "'aguardando_autorizacao',now(),null,null,null)"
            ),
            {"m": MOV_CONTROLADO, "l": LOTE_CONTROLADO},
        )

        # --- movimento_saida: dois lotes liberados, saldos via entrada -----
        c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'9990000000602','T051 Saida','F','x','comum','A',true,100) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PRODUTO},
        )
        for lote_id, dias_validade in ((LOTE_A, 200), (LOTE_B, 300)):
            c.execute(
                sa.text(
                    "INSERT INTO lote VALUES "
                    "(:l,:p,:n,'cd-matriz',:f,:v,'liberado',null) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "l": lote_id,
                    "p": PRODUTO,
                    "n": f"N-{lote_id}",
                    "f": hoje - timedelta(days=10),
                    "v": hoje + timedelta(days=dias_validade),
                },
            )
            c.execute(sa.text("UPDATE lote SET status='liberado' WHERE id=:l"), {"l": lote_id})
            c.execute(
                sa.text(
                    "INSERT INTO movimento VALUES "
                    "(:m,:l,'cd-matriz','entrada',50,'recebimento',null,'t051-cleide',null,"
                    "'efetivado',now(),null,null,null) ON CONFLICT (id) DO NOTHING"
                ),
                {"m": f"{lote_id}-entrada", "l": lote_id},
            )

        # --- movimento_descarte: dois lotes só-descarte (bloqueado/vencido) -
        c.execute(
            sa.text(
                "INSERT INTO usuario VALUES "
                "('t051-ivo','Ivo t051','t051-ivo@bertoni.test','x','gerente',true) "
                "ON CONFLICT (id) DO NOTHING"
            )
        )
        c.execute(
            sa.text(
                "INSERT INTO usuario_unidade VALUES ('t051-ivo','cd-matriz') "
                "ON CONFLICT DO NOTHING"
            )
        )
        c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'9990000000603','T051 Descarte','F','x','comum','A',true,100) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PRODUTO_DESC},
        )
        c.execute(
            sa.text(
                "INSERT INTO lote VALUES "
                "(:l,:p,'N-DESC-A','cd-matriz',:f,:v,'bloqueado',null) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "l": LOTE_DESC_A,
                "p": PRODUTO_DESC,
                "f": hoje - timedelta(days=300),
                "v": hoje + timedelta(days=200),
            },
        )
        c.execute(sa.text("UPDATE lote SET status='bloqueado' WHERE id=:l"), {"l": LOTE_DESC_A})
        c.execute(
            sa.text(
                "INSERT INTO lote VALUES "
                "(:l,:p,'N-DESC-B','cd-matriz',:f,:v,'liberado',null) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "l": LOTE_DESC_B,
                "p": PRODUTO_DESC,
                "f": hoje - timedelta(days=400),
                "v": hoje - timedelta(days=10),  # vencido
            },
        )
        c.execute(sa.text("UPDATE lote SET status='liberado' WHERE id=:l"), {"l": LOTE_DESC_B})
        for lote_id in (LOTE_DESC_A, LOTE_DESC_B):
            c.execute(
                sa.text(
                    "INSERT INTO movimento VALUES "
                    "(:m,:l,'cd-matriz','entrada',30,'recebimento',null,'t051-cleide',null,"
                    "'efetivado',now(),null,null,null) ON CONFLICT (id) DO NOTHING"
                ),
                {"m": f"{lote_id}-entrada", "l": lote_id},
            )
            # Uma execução anterior pode ter descartado o lote inteiro (o
            # descarte zera o saldo) — uma entrada nova, id sempre distinto,
            # devolve saldo positivo sem depender de desfazer o descarte.
            c.execute(
                sa.text(
                    "INSERT INTO movimento VALUES "
                    "(:m,:l,'cd-matriz','entrada',30,'recebimento',null,'t051-cleide',null,"
                    "'efetivado',now(),null,null,null)"
                ),
                {"m": f"{lote_id}-reforco-{secrets.token_hex(4)}", "l": lote_id},
            )

        # --- movimento_estorno: um lote com DUAS saídas efetivadas ----------
        c.execute(
            sa.text(
                "INSERT INTO produto VALUES "
                "(:p,'9990000000604','T051 Estorno','F','x','comum','A',true,100) "
                "ON CONFLICT DO NOTHING"
            ),
            {"p": PRODUTO_ESTORNO},
        )
        c.execute(
            sa.text(
                "INSERT INTO lote VALUES "
                "(:l,:p,'N-EST','cd-matriz',:f,:v,'liberado',null) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "l": LOTE_ESTORNO,
                "p": PRODUTO_ESTORNO,
                "f": hoje - timedelta(days=10),
                "v": hoje + timedelta(days=300),
            },
        )
        c.execute(
            sa.text(
                "INSERT INTO movimento VALUES "
                "(:m,:l,'cd-matriz','entrada',50,'recebimento',null,'t051-cleide',null,"
                "'efetivado',now(),null,null,null) ON CONFLICT (id) DO NOTHING"
            ),
            {"m": f"{LOTE_ESTORNO}-entrada", "l": LOTE_ESTORNO},
        )
        for mov_id in (SAIDA_1, SAIDA_2):
            # Estornos de execuções anteriores referenciam estas saídas —
            # apagar os filhos antes do pai, ou o FK recusa (repetível).
            c.execute(
                sa.text("DELETE FROM movimento WHERE estorna_movimento_id=:m"), {"m": mov_id}
            )
            c.execute(sa.text("DELETE FROM movimento WHERE id=:m"), {"m": mov_id})
            c.execute(
                sa.text(
                    "INSERT INTO movimento VALUES "
                    "(:m,:l,'cd-matriz','saida',1,'avaria',null,'t051-cleide',null,"
                    "'efetivado',now(),null,null,null)"
                ),
                {"m": mov_id, "l": LOTE_ESTORNO},
            )


def helena() -> str:
    return criar_sessao(usuario_id="t051-helena", papel="rt", unidades=("cd-matriz",))


def cleide() -> str:
    return criar_sessao(usuario_id="t051-cleide", papel="conferente", unidades=("cd-matriz",))


async def _dados(sid: str, componente: str, params: dict[str, Any]) -> dict[str, Any]:
    async with cliente(sid) as cli:
        r = await cli.post(
            f"/api/componentes/{componente}/dados",
            json={"params": params, "pagina": {"limite": 20, "cursor": None}},
        )
    return cast(dict[str, Any], r.json())


async def _comando(sid: str, nome: str, corpo: dict[str, Any], etag: str) -> Any:
    async with cliente(sid) as cli:
        return await cli.post(
            f"/api/comandos/{nome}",
            headers={"If-Match": etag, "Idempotency-Key": secrets.token_hex(8)},
            json=corpo,
        )


# --------------------------------------------------- controlado_autorizar ---


async def test_ac1_controlado_autorizar_bloc_level_ponta_a_ponta() -> None:
    sid = helena()
    d = await _dados(sid, "controlado_autorizar", {"movimento_id": MOV_CONTROLADO})
    etag = d["meta"]["etag"]
    assert isinstance(etag, str) and len(etag) > 0

    r = await _comando(
        sid,
        "controlado_autorizar",
        {"movimento_id": MOV_CONTROLADO, "decisao": "autorizar", "motivo": "receita conferida"},
        etag,
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


async def test_ac1_negativo_etag_desatualizado_devolve_conflito() -> None:
    sid = helena()
    d1 = await _dados(sid, "controlado_autorizar", {"movimento_id": MOV_CONTROLADO})
    etag_velho = d1["meta"]["etag"]

    ok1 = await _comando(
        sid,
        "controlado_autorizar",
        {"movimento_id": MOV_CONTROLADO, "decisao": "autorizar", "motivo": "receita conferida"},
        etag_velho,
    )
    assert ok1.status_code == 200, ok1.text

    r2 = await _comando(
        sid,
        "controlado_autorizar",
        {
            "movimento_id": MOV_CONTROLADO,
            "decisao": "recusar",
            "motivo": "tentativa com etag velho",
        },
        etag_velho,
    )
    assert r2.json()["ok"] is False
    assert r2.json()["erro"]["codigo"] == "conflito"


# -------------------------------------------------------- movimento_saida ---


async def _linhas_saida(sid: str) -> dict[str, Any]:
    d = await _dados(sid, "movimento_saida", {"produto_id": PRODUTO, "unidade_id": UNIDADE})
    return cast(dict[str, Any], d["dados"])


async def test_ac2_cada_linha_tem_etag_proprio() -> None:
    dados = await _linhas_saida(cleide())
    proposta = dados["proposta"]
    alternativas = dados["alternativas"]
    assert proposta["lote_id"] == LOTE_A  # menor validade — RN-L02
    assert len(alternativas) == 1 and alternativas[0]["lote_id"] == LOTE_B
    assert isinstance(proposta["etag"], str) and len(proposta["etag"]) > 0
    assert proposta["etag"] != alternativas[0]["etag"]


async def test_ac3_escrever_com_o_etag_da_linha_escolhida_e_aceito() -> None:
    sid = cleide()
    dados = await _linhas_saida(sid)
    proposta = dados["proposta"]

    r = await _comando(
        sid,
        "movimento_saida",
        {"lote_id": proposta["lote_id"], "quantidade": 1, "motivo": "avaria"},
        proposta["etag"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


async def test_ac3_negativo_etag_de_outra_linha_e_recusado() -> None:
    """O critério central: o etag da ALTERNATIVA não serve para escrever na
    PROPOSTA — se servisse, o etag seria por bloco disfarçado de "por linha"."""
    sid = cleide()
    dados = await _linhas_saida(sid)
    proposta, alternativa = dados["proposta"], dados["alternativas"][0]

    def _saidas() -> int:
        with motor_dono().connect() as c:
            return cast(
                int,
                c.execute(
                    sa.text("SELECT count(*) FROM movimento WHERE lote_id=:l AND tipo='saida'"),
                    {"l": proposta["lote_id"]},
                ).scalar_one(),
            )

    antes = _saidas()
    r = await _comando(
        sid,
        "movimento_saida",
        {"lote_id": proposta["lote_id"], "quantidade": 1, "motivo": "avaria"},
        alternativa["etag"],
    )
    assert r.json()["ok"] is False
    assert r.json()["erro"]["codigo"] == "conflito"
    # Nenhuma saída NOVA nasceu da tentativa recusada — não importa quantas
    # já existiam de outros testes deste arquivo.
    assert _saidas() == antes


# ----------------------------------------------------- movimento_descarte ---


async def test_ac2_ac3_descarte_etag_por_linha() -> None:
    sid = helena()
    d = await _dados(sid, "movimento_descarte", {"unidade_id": UNIDADE})
    fila = {linha["lote_id"]: linha for linha in d["dados"]["fila"]}
    a, b = fila[LOTE_DESC_A], fila[LOTE_DESC_B]
    assert isinstance(a["etag"], str) and a["etag"] != b["etag"]

    corpo_a = {
        "lote_id": LOTE_DESC_A,
        "motivo": "avaria",
        "justificativa": "lote com embalagem violada, sem condição de venda",
        "segunda_identificacao_id": GERENTE,
    }

    # Negativo primeiro: o etag de B não serve para descartar A.
    r_errado = await _comando(sid, "movimento_descarte", corpo_a, b["etag"])
    assert r_errado.json()["ok"] is False
    assert r_errado.json()["erro"]["codigo"] == "conflito"

    r_certo = await _comando(sid, "movimento_descarte", corpo_a, a["etag"])
    assert r_certo.status_code == 200, r_certo.text
    assert r_certo.json()["ok"] is True


# ------------------------------------------------------ movimento_estorno ---


async def test_ac2_ac3_estorno_etag_por_linha() -> None:
    sid = helena()
    d = await _dados(sid, "movimento_estorno", {"lote_id": LOTE_ESTORNO})
    lancamentos = {linha["movimento_id"]: linha for linha in d["dados"]["lancamentos"]}
    l1, l2 = lancamentos[SAIDA_1], lancamentos[SAIDA_2]
    assert isinstance(l1["etag"], str) and l1["etag"] != l2["etag"]

    corpo_1 = {
        "movimento_id": SAIDA_1,
        "motivo": "erro_de_separacao",
        "complemento": "separado o lote errado, corrigindo pelo estorno",
    }

    # Negativo: o etag do lançamento 2 não serve para estornar o 1.
    r_errado = await _comando(sid, "movimento_estorno", corpo_1, l2["etag"])
    assert r_errado.json()["ok"] is False
    assert r_errado.json()["erro"]["codigo"] == "conflito"

    r_certo = await _comando(sid, "movimento_estorno", corpo_1, l1["etag"])
    assert r_certo.status_code == 200, r_certo.text
    assert r_certo.json()["ok"] is True
