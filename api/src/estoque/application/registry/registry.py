"""Registro em runtime e catalogo derivado por ator. ADR-0003, ADR-0012.

A v1 tinha o catalogo como constante no cliente — a mesma lista para todo mundo.
Aqui ele e' gerado no servidor, por requisicao, filtrado pelas permissoes e
unidades do ator. Cleide nao tem `custo.ler`, entao nenhum componente que exponha
custo entra no catalogo dela: o modelo nao consegue nem propor.

Isso e' HIGIENE, nao garantia. A garantia e' a autorizacao em cada `load` e cada
`command` (ADR-0004). Passar nos testes daqui nao autoriza afrouxar aquilo.
"""

from collections.abc import Iterator, Mapping
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin

from estoque.application.registry.definir import ComponentDef, RequiresPorValor, permissoes_base
from estoque.domain.identidade import Ator, Permissao

TETO_CATALOGO = 25  # ADR-0011. Acima disso, recuperacao de catalogo vira obrigatoria.

_REGISTRO: dict[str, ComponentDef] = {}


def registrar(componente: ComponentDef) -> ComponentDef:
    if componente.id in _REGISTRO:
        msg = f"id de componente duplicado: {componente.id!r}"
        raise ValueError(msg)
    _REGISTRO[componente.id] = componente
    return componente


def limpar_registro() -> None:
    """So' para teste. Producao registra uma vez, na importacao do indice."""
    _REGISTRO.clear()


def todos() -> Mapping[str, ComponentDef]:
    return dict(_REGISTRO)


def buscar(id_componente: str) -> ComponentDef | None:
    return _REGISTRO.get(id_componente)


def _tem_todas(ator: Ator, permissoes: tuple[Permissao, ...]) -> bool:
    return all(ator.pode(p) for p in permissoes)


def _valores_de_enum(modelo: type[Any], campo: str) -> tuple[str, ...]:
    """Extrai os literais de um campo, desembrulhando `X | None`.

    `get_args` sobre `UnidadeId | None` devolve `(Literal[...], NoneType)`, nao
    os valores. Sem descer um nivel, o enum vazava a representacao do tipo para
    dentro do JSON Schema que vai ao modelo — e um enum invalido faz o provedor
    recusar a requisicao inteira.
    """
    info = modelo.model_fields.get(campo)
    if info is None or info.annotation is None:
        return ()
    return _literais(info.annotation)


def _literais(anotacao: Any) -> tuple[str, ...]:
    origem = get_origin(anotacao)
    if origem is Literal:
        return tuple(str(v) for v in get_args(anotacao))
    if origem in (Union, UnionType):
        saida: list[str] = []
        for parte in get_args(anotacao):
            if parte is type(None):
                continue
            saida.extend(_literais(parte))
        return tuple(saida)
    return ()


class EntradaCatalogo(dict[str, Any]):
    """Serializacao de um componente para o prompt."""


def catalogo_de(ator: Ator) -> list[EntradaCatalogo]:
    """O vocabulario que ESTE ator entrega ao modelo.

    Duas filtragens acontecem:
      1. componente inteiro sai, se faltar permissao base;
      2. VALORES de enum saem, quando `requires` depende do valor (achado A-05).
    """
    saida: list[EntradaCatalogo] = []
    for comp in sorted(_REGISTRO.values(), key=lambda c: c.id):
        if not _tem_todas(ator, permissoes_base(comp.requires)):
            continue
        entrada = EntradaCatalogo(
            id=comp.id,
            label=comp.label,
            description=comp.description,
            examples=list(comp.examples),
            params=_params_filtrados(comp, ator),
        )
        saida.append(entrada)
    return saida


def _params_filtrados(comp: ComponentDef, ator: Ator) -> dict[str, Any]:
    """Descreve os params para o modelo, removendo valores de enum proibidos."""
    descricao: dict[str, Any] = {}
    proibidos: dict[str, set[str]] = {}
    if isinstance(comp.requires, RequiresPorValor):
        for campo, mapa in comp.requires.por_valor.items():
            for valor, exigidas in mapa.items():
                if not _tem_todas(ator, exigidas):
                    proibidos.setdefault(campo, set()).add(valor)

    for nome, info in comp.params.model_fields.items():
        valores = _valores_de_enum(comp.params, nome)
        if valores:
            permitidos = [v for v in valores if v not in proibidos.get(nome, set())]
            descricao[nome] = {
                "valores": permitidos,
                "obrigatorio": info.is_required(),
            }
        else:
            descricao[nome] = {
                "tipo": _nome_do_tipo(info.annotation),
                "obrigatorio": info.is_required(),
            }
    return descricao


def _nome_do_tipo(anotacao: Any) -> str:
    return getattr(anotacao, "__name__", str(anotacao))


def ids_permitidos(ator: Ator) -> frozenset[str]:
    """Conjunto usado pela revalidacao de schema no servidor (ADR-0004)."""
    return frozenset(e["id"] for e in catalogo_de(ator))


def valores_proibidos(comp: ComponentDef, ator: Ator) -> dict[str, set[str]]:
    if not isinstance(comp.requires, RequiresPorValor):
        return {}
    fora: dict[str, set[str]] = {}
    for campo, mapa in comp.requires.por_valor.items():
        for valor, exigidas in mapa.items():
            if not _tem_todas(ator, exigidas):
                fora.setdefault(campo, set()).add(valor)
    return fora


def iter_componentes() -> Iterator[ComponentDef]:
    yield from _REGISTRO.values()


# Risco R-5 (PRD §9): um campo de params sem enum deixa o modelo INVENTAR o
# recorte — "clientes grandes" em vez de um valor nomeado — e a resposta
# alarga em silencio, sem erro em lugar nenhum. Estes dois padroes sao FORA
# do risco por natureza, nao por lista de excecao caso a caso:
# - identificador (`lote_id`, `produto_id`, `ean`, ...): busca exata, nunca
#   recorte de faixa;
# - `de`/`ate`: fronteira de um intervalo continuo (data), onde "valor
#   nomeado" nao faz sentido — o enum aqui e' o PRESET (`periodo`, `janela`),
#   que ja existe ao lado.
def _e_identificador_ou_intervalo(campo: str) -> bool:
    return campo.endswith("_id") or campo in {"ean", "de", "ate"}


def campos_filtraveis(params: type[Any]) -> dict[str, tuple[str, ...]]:
    """Campo de `params` com enum -> os valores. É o mesmo campo que o T-055
    expõe como filtro: identificador nunca tem enum, então nunca aparece aqui
    por construção — não precisa de uma segunda lista de exclusão."""
    return {
        campo: valores
        for campo in params.model_fields
        if (valores := _valores_de_enum(params, campo))
    }


def campos_sem_enum(componentes: Mapping[str, ComponentDef]) -> dict[str, tuple[str, ...]]:
    """Todo campo de `params` que NAO e' enum e NAO e' identificador/intervalo.

    Vazio e' o estado correto. Um campo aqui e' um recorte que o modelo pode
    preencher com texto livre — a auditoria do AC-5 da T-032 falha para
    qualquer entrada, forcando decisao explicita (virar enum, ou entrar na
    lista de exececao acima com o motivo) em vez de silencio.
    """
    achados: dict[str, tuple[str, ...]] = {}
    for comp_id, comp in componentes.items():
        filtraveis = campos_filtraveis(comp.params)
        suspeitos = tuple(
            campo
            for campo in comp.params.model_fields
            if campo not in filtraveis and not _e_identificador_ou_intervalo(campo)
        )
        if suspeitos:
            achados[comp_id] = suspeitos
    return achados
