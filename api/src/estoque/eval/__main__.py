"""`make eval` — roda a suíte e publica as métricas.

Mede os DOIS modos (ADR-0024): `livre` responde a pergunta original da v1
— com que frequência o modelo emite schema válido sozinho — e `restrito` é o
que o sistema realmente entrega. Publicar só um dos dois contaria meia história.

Recusa rodar com o adaptador mock: foi assim que a v1 publicou números de um
simulador sem perceber.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import estoque.application.registry.indice  # noqa: F401
from estoque.application.registry.registry import catalogo_de
from estoque.application.schema.validar import validar_schema
from estoque.assistant.adapter import extrair_json
from estoque.assistant.fabrica import criar_adaptador
from estoque.assistant.langfuse_obs import criar as criar_observador
from estoque.assistant.observador import Observador, ObservadorNulo
from estoque.assistant.trace import Modo
from estoque.domain.identidade import PERMISSOES_POR_PAPEL, Ator, PapelId
from estoque.eval.casos import CASOS, Caso

# ADR-0013: "CI falha se a taxa de schema válido cair mais de 5 pontos
# percentuais em relação à execução anterior registrada." A linha de base é
# um arquivo versionado, não recalculada a cada rodada — senão uma queda
# lenta, rodada a rodada, nunca cruzaria limiar nenhum.
#
# Mora DENTRO de `api/`, não em `docs/`: `make eval` roda em container cujo
# contexto de build é só `./api` (`docker-compose.yml`) — um caminho fora
# disso não existe no container, e a primeira execução real quebrou
# exatamente assim, tentando criar `/docs/relatorios` na raiz do container.
LINHA_DE_BASE = Path(__file__).resolve().parent / "linha_de_base.json"
TOLERANCIA_PP = 0.05

TODAS = frozenset({"cd-matriz", "cd-refrigerado", "filial-uberlandia"})
PERSONAS: dict[str, tuple[PapelId, frozenset[str]]] = {
    "marco": ("diretor", TODAS),
    "helena": ("rt", TODAS),
    "ivo": ("gerente", frozenset({"cd-matriz", "cd-refrigerado"})),
    "odair": ("gerente", frozenset({"filial-uberlandia"})),
    "cleide": ("conferente", frozenset({"cd-matriz", "cd-refrigerado"})),
    "rafael": ("comprador", TODAS),
    "sandra": ("auditoria", TODAS),
}


def ator_de(nome: str) -> Ator:
    papel, unidades = PERSONAS[nome]
    return Ator(
        id=f"u-{nome}",
        nome=nome.title(),
        papel=papel,
        unidades=unidades,  # type: ignore[arg-type]
        permissoes=PERMISSOES_POR_PAPEL[papel],
        ativo=True,
    )


@dataclass(slots=True)
class Resultado:
    caso: Caso
    modo: str
    schema_valido: bool
    composicao_correta: bool
    ms: int
    tokens_entrada: int
    custo_usd: float | None
    obtido: frozenset[str]


async def rodar_caso(caso: Caso, modo: Modo, obs: Observador) -> Resultado:
    ator = ator_de(caso.persona)
    cat = catalogo_de(ator)
    adaptador = criar_adaptador()
    inicio = time.perf_counter()
    r = await adaptador.compor(caso.pergunta, list(cat), modo=modo)
    ms = int((time.perf_counter() - inicio) * 1000)

    obtido: frozenset[str] = frozenset()
    valido = False
    if not r.trace.erro:
        try:
            bruto = extrair_json(r.bruto)
        except ValueError:
            bruto = None
        if bruto is not None:
            v = validar_schema(bruto, ator)
            # Composição vazia conta como schema válido: é a resposta correta
            # para pergunta fora do catálogo, e o prompt pede exatamente isso.
            valido = v.ok
            obtido = frozenset(v.aceitos)
            r.trace.aceitos = v.aceitos
            r.trace.rejeitados = [(x.tipo, x.motivo) for x in v.rejeitados]

    obs.composicao(trace=r.trace, ator_id=ator.id, papel=ator.papel, catalogo=len(cat))
    return Resultado(
        caso=caso,
        modo=modo,
        schema_valido=valido,
        # Para caso negativo, correto é NÃO compor.
        composicao_correta=(obtido == caso.esperado),
        ms=r.trace.ms_ate_primeiro_token or ms,
        tokens_entrada=r.trace.tokens_entrada,
        custo_usd=r.trace.custo_usd,
        obtido=obtido,
    )


def resumo(rs: list[Resultado], modo: str) -> dict[str, object]:
    do_modo = [r for r in rs if r.modo == modo]
    if not do_modo:
        return {}
    n = len(do_modo)
    tempos = sorted(r.ms for r in do_modo)
    custo = sum(r.custo_usd or 0 for r in do_modo)
    return {
        "modo": modo,
        "casos": n,
        "schema_valido": round(sum(r.schema_valido for r in do_modo) / n, 3),
        "composicao_correta": round(sum(r.composicao_correta for r in do_modo) / n, 3),
        "ms_p50": tempos[n // 2],
        "ms_p95": tempos[min(n - 1, int(n * 0.95))],
        "tokens_entrada_medio": round(sum(r.tokens_entrada for r in do_modo) / n),
        "custo_usd_total": round(custo, 6) if custo else None,
    }


def regrediu(atual: float, base: float, tolerancia: float = TOLERANCIA_PP) -> bool:
    """Regressão é queda de mais de `tolerancia` (fração 0–1) — nunca melhora,
    e nunca é sobre outra métrica: o ADR-0013 fala só de schema válido."""
    return (base - atual) > tolerancia


def carregar_linha_de_base() -> dict[str, float]:
    if not LINHA_DE_BASE.exists():
        return {}
    dados: dict[str, float] = json.loads(LINHA_DE_BASE.read_text(encoding="utf-8"))
    return dados


def gravar_linha_de_base(valores: dict[str, float]) -> None:
    LINHA_DE_BASE.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(valores, indent=2, sort_keys=True) + "\n"
    LINHA_DE_BASE.write_text(texto, encoding="utf-8")


async def principal(
    modos: Sequence[Modo], somente: str | None, *, atualizar_linha_de_base: bool = False
) -> int:
    adaptador = criar_adaptador()
    if type(adaptador).__name__ == "AdaptadorMock":
        print("recuso rodar com o mock: o número não valeria nada.", file=sys.stderr)
        return 2

    obs = criar_observador() or ObservadorNulo()
    casos = [c for c in CASOS if not somente or somente in c.id]
    rs: list[Resultado] = []

    for modo in modos:
        print(f"\n── modo {modo} ──")
        for caso in casos:
            r = await rodar_caso(caso, modo, obs)
            rs.append(r)
            marca = "ok " if r.composicao_correta else "ERR"
            esperado = ", ".join(sorted(caso.esperado)) or "(não compor)"
            obtido = ", ".join(sorted(r.obtido)) or "(não compôs)"
            print(
                f"  {marca} {caso.id:20} {r.ms:>5}ms  {obtido}"
                + ("" if r.composicao_correta else f"   ≠ esperado: {esperado}")
            )

    relatorio = {"modos": [resumo(rs, m) for m in modos]}
    print("\n" + json.dumps(relatorio, indent=2, ensure_ascii=False))

    for m in modos:
        s = resumo(rs, m)
        if s:
            obs.nota(nome=f"schema_valido_{m}", valor=float(s["schema_valido"]))  # type: ignore[arg-type]
            obs.nota(nome=f"composicao_correta_{m}", valor=float(s["composicao_correta"]))  # type: ignore[arg-type]
    obs.descarregar()

    if destino := os.environ.get("EVAL_SAIDA"):
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        print(f"\nrelatório em {destino}")

    base = carregar_linha_de_base()
    novos_valores: dict[str, float] = {
        str(m): cast(float, resumo(rs, m)["schema_valido"]) for m in modos if resumo(rs, m)
    }
    if not base:
        gravar_linha_de_base(novos_valores)
        print(f"\nlinha de base gravada em {LINHA_DE_BASE} (primeira execução, ADR-0013).")
        return 0

    saida = 0
    for nome_modo, atual in novos_valores.items():
        anterior = base.get(nome_modo)
        if anterior is None:
            continue
        if regrediu(atual, anterior):
            print(
                f"\nREGRESSÃO em {nome_modo}: schema_valido caiu de {anterior:.1%} para "
                f"{atual:.1%} (tolerância: {TOLERANCIA_PP:.0%})",
                file=sys.stderr,
            )
            saida = 1
    if saida == 0 and atualizar_linha_de_base:
        gravar_linha_de_base({**base, **novos_valores})
        print(f"\nlinha de base atualizada em {LINHA_DE_BASE}.")
    return saida


def main() -> int:
    p = argparse.ArgumentParser(description="Suíte de avaliação do assistente")
    p.add_argument("--modo", action="append", choices=["restrito", "ferramenta", "livre"])
    p.add_argument("--caso", help="roda só os casos cujo id contém este texto")
    p.add_argument(
        "--atualizar-linha-de-base",
        action="store_true",
        help="grava esta execução como nova linha de base (ADR-0013) — só se não regrediu",
    )
    a = p.parse_args()
    modos: list[Modo] = a.modo or ["restrito", "livre"]
    return asyncio.run(
        principal(modos, a.caso, atualizar_linha_de_base=a.atualizar_linha_de_base)
    )


if __name__ == "__main__":
    raise SystemExit(main())
