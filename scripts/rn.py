#!/usr/bin/env python3
"""`make rn RN-L05 RN-R02` — imprime so' as regras citadas.

O protocolo de leitura manda ler **so'** as `RN-*` que a tarefa cita. Mas o
arquivo e' um so', com 69 regras em 18 KB, e abrir o arquivo le' as 69 para usar
duas. Este script faz o recorte que o protocolo sempre pediu e nao tinha como
fazer.

Imprime a regra com a secao de onde ela veio, porque `RN-L05` fora de "Lote e
validade" perde metade do sentido, e a legenda de `[R]`/`[S]`/`[C]` quando
alguma das regras pedidas carrega marcador — o marcador e' o que diz se a regra
e' negociavel.
"""

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "docs" / "02-regras-de-negocio.md"

LEGENDA = (
    "**[R]** exigência regulatória · **[S]** separação de funções · "
    "**[C]** decisão comercial · sem marca: consequência operacional"
)


def indexar(texto: str) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """id -> (secao, linha da tabela), preservando a ordem do documento."""
    regras: dict[str, tuple[str, str]] = {}
    ordem: list[str] = []
    secao = ""
    for linha in texto.splitlines():
        if linha.startswith("### "):
            secao = linha.removeprefix("### ").strip()
        elif m := re.match(r"^\|\s*\*\*(RN-[A-Z]+\d+)\*\*\s*\|", linha):
            regras[m.group(1)] = (secao, linha.strip())
            ordem.append(m.group(1))
    return regras, ordem


def main() -> int:
    pedidos = [a.upper() for a in sys.argv[1:]]
    regras, ordem = indexar(FONTE.read_text(encoding="utf-8"))

    if not pedidos:
        fonte = FONTE.relative_to(RAIZ)
        print(f"uso: make rn RN-L05 RN-R02       ({len(regras)} regras em {fonte})")
        print("\nprefixos: " + ", ".join(sorted({r[:5].rstrip("0123456789") for r in ordem})))
        return 0

    faltando = [p for p in pedidos if p not in regras]
    achados = [p for p in ordem if p in pedidos]  # ordem do documento, sem repetir

    for i, rid in enumerate(achados):
        secao, linha = regras[rid]
        if i == 0 or regras[achados[i - 1]][0] != secao:
            print(f"\n### {secao}\n")
            print("| ID | Regra |")
            print("|---|---|")
        print(linha)

    if any(m in regras[r][1] for r in achados for m in ("**[R]**", "**[S]**", "**[C]**")):
        print(f"\n> {LEGENDA}")

    if faltando:
        # Nao e' aviso decorativo: id errado numa tarefa quer dizer que a tarefa
        # cita regra que nao existe, e isso e' achado, nao erro de digitacao.
        fonte = FONTE.relative_to(RAIZ)
        print(f"\n!! não existe(m) em {fonte}: {', '.join(faltando)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
