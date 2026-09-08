"""T-040 · CSRF — AC-1 a AC-4.

Proteção que três documentos prometiam e nenhum código implementava
([A-002](../../docs/relatorios/A-002-auditoria-de-execucao.md), achado A-02).
O cookie era criado, o cliente mandava o header, e o servidor nunca o lia.
"""

import pytest
from fastapi import Request

from estoque.auth import csrf
from estoque.domain.erros import ErroDominio

ORIGEM = "http://localhost:5173"


def requisicao(
    metodo: str = "POST",
    caminho: str = "/api/comandos/x",
    cookie: str | None = "abc",
    header: str | None = "abc",
    origem: str | None = ORIGEM,
) -> Request:
    cabecalhos: list[tuple[bytes, bytes]] = []
    if cookie is not None:
        cabecalhos.append((b"cookie", f"csrf={cookie}".encode()))
    if header is not None:
        cabecalhos.append((b"x-csrf-token", header.encode()))
    if origem is not None:
        cabecalhos.append((b"origin", origem.encode()))
    return Request(
        {
            "type": "http",
            "method": metodo,
            "path": caminho,
            "headers": cabecalhos,
            "query_string": b"",
            "scheme": "http",
            "server": ("localhost", 5173),
            "root_path": "",
        }
    )


# --- AC-1 ------------------------------------------------------------------
def test_ac1_escrita_sem_token_e_recusada() -> None:
    with pytest.raises(ErroDominio) as e:
        csrf.conferir(requisicao(header=None), ORIGEM)
    assert e.value.codigo == "nao_autorizado"


def test_ac1_escrita_sem_cookie_e_recusada() -> None:
    with pytest.raises(ErroDominio):
        csrf.conferir(requisicao(cookie=None), ORIGEM)


# --- AC-2 ------------------------------------------------------------------
def test_ac2_token_diferente_do_cookie_e_recusado() -> None:
    with pytest.raises(ErroDominio):
        csrf.conferir(requisicao(cookie="abc", header="xyz"), ORIGEM)


def test_ac2_token_igual_passa() -> None:
    csrf.conferir(requisicao(cookie="abc", header="abc"), ORIGEM)


def test_ac2_comparacao_e_em_tempo_constante() -> None:
    """`==` vaza por temporização quantos caracteres o atacante acertou."""
    import inspect

    assert "compare_digest" in inspect.getsource(csrf.conferir)


# --- AC-3 ------------------------------------------------------------------
def test_ac3_origem_de_outro_dominio_e_recusada() -> None:
    with pytest.raises(ErroDominio) as e:
        csrf.conferir(requisicao(origem="https://evil.example"), ORIGEM)
    assert "origem" in e.value.mensagem_publica.lower()


@pytest.mark.parametrize(
    "origem",
    [
        "https://localhost:5173",  # esquema diferente
        "http://localhost:5174",  # porta diferente
        "http://localhos:5173",  # host quase igual
    ],
)
def test_ac3_origem_quase_igual_tambem_e_recusada(origem: str) -> None:
    """Comparar só o host aceitaria `http` onde se espera `https`."""
    with pytest.raises(ErroDominio):
        csrf.conferir(requisicao(origem=origem), ORIGEM)


def test_ac3_origem_ausente_ainda_exige_token() -> None:
    """Cliente de linha de comando não manda `Origin`. O token continua sendo
    exigido — senão bastaria omitir o cabeçalho para escapar."""
    csrf.conferir(requisicao(origem=None), ORIGEM)
    with pytest.raises(ErroDominio):
        csrf.conferir(requisicao(origem=None, header=None), ORIGEM)


# --- AC-4 ------------------------------------------------------------------
@pytest.mark.parametrize("caminho", ["/api/auth/entrar", "/api/auth/registrar"])
def test_ac4_login_e_cadastro_passam_sem_token(caminho: str) -> None:
    """Acontecem ANTES de existir sessão: não há cookie de onde tirar o token."""
    csrf.conferir(requisicao(caminho=caminho, cookie=None, header=None), ORIGEM)


def test_leitura_nao_exige_token() -> None:
    csrf.conferir(requisicao(metodo="GET", cookie=None, header=None), ORIGEM)


@pytest.mark.parametrize("metodo", ["POST", "PUT", "PATCH", "DELETE"])
def test_todo_metodo_de_escrita_e_coberto(metodo: str) -> None:
    with pytest.raises(ErroDominio):
        csrf.conferir(requisicao(metodo=metodo, header=None), ORIGEM)
