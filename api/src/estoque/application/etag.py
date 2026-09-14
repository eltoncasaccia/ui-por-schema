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
    """A MESMA forma que `commands/lote.py:_etag_do_lote` e
    `commands/saida.py:_etag_da_saida` (a parte que nao inclui saldo) usam."""
    return etag_de_valores(
        {
            "id": lote.id,
            "status": lote.status,
            "validade": lote.validade,
            "endereco": lote.endereco,
        }
    )
