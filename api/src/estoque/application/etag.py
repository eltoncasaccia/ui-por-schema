"""Etag do estado atual de uma entidade — usado dos dois lados de `If-Match`.

`registry/` nao pode importar `commands/*.py` (contrato 2 do import-linter:
`registry -> sqlalchemy`, inclusive por caminho indireto, ja documentado pela
T-027 ao evitar `registry -> commands.pipeline`). Mas a LEITURA (`registry`)
precisa devolver o MESMO etag que a ESCRITA (`commands`) recalcula para
comparar com `If-Match` — sao o mesmo hash, ou toda escrita cai em `conflito`
mesmo sem concorrencia nenhuma (T-050).

Este modulo e' o lugar neutro: sem SQLAlchemy, sem FastAPI, so tipos de
`domain/`. Os dois lados importam daqui; nenhum dos dois reimplementa a
formula.
"""

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from estoque.domain.tipos import Lote


def etag_de_valores(valores: Mapping[str, Any]) -> str:
    """Derivado do conteudo, e nao de um contador — um contador exigiria coluna
    nova em toda tabela e um lugar a mais para esquecer de incrementar."""
    bruto = json.dumps(dict(sorted(valores.items())), separators=(",", ":"), default=str)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:32]


def etag_lote(lote: Lote) -> str:
    """A MESMA forma que `commands/lote.py:_etag_do_lote` usa."""
    return etag_de_valores(
        {
            "id": lote.id,
            "status": lote.status,
            "validade": lote.validade,
            "endereco": lote.endereco,
        }
    )


def etag_lote_e_saldo(lote: Lote, saldo: int) -> str:
    """A MESMA forma que `commands/saida.py:_etag_da_saida` e
    `commands/descarte.py:_etag_do_lote` usam — SEM `endereco`, COM `saldo`
    (T-051): a decisao de saida/descarte depende de quanto ainda existe, nao
    de onde o lote esta guardado."""
    return etag_de_valores(
        {"id": lote.id, "status": lote.status, "validade": lote.validade, "saldo": saldo}
    )


def etag_movimento_autorizacao(id: str, status: str, autorizador_id: str | None) -> str:
    """A MESMA forma que `commands/autorizacao.py:_etag_do_movimento` usa.

    Recebe VALORES, nao um `Movimento`: `RepoMovimento` nao tem `por_id`
    (so' `listar`/`do_lote`/`por_cliente`), e o comando le so' estas tres
    colunas por `sa.select()` direto — construir um `Movimento` fake so' para
    chamar esta funcao seria pior que passar os tres valores.
    """
    return etag_de_valores({"id": id, "status": status, "autorizador_id": autorizador_id})


def etag_movimento_estorno(
    id: str, status: str, lote_id: str, quantidade: int, *, estornado: bool
) -> str:
    """A MESMA forma que `commands/estorno.py:_etag_do_original` usa.
    `estornado` e' `domain.regras.estados.ja_estornado(mov, todos)` do lado do
    registry — a MESMA checagem que a tela ja' faz para `impedimento`
    (T-051) — e a contagem de `estorna_movimento_id` do lado do comando."""
    return etag_de_valores(
        {
            "id": id,
            "status": status,
            "lote_id": lote_id,
            "quantidade": quantidade,
            "estornado": estornado,
        }
    )
