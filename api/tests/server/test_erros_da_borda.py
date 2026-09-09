"""Nenhum caminho alcançável pelo usuário devolve 500.

Achado ao escrever cenários de teste: uma métrica fora do enum levantava
`ValidationError`, que não é `ErroDominio` — escapava do handler e virava 500.
Status errado num caminho que qualquer pessoa alcança digitando.

O critério T-011 AC-5 ("erro inesperado devolve envelope genérico, sem stack")
estava escrito e não implementado.
"""

import inspect

from estoque.server import app
from estoque.server.rotas import auth


def test_existe_handler_para_entrada_invalida() -> None:
    fonte = inspect.getsource(app)
    assert "@app.exception_handler(ValidationError)" in fonte


def test_existe_handler_para_erro_inesperado() -> None:
    """Sem ele, qualquer exceção não prevista vaza como 500 cru."""
    fonte = inspect.getsource(app)
    assert "@app.exception_handler(Exception)" in fonte


def test_nenhuma_mensagem_publica_ecoa_a_entrada() -> None:
    """Ecoar o valor recebido devolveria conteúdo hostil para dentro do log e
    confirmaria ao atacante o que ele mandou."""
    fonte = inspect.getsource(app._invalido)
    assert "Entrada invalida." in fonte
    # nenhuma interpolação do erro na mensagem pública
    assert "{e}" not in fonte and "str(e)" not in fonte


def test_erro_inesperado_nao_devolve_stack() -> None:
    """A resposta carrega só código e mensagem fixa. O traceback vai para o log.

    Verifica o CONTEÚDO devolvido, não o texto do fonte: a primeira versão
    procurava a palavra "traceback" no código e falhava por causa do próprio
    comentário que explicava a decisão.
    """
    fonte = inspect.getsource(app._inesperado)
    assert "exception(" in fonte, "o traceback precisa ir para o log"

    corpo = _corpo_do_handler(fonte)
    assert corpo == {"ok": False, "erro": {"codigo": "invalido", "mensagem": "Erro interno."}}


def _corpo_do_handler(fonte: str) -> dict[str, object]:
    """Extrai o dicionário literal de `content=` do handler."""
    import ast

    arvore = ast.parse(inspect.cleandoc(fonte))
    for no in ast.walk(arvore):
        if isinstance(no, ast.keyword) and no.arg == "content":
            valor = ast.literal_eval(no.value)
            assert isinstance(valor, dict)
            return valor
    msg = "handler sem `content=`"
    raise AssertionError(msg)


def test_cadastro_nao_concede_papel() -> None:
    """ADR-0019: cadastro cria usuário SEM papel.

    Se deixasse escolher, `RN-R02` (liberação privativa do RT) e `CA-04` (dupla
    identificação) virariam enfeite — escalação de privilégio por formulário.
    """
    fonte = inspect.getsource(auth.registrar)
    assert "papel=None" in fonte
    # o corpo do pedido não tem campo de papel nem de unidade
    campos = set(auth.Cadastro.model_fields)
    assert campos == {"nome", "email", "senha"}, campos


def test_cadastro_nao_vira_verificador_de_contas() -> None:
    """Resposta idêntica para e-mail novo e já cadastrado — senão o formulário
    de cadastro passa a responder 'esta pessoa tem conta aqui?'."""
    fonte = inspect.getsource(auth.registrar)
    assert fonte.count("return ok(") == 1, "um único retorno, para os dois casos"
    assert "PH.hash(corpo.senha)" in fonte, "gasta o mesmo tempo nos dois caminhos"
