"""Exporta o contrato do registry para o cliente gerar tipos. T-039, ADR-0017.

O ADR-0006 se orgulhava de não ter uma segunda lista. Com a API em Python e as
views em TypeScript, ela existe — e o que impede o apodrecimento que aquele ADR
descrevia é a bijeção verificada, não a disciplina.

O que sai daqui:

    ids            a união de literais `ComponentId` do cliente
    viewmodel      o JSON Schema do que `select` devolve — é o que atravessa a
                   rede, e é o que a view consome
    tamanho        o layout obedece ao componente, não ao modelo
    filtros        T-055 — só nos oito componentes do escopo, só o campo de
                   `params` com enum (nunca identificador, por construção) e
                   os valores nomeados. É recorte, não permissão: a barra
                   oferece o valor, `RequiresPorValor` continua decidindo se o
                   ator pode pedi-lo (ADR-0004) — o filtro nunca é uma segunda
                   porta.

O que NÃO sai: `load`, `requires`, o resto de `params`. São do servidor, e o
cliente não tem o que fazer com eles — mandar seria vazar a superfície de
permissão para dentro do bundle.
"""

import json
from typing import Any

import estoque.application.registry.indice  # noqa: F401  — registra os componentes
from estoque.application.registry.registry import campos_filtraveis, todos

# T-055 §"Escopo". Só estes oito ganham `filtros` no contrato — os outros
# componentes podem até ter campo com enum em `Params`, mas a barra de filtro
# desta tarefa não cobre eles (corte de escopo, não limite técnico).
_COM_FILTRO = frozenset(
    {
        "lote_lista",
        "movimento_lista",
        "recebimento_lista",
        "fila_vencimento",
        "vencimento_grafico",
        "quarentena_fila",
        "auditoria_trilha",
        "relatorio_movimentacao",
    }
)
# `agrupar_por` é o eixo que a composição já fixou — refiltrar um relatório
# não é reagrupá-lo, é uma pergunta nova. Só este campo, deste componente.
_FIXADO_PELA_COMPOSICAO = {"relatorio_movimentacao": {"agrupar_por"}}


def _sem_titulo_de_propriedade(no: Any) -> Any:
    """Remove `title` de PROPRIEDADE, preservando o do modelo.

    O Pydantic põe `"title": "Escopo"` em cada campo, e o gerador de TypeScript
    ica cada propriedade titulada para um tipo nomeado no topo do arquivo. Como
    vários componentes têm campos com o mesmo nome — `rotulo`, `valor`, `ordem`
    — os tipos colidem e o arquivo não compila.
    """
    if isinstance(no, dict):
        limpo = {k: _sem_titulo_de_propriedade(v) for k, v in no.items()}
        props = limpo.get("properties")
        if isinstance(props, dict):
            for campo in props.values():
                if isinstance(campo, dict):
                    campo.pop("title", None)
        return limpo
    if isinstance(no, list):
        return [_sem_titulo_de_propriedade(x) for x in no]
    return no


def _prefixar(esquema: dict[str, Any], prefixo: str) -> dict[str, Any]:
    """Torna os nomes únicos entre componentes.

    As três classes de viewmodel se chamam `VM` no Python, e os modelos
    aninhados repetem nomes — `Faixa` existe em mais de um. Sem prefixo, o
    arquivo gerado tem três `interface VM` e não compila.
    """
    esquema = json.loads(json.dumps(esquema).replace("#/$defs/", f"#/$defs/{prefixo}"))
    esquema["title"] = f"VM{prefixo}"
    if defs := esquema.get("$defs"):
        esquema["$defs"] = {f"{prefixo}{k}": v for k, v in defs.items()}
        for nome, corpo in esquema["$defs"].items():
            if isinstance(corpo, dict):
                corpo["title"] = nome
    return esquema


def _pascal(id_componente: str) -> str:
    return "".join(p.capitalize() for p in id_componente.split("_"))


def _filtros(comp_id: str, params: type[Any]) -> dict[str, list[str]]:
    """T-055. Só enum, só os oito do escopo, nunca identificador — identificador
    não tem enum, então já sai de `campos_filtraveis` por construção."""
    if comp_id not in _COM_FILTRO:
        return {}
    excluidos = _FIXADO_PELA_COMPOSICAO.get(comp_id, set())
    return {
        campo: list(valores)
        for campo, valores in campos_filtraveis(params).items()
        if campo not in excluidos
    }


def contrato() -> dict[str, Any]:
    saida: list[dict[str, Any]] = []
    for comp in sorted(todos().values(), key=lambda c: c.id):
        # O modelo de retorno de `select`, que é o viewmodel.
        anot = comp.select.__annotations__.get("return")
        bruto = anot.model_json_schema() if anot is not None else {}
        esquema = _prefixar(_sem_titulo_de_propriedade(bruto), _pascal(comp.id))
        entrada: dict[str, Any] = {
            "id": comp.id,
            "label": comp.label,
            "tamanho": comp.tamanho,
            "viewmodel": esquema,
        }
        if filtros := _filtros(comp.id, comp.params):
            entrada["filtros"] = filtros
        saida.append(entrada)
    return {"versao": 1, "componentes": saida}


def main() -> int:
    print(json.dumps(contrato(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
