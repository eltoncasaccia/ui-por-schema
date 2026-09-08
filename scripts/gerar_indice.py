#!/usr/bin/env python3
"""Gera os dois indices que todo componente teria de editar. Acordo §4.

O `indice.py` ja' se declarava GERADO por `make gerar-indice` — e o alvo nunca
existiu. O `views/indice.ts` era escrito a mao. Sao os dois unicos arquivos que
as sete tarefas de componente precisariam tocar ao mesmo tempo: 22 componentes
registrados a mao em dois arquivos so' sao 44 conflitos de merge garantidos.

Varre `api/src/estoque/registry/componentes/*.py` e `web/src/views/*.tsx`, em
ordem, e reescreve os dois indices. Deterministico: rodar duas vezes produz o
mesmo byte, que e' o que permite ao CI conferir se alguem editou a mao.

Uso:
    python3 scripts/gerar_indice.py            # reescreve
    python3 scripts/gerar_indice.py --conferir # falha se estiver desatualizado
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
COMPONENTES = RAIZ / "api" / "src" / "estoque" / "registry" / "componentes"
INDICE_PY = RAIZ / "api" / "src" / "estoque" / "registry" / "indice.py"
VIEWS = RAIZ / "web" / "src" / "views"
INDICE_TS = VIEWS / "indice.ts"

# Arquivos de `views/` que nao sao componente. `indice.ts` e `tipos.ts` sao
# `.ts`, e o filtro e' por `.tsx` — mas a lista fica explicita para o dia em
# que alguem criar um utilitario `.tsx` ali.
NAO_SAO_VIEW: frozenset[str] = frozenset()


def modulos() -> list[str]:
    return sorted(
        p.stem for p in COMPONENTES.glob("*.py") if not p.stem.startswith("__")
    )


def views() -> list[str]:
    return sorted(p.stem for p in VIEWS.glob("*.tsx") if p.stem not in NAO_SAO_VIEW)


def texto_py(nomes: list[str]) -> str:
    if not nomes:
        importacoes = ""
        todos = "[]"
    elif len(nomes) == 1:
        importacoes = f"from estoque.registry.componentes import {nomes[0]}\n"
        todos = f'["{nomes[0]}"]'
    else:
        corpo = "".join(f"    {n},\n" for n in nomes)
        importacoes = f"from estoque.registry.componentes import (\n{corpo})\n"
        todos = "[\n" + "".join(f'    "{n}",\n' for n in nomes) + "]"
    return f'''"""Importa todos os componentes, registrando-os. Ponto unico de entrada.

Este modulo e' GERADO por `make gerar-indice` varrendo `componentes/*.py`.
Nao edite a mao: 22 componentes registrados manualmente num arquivo so' seriam
22 conflitos de merge garantidos em trabalho paralelo.
"""

{importacoes}from estoque.registry.orcamento import verificar_teto

__all__ = {todos}

verificar_teto()  # RNF-08: falha a inicializacao acima de 25 componentes
'''


def texto_ts(nomes: list[str]) -> str:
    importacoes = "".join(f"import {{ view as {n} }} from './{n}'\n" for n in nomes)
    mapa = "".join(f"  {n},\n" for n in nomes)
    return f"""/* GERADO por `make gerar-indice` — NÃO EDITE.
 *
 * Varre `views/*.tsx`. É o par do `registry/indice.py` no lado cliente: os dois
 * únicos arquivos que toda tarefa de componente precisaria editar, e por isso
 * os dois únicos que ninguém edita.
 */
import type {{ ComponentId }} from '../generated/componentes'
{importacoes}
/**
 * O mapa id → view. Lado cliente da bijeção do ADR-0017.
 *
 * `Record<ComponentId, ...>` é a metade que o COMPILADOR garante: falta uma
 * view aqui e o `tsc` recusa. A outra metade — view sobrando, sem registro na
 * API — é o teste de bijeção, porque tipo nenhum vê o servidor.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const VIEWS: Record<ComponentId, (props: {{ vm: any }}) => JSX.Element> = {{
{mapa}}}

export const IDS_DAS_VIEWS = Object.keys(VIEWS).sort()
"""


def main() -> int:
    conferir = "--conferir" in sys.argv
    alvos = [(INDICE_PY, texto_py(modulos())), (INDICE_TS, texto_ts(views()))]

    if conferir:
        sujos = [
            p for p, novo in alvos if not p.exists() or p.read_text("utf8") != novo
        ]
        for p in sujos:
            print(f"desatualizado (editado a mao?): {p.relative_to(RAIZ)}")
        if sujos:
            print("rode `make gerar-indice`")
            return 1
        print(f"indices em dia — {len(modulos())} componentes, {len(views())} views")
        return 0

    for p, novo in alvos:
        p.write_text(novo, "utf8")
    print(f"gerado indice.py ({len(modulos())}) e views/indice.ts ({len(views())})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
