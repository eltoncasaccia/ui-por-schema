#!/usr/bin/env python3
"""`make env` — compara .env com .env.example.

Acrescentar variavel ao exemplo NAO atualiza o `.env` de quem ja' rodou. A
variavel some no padrao do compose: funciona, e esconde a opcao. Este script
mostra a diferenca e oferece completar.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def chaves(p: Path) -> dict[str, str]:
    if not p.exists():
        return {}
    return {
        m.group(1): m.group(2)
        for l in p.read_text().splitlines()
        if (m := re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", l))
    }


def main() -> int:
    exemplo, atual = chaves(RAIZ / ".env.example"), chaves(RAIZ / ".env")
    if not atual:
        print("sem .env — rode `make up`, que cria a partir do exemplo")
        return 1

    faltando = [k for k in exemplo if k not in atual]
    sobrando = [k for k in atual if k not in exemplo]
    vazias = [k for k in ("OPENROUTER_API_KEY", "SESSAO_SECRET") if not atual.get(k)]

    if faltando:
        print(f"faltam no .env ({len(faltando)}):")
        for k in faltando:
            print(f"  {k}={exemplo[k]}")
    if sobrando:
        print("no .env e não no exemplo:", ", ".join(sobrando))
    if vazias:
        print("vazias e importantes:", ", ".join(vazias))
    if not (faltando or sobrando or vazias):
        print("`.env` em dia com o exemplo")
        return 0

    if faltando and "--completar" in sys.argv:
        with (RAIZ / ".env").open("a") as f:
            f.write("\n# acrescentadas por `make env-completar`\n")
            for k in faltando:
                f.write(f"{k}={exemplo[k]}\n")
        print(f"\n{len(faltando)} variáveis acrescentadas ao .env")
    elif faltando:
        print("\nrode `make env-completar` para acrescentar com os valores do exemplo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
