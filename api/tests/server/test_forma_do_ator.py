"""Regressao do bug da tela branca.

`/auth/entrar` devolvia {id, nome, papel} e `/auth/eu` devolvia o ator completo.
O cliente tratava os dois como a mesma coisa: `unidades` chegava undefined depois
do login e a tela quebrava em branco ate' o refresh.

Duas formas do mesmo conceito e' um bug esperando acontecer. A regra que passa a
valer: existe UMA funcao que serializa o ator, e os dois endpoints usam ela.
"""

import ast
from pathlib import Path

APP = Path(__file__).parents[2] / "src" / "estoque" / "server" / "app.py"


def test_login_e_eu_usam_a_mesma_serializacao() -> None:
    arvore = ast.parse(APP.read_text())
    retornos: dict[str, list[str]] = {}
    for no in ast.walk(arvore):
        if isinstance(no, ast.AsyncFunctionDef) and no.name in {"entrar", "eu"}:
            retornos[no.name] = [
                c.func.id
                for c in ast.walk(no)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
            ]
    assert "_eu" in retornos["entrar"], "login precisa devolver a forma completa do ator"
    assert "_eu" in retornos["eu"]


def test_existe_uma_unica_funcao_de_serializacao_do_ator() -> None:
    texto = APP.read_text()
    assert texto.count("def _eu(") == 1
    # nenhum dicionario de ator montado a mao fora dela
    assert texto.count('"unidades": sorted(ator.unidades)') == 1
