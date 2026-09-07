"""Identidade e permissao. CONTRATOS secao 1.

Nenhuma funcao deste sistema recebe `Ator` opcional: se a assinatura permite
`None`, alguem vai passar `None`.
"""

from dataclasses import dataclass
from typing import Literal

PapelId = Literal["diretor", "rt", "gerente", "conferente", "comprador", "auditoria"]

UnidadeId = Literal["cd-matriz", "cd-refrigerado", "filial-uberlandia"]

UNIDADES: frozenset[UnidadeId] = frozenset({"cd-matriz", "cd-refrigerado", "filial-uberlandia"})

Permissao = Literal[
    # leitura
    "produto.ler",
    "lote.ler",
    "movimento.ler",
    "recebimento.ler",
    "temperatura.ler",
    "auditoria.ler",
    "auditoria.rastrear",
    "usuario.ler",
    "custo.ler",
    # escrita
    "lote.liberar",
    "lote.status",
    "movimento.criar",
    "movimento.estornar",
    "movimento.descartar",
    "recebimento.criar",
    "controlado.movimentar",
    "controlado.autorizar",
    "usuario.gerenciar",
]

PERMISSOES: frozenset[Permissao] = frozenset(
    {
        "produto.ler",
        "lote.ler",
        "movimento.ler",
        "recebimento.ler",
        "temperatura.ler",
        "auditoria.ler",
        "auditoria.rastrear",
        "usuario.ler",
        "custo.ler",
        "lote.liberar",
        "lote.status",
        "movimento.criar",
        "movimento.estornar",
        "movimento.descartar",
        "recebimento.criar",
        "controlado.movimentar",
        "controlado.autorizar",
        "usuario.gerenciar",
    }
)

# Matriz do documento 02, secao 6. Fonte unica: o seed deriva daqui.
PERMISSOES_POR_PAPEL: dict[PapelId, frozenset[Permissao]] = {
    "diretor": frozenset(
        {
            "produto.ler",
            "lote.ler",
            "movimento.ler",
            "recebimento.ler",
            "temperatura.ler",
            "auditoria.ler",
            "auditoria.rastrear",
            "usuario.ler",
            "custo.ler",
            "movimento.estornar",
            "movimento.descartar",
            "usuario.gerenciar",
        }
    ),
    # RT nao tem custo.ler (RN-A02) e e' a UNICA com lote.liberar (RN-R02).
    "rt": frozenset(
        {
            "produto.ler",
            "lote.ler",
            "movimento.ler",
            "recebimento.ler",
            "temperatura.ler",
            "auditoria.ler",
            "auditoria.rastrear",
            "lote.liberar",
            "lote.status",
            "movimento.estornar",
            "movimento.descartar",
            "controlado.autorizar",
        }
    ),
    "gerente": frozenset(
        {
            "produto.ler",
            "lote.ler",
            "movimento.ler",
            "recebimento.ler",
            "temperatura.ler",
            "movimento.criar",
            "movimento.descartar",
            "movimento.estornar",
            "recebimento.criar",
        }
    ),
    "conferente": frozenset(
        {
            "produto.ler",
            "lote.ler",
            "movimento.ler",
            "recebimento.ler",
            "temperatura.ler",
            "movimento.criar",
            "recebimento.criar",
            "controlado.movimentar",
        }
    ),
    "comprador": frozenset({"produto.ler", "lote.ler", "custo.ler"}),
    "auditoria": frozenset(
        {
            "produto.ler",
            "lote.ler",
            "movimento.ler",
            "recebimento.ler",
            "temperatura.ler",
            "auditoria.ler",
            "auditoria.rastrear",
            "usuario.ler",
            "custo.ler",
        }
    ),
}


@dataclass(frozen=True, slots=True)
class Ator:
    """Quem esta fazendo a requisicao.

    `papel is None` e' o estado do recem-cadastrado: catalogo vazio, nenhum
    `load` autorizado, nenhuma tela. Ver ADR-0019 — cadastro nao concede papel,
    senao seria escalacao de privilegio por formulario.
    """

    id: str
    nome: str
    papel: PapelId | None
    unidades: frozenset[UnidadeId]
    permissoes: frozenset[Permissao]
    ativo: bool

    def pode(self, permissao: Permissao) -> bool:
        return self.ativo and permissao in self.permissoes
