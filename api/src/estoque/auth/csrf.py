"""Proteção CSRF por dupla submissão. ADR-0019, T-040.

Por que `SameSite=Lax` não basta: ele bloqueia o cookie em requisição
cross-site iniciada por navegação de terceiro, mas não cobre tudo — subdomínio
comprometido, cliente antigo que ignora o atributo, e o próprio `Lax` permite
GET de navegação. A segunda camada é barata e fecha o resto.

Dupla submissão: o mesmo valor vai num cookie legível por JS e num header. Um
site de terceiro consegue DISPARAR a requisição (o cookie viaja), mas não
consegue LER o cookie para montar o header — a política de mesma origem o
impede.

Comparação em tempo constante: comparar token com `==` vaza, por temporização,
quantos caracteres iniciais o atacante acertou.
"""

import hmac
import logging
from urllib.parse import urlparse

from fastapi import Request

from estoque.domain.erros import ErroDominio

_log = logging.getLogger("estoque.csrf")

COOKIE = "csrf"
HEADER = "X-CSRF-Token"

METODOS_DE_ESCRITA = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Entrar e registrar acontecem ANTES de existir sessão: não há cookie de onde
# tirar o token. A proteção deles é outra — o rate limit deste mesmo módulo
# irmão, e o fato de que forjar um login alheio exige a senha.
ISENTOS = frozenset({"/api/auth/entrar", "/api/auth/registrar"})


def _mesma_origem(bruto: str, permitida: str) -> bool:
    """Compara esquema + host + porta. Comparar a string inteira falharia por
    barra final, e comparar só o host aceitaria `http` onde se espera `https`."""
    a, b = urlparse(bruto), urlparse(permitida)
    return (a.scheme, a.hostname, a.port) == (b.scheme, b.hostname, b.port)


def conferir(req: Request, origem_permitida: str) -> None:
    """Levanta `ErroDominio` se a requisição de escrita não provar a origem."""
    if req.method not in METODOS_DE_ESCRITA:
        return
    if req.url.path in ISENTOS:
        return

    # `Origin` vem em toda requisição de escrita feita por navegador moderno.
    # Ausente é aceito porque cliente de linha de comando não manda — e para
    # esse caso o token do cookie continua sendo exigido logo abaixo.
    origem = req.headers.get("origin")
    if origem and not _mesma_origem(origem, origem_permitida):
        _log.warning("origem recusada: %s", origem)
        raise ErroDominio("nao_autorizado", "a esta origem")

    do_cookie = req.cookies.get(COOKIE, "")
    do_header = req.headers.get(HEADER, "")
    # Mensagem UNICA para ausente e divergente: distinguir diria ao atacante se
    # ele acertou o formato, e nao ha' nada de util nessa distincao para quem
    # esta' usando o sistema de boa-fe.
    if not (do_cookie and do_header and hmac.compare_digest(do_cookie, do_header)):
        raise ErroDominio("nao_autorizado", "a esta operação: token de origem inválido")
