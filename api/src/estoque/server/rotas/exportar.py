"""`/api/componentes/{id}/exportar` — o arquivo do que a tela mostraria (T-054).

Mesma leitura autorizada de `dados` (`deps.ler_componente`), com a mesma
identidade real. O arquivo nasce do viewmodel e nao do `load`: o que o
`select` nao deixou atravessar a rede tambem nao entra no arquivo (RN-A02,
ADR-0035).
"""

import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Cookie
from fastapi.responses import Response
from pydantic import BaseModel

from estoque.application.exportacao.porta import Cabecalho, Formato
from estoque.application.exportacao.tabelas import TABULADORES
from estoque.application.registry.definir import Pagina
from estoque.auditoria import registro as aud
from estoque.domain.erros import ErroDominio
from estoque.exportacao import EXPORTADORES
from estoque.server.deps import ator_ou_falhar, ler_componente, motor

rotas = APIRouter()

EMISSOR = "Bertoni Distribuidora Farmacêutica"
# Acima disto a exportacao e' recusada, nunca cortada (AC-8). Um arquivo com
# as primeiras 5.000 linhas de 7.000 parece completo, e ninguem confere.
TETO_DE_LINHAS = 5000


class PedidoExportar(BaseModel):
    params: dict[str, Any] = {}
    formato: Formato


def _nome_arquivo(base: str, quando: datetime, extensao: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    limpo = re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-") or "exportacao"
    return f"{limpo}-{quando:%Y-%m-%d}.{extensao}"


@rotas.post("/api/componentes/{componente_id}/exportar")
async def exportar(
    componente_id: str, corpo: PedidoExportar, sessao: str | None = Cookie(default=None)
) -> Response:
    tabular = TABULADORES.get(componente_id)
    async with motor.connect() as c:
        ator = await ator_ou_falhar(c, sessao)
        if tabular is None:
            # A mesma resposta de componente inexistente (ADR-0014).
            raise ErroDominio("nao_encontrado", "Registro nao encontrado.")
        # Uma pagina que cabe o teto inteiro: o `select` diz `tem_mais` se
        # houver mais linhas do que isso.
        pagina = Pagina(limite=TETO_DE_LINHAS, cursor=None)
        _, vm, _ = await ler_componente(c, ator, componente_id, corpo.params, pagina)

    tabela = tabular(vm)
    if getattr(vm, "tem_mais", False) or len(tabela.linhas) > TETO_DE_LINHAS:
        raise ErroDominio(
            "invalido",
            f"Mais de {TETO_DE_LINHAS} linhas. Estreite o filtro para exportar.",
        )

    agora = datetime.now(UTC)
    exportador = EXPORTADORES[corpo.formato]
    conteudo = exportador.gerar(tabela, Cabecalho(EMISSOR, ator.nome, agora))

    # RN-D05: levar os dados para fora da tela e' consulta, e das que mais
    # importam auditar.
    async with motor.begin() as c2:
        await aud.registrar(
            c2,
            ator_id=ator.id,
            acao="exportar",
            origem="tela",
            entidade=componente_id,
            valor_novo={
                "params": corpo.params,
                "formato": corpo.formato,
                "linhas": len(tabela.linhas),
            },
        )

    nome = _nome_arquivo(tabela.nome_base, agora, exportador.extensao)
    return Response(
        content=conteudo,
        media_type=exportador.tipo_midia,
        headers={
            "Content-Disposition": f'attachment; filename="{nome}"',
            # Arquivo com dado de estoque nao fica em cache intermediario.
            "Cache-Control": "no-store",
        },
    )
