"""A regra da casa: uma regra que nunca falhou nao e' evidencia de nada.

Estes testes introduzem as violacoes DE PROPOSITO e afirmam que o verificador
quebra. Sem eles, `lint-imports` verde nao prova nada — pode estar verde porque
nao esta verificando.

O contrato testado e' o do ADR-0002, que sustenta a tese do projeto: o pipeline
do assistente nunca alcanca um comando de escrita.
"""

import subprocess
import sys
from pathlib import Path

VIOLACOES = Path(__file__).parent / "violacoes"
RAIZ = Path(__file__).parents[2]

# `python -m importlinter.cli` sai com codigo 0 e saida vazia — o modulo nao
# invoca o comando click. Usamos o console script do proprio venv.
EXECUTAVEL = Path(sys.executable).parent / "lint-imports"


def rodar(cwd: Path, config: str | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [str(EXECUTAVEL), "--no-logo"]
    if config:
        cmd += ["--config", config]
    # S603: o comando e' construido aqui, sem entrada externa.
    return subprocess.run(  # noqa: S603
        cmd, cwd=cwd, capture_output=True, text=True, check=False
    )


def test_o_executavel_do_verificador_existe() -> None:
    """Se o binario sumir, todos os testes abaixo passariam a testar nada."""
    assert EXECUTAVEL.is_file(), f"lint-imports nao encontrado em {EXECUTAVEL}"


def _falhou_por_contrato(r: subprocess.CompletedProcess[str]) -> bool:
    """Falhou por CONTRATO VIOLADO, nao por configuracao quebrada.

    Descoberto ao escrever este teste: `lint-imports` com pacote inexistente
    imprime 'Could not find package' e sai com codigo 0. Um verificador mal
    configurado passaria em silencio — exatamente o modo de falha que estes
    testes existem para impedir. Por isso a assercao exige a evidencia da
    violacao, nao so' o codigo de saida.
    """
    saida = r.stdout + r.stderr
    if "Could not find package" in saida or "Could not read any configuration" in saida:
        return False
    return r.returncode != 0 and "is not allowed to import" in saida


def test_violacao_direta_quebra_o_verificador() -> None:
    assert _falhou_por_contrato(rodar(VIOLACOES, "direta.cfg"))


def test_violacao_indireta_em_dois_saltos_quebra() -> None:
    """T-005 AC-6 — o caso que importa mais.

    Um import direto e' obvio e alguem barraria na revisao. O perigoso e' o
    indireto: assistant -> utils -> commands. Se o verificador so' pegasse o
    direto, a regra mais importante do projeto seria contornavel por indirecao,
    em silencio.
    """
    r = rodar(VIOLACOES, "indireta.cfg")
    assert _falhou_por_contrato(r)
    assert "indireta.utils" in r.stdout, "o caminho de dois saltos precisa aparecer"


def test_o_projeto_real_esta_limpo() -> None:
    r = rodar(RAIZ)
    assert r.returncode == 0, r.stdout
    assert "Contracts: 4 kept, 0 broken" in r.stdout
