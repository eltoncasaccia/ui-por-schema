"""Erros de dominio. CONTRATOS secao 2, ADR-0014.

Regra que governa este modulo: a mensagem publica nunca revela a existencia
nem o conteudo de um registro negado (RN-A07), e nunca lista ids — correcao
direta do vazamento da v1.
"""

from typing import Literal

CodigoErro = Literal[
    "nao_autenticado",  # nao ha ator
    "nao_autorizado",  # escopo DECLARADO negado (uma unidade) — ADR-0014
    "nao_encontrado",  # inexistente OU registro fora do escopo — indistinguiveis
    "invalido",  # falha de validacao de entrada
    "conflito",  # etag divergente, ou regra de estado violada
    "limite",  # rate limit
]


class ErroDominio(Exception):
    """Erro com duas faces: uma publica e uma interna.

    `detalhe_interno` NUNCA e' serializado para o cliente. E' o unico lugar
    onde `nao_encontrado` por inexistencia e `nao_encontrado` por escopo se
    distinguem — no log do servidor, nunca na resposta.
    """

    __slots__ = ("codigo", "detalhe_interno", "mensagem_publica")

    def __init__(
        self,
        codigo: CodigoErro,
        mensagem_publica: str,
        detalhe_interno: object | None = None,
    ) -> None:
        super().__init__(mensagem_publica)
        self.codigo: CodigoErro = codigo
        self.mensagem_publica = mensagem_publica
        self.detalhe_interno = detalhe_interno

    def __repr__(self) -> str:
        # Sem detalhe_interno: repr vaza para log de terceiro e para traceback.
        return f"ErroDominio({self.codigo!r}, {self.mensagem_publica!r})"


def nao_encontrado(detalhe_interno: object | None = None) -> ErroDominio:
    """Resposta unica para inexistente e para fora de escopo (ADR-0014).

    A mensagem e' constante de proposito: qualquer variacao vira oraculo de
    enumeracao de registros.
    """
    return ErroDominio("nao_encontrado", "Registro nao encontrado.", detalhe_interno)


def nao_autorizado(o_que: str) -> ErroDominio:
    """Negativa de escopo DECLARADO — uma unidade, um recurso que o ator ja sabe
    que existe. Retornar vazio aqui ensinaria um fato falso (ADR-0014)."""
    return ErroDominio("nao_autorizado", f"Sem acesso a {o_que}.")
