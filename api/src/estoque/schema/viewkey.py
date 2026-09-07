"""Os dois identificadores de view. ADR-0021.

A auditoria A-001 encontrou o ADR-0009 afirmando tres coisas incompativeis: id
gerado no servidor, chave por hash de conteudo, e revogacao. Hash de conteudo
NAO e' revogavel — recompor a mesma view regenera a mesma chave.

Resolucao: dois identificadores com papeis distintos.

    view_key   hash do schema canonicalizado, INTERNO
               responde "esta tela e' a mesma de antes?" — favorito, historico

    view_id    opaco, aleatorio, PUBLICO, na URL
               responde "qual o endereco desta tela?" — revogacao, auditoria
"""

import hashlib
import json
import secrets
from typing import Any

from estoque.schema.contrato import ViewSchema

BITS_VIEW_ID = 128


def canonicalizar(schema: ViewSchema) -> str:
    """Forma canonica para o hash ser estavel.

    Chaves ordenadas, valores nulos removidos, separadores fixos. A ORDEM DOS
    BLOCOS E' PRESERVADA de proposito: ordem e' significado — trocar dois blocos
    de lugar e' outra tela.
    """
    dados: dict[str, Any] = {
        "versao": schema.versao,
        "blocos": [
            {
                "tipo": b.tipo,
                "params": {k: v for k, v in sorted(b.params.items()) if v is not None},
            }
            for b in schema.blocos
        ],
    }
    # `titulo` NAO entra: e' cosmetico, e a mesma tela com titulo diferente
    # continua sendo a mesma tela.
    return json.dumps(dados, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def view_key(schema: ViewSchema) -> str:
    """Hash estavel entre execucoes e entre processos.

    Usa sha256, nao `hash()` do Python — que e' salgado por processo e daria
    chaves diferentes a cada reinicio.
    """
    return hashlib.sha256(canonicalizar(schema).encode("utf-8")).hexdigest()


def novo_view_id() -> str:
    """Endereco publico: opaco, nao enumeravel, nao derivavel do conteudo."""
    return secrets.token_urlsafe(BITS_VIEW_ID // 8)
