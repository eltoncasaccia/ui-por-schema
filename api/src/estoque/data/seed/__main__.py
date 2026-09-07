"""`make seed` — popula o banco. Idempotente: rodar duas vezes nao duplica."""

import asyncio
import os
import sys
from datetime import UTC, datetime

import sqlalchemy as sa
from argon2 import PasswordHasher
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from estoque.data import modelos as m
from estoque.data.seed import dados

SENHA_DEMO = "demo"


async def semear(url: str) -> None:
    ph = PasswordHasher()
    hash_demo = ph.hash(SENHA_DEMO)
    eng = create_async_engine(url, future=True)

    async with eng.begin() as c:
        await _upsert(
            c,
            m.unidade,
            [{"id": i, "nome": n, "tipo": t, "sala_cofre": s} for i, n, t, s in dados.UNIDADES],
            ["id"],
        )

        await _upsert(
            c,
            m.produto,
            [
                {
                    "id": i,
                    "ean": e,
                    "nome": n,
                    "fabricante": f,
                    "principio_ativo": pa,
                    "classe": cl,
                    "curva_abc": cv,
                    "ativo": a,
                    "custo_unitario_centavos": ct,
                }
                for i, e, n, f, pa, cl, cv, a, ct in dados.PRODUTOS
            ],
            ["id"],
        )

        await _upsert(
            c,
            m.usuario,
            [
                {
                    "id": i,
                    "nome": n,
                    "email": e,
                    "senha_hash": hash_demo,
                    "papel": p,
                    "ativo": True,
                }
                for i, n, e, p, _u in dados.USUARIOS
            ],
            ["id"],
        )

        await _upsert(
            c,
            m.usuario_unidade,
            [
                {"usuario_id": i, "unidade_id": u}
                for i, _n, _e, _p, unis in dados.USUARIOS
                for u in unis
            ],
            ["usuario_id", "unidade_id"],
        )

        await _upsert(
            c,
            m.lote,
            [
                {
                    "id": lid,
                    "produto_id": pid,
                    "numero": num,
                    "unidade_id": uid,
                    "fabricacao": fab,
                    "validade": val,
                    "status": st,
                    "endereco": end,
                }
                for lid, pid, num, uid, fab, val, st, end in dados.lotes()
            ],
            ["id"],
        )

        movs: list[dict[str, object]] = []
        for mv in dados.movimentos():
            linha: dict[str, object] = {
                "complemento": None,
                "autorizador_id": None,
                "estorna_movimento_id": None,
                "cliente_id": None,
                "nota_fiscal": None,
                "criado_em": datetime.now(UTC),
            }
            linha.update(mv)
            movs.append(linha)
        await _upsert(c, m.movimento, movs, ["id"])

        await _upsert(
            c,
            m.registro_temperatura,
            [
                {"id": i, "unidade_id": u, "medido_em": t, "celsius": ce}
                for i, u, t, ce in dados.temperaturas()
            ],
            ["id"],
        )

        await c.execute(sa.text("REFRESH MATERIALIZED VIEW saldo_lote"))

    async with eng.connect() as c:
        n_lote = (await c.execute(sa.select(sa.func.count()).select_from(m.lote))).scalar_one()
        n_mov = (
            await c.execute(sa.select(sa.func.count()).select_from(m.movimento))
        ).scalar_one()
        n_tmp = (
            await c.execute(sa.select(sa.func.count()).select_from(m.registro_temperatura))
        ).scalar_one()
    await eng.dispose()
    print(
        f"seed ok: {len(dados.USUARIOS)} usuarios, {n_lote} lotes, "
        f"{n_mov} movimentos, {n_tmp} leituras de temperatura"
    )
    print(f"senha de todas as personas: {SENHA_DEMO!r}")


async def _upsert(
    conn: AsyncConnection,
    tabela: sa.Table,
    linhas: list[dict[str, object]],
    chave: list[str],
) -> None:
    """ON CONFLICT DO NOTHING — e' o que torna o seed idempotente (T-035 AC-2)."""
    if not linhas:
        return
    await conn.execute(
        pg_insert(tabela).values(linhas).on_conflict_do_nothing(index_elements=chave)
    )


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL ausente", file=sys.stderr)
        return 1
    asyncio.run(semear(url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
