"""Exporta o contrato do registry para o cliente gerar tipos. T-039, ADR-0017.

O ADR-0006 se orgulhava de não ter uma segunda lista. Com a API em Python e as
views em TypeScript, ela existe — e o que impede o apodrecimento que aquele ADR
descrevia é a bijeção verificada, não a disciplina.

O que sai daqui:

    ids            a união de literais `ComponentId` do cliente
    viewmodel      o JSON Schema do que `select` devolve — é o que atravessa a
                   rede, e é o que a view consome
    tamanho        o layout obedece ao componente, não ao modelo

O que NÃO sai: `load`, `requires`, `params`. São do servidor, e o cliente não
tem o que fazer com eles — mandar seria vazar a superfície de permissão para
dentro do bundle.
"""

import json
from typing import Any

import estoque.application.registry.indice  # noqa: F401  — registra os componentes
from estoque.application.registry.registry import todos


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


def contrato() -> dict[str, Any]:
    saida: list[dict[str, Any]] = []
    for comp in sorted(todos().values(), key=lambda c: c.id):
        # O modelo de retorno de `select`, que é o viewmodel.
        anot = comp.select.__annotations__.get("return")
        bruto = anot.model_json_schema() if anot is not None else {}
        esquema = _prefixar(_sem_titulo_de_propriedade(bruto), _pascal(comp.id))
        saida.append(
            {
                "id": comp.id,
                "label": comp.label,
                "tamanho": comp.tamanho,
                "viewmodel": esquema,
            }
        )
    return {"versao": 1, "componentes": saida}


def main() -> int:
    print(json.dumps(contrato(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
