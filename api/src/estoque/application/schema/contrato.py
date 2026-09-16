"""O que o modelo produz. CONTRATOS secao 7, ADR-0001.

O schema NAO TEM ONDE CARREGAR CODIGO: nao existe campo para markup, estilo,
layout livre, valor literal de dado ou expressao. Isso e' propriedade da
estrutura de dados, nao promessa de prompt.

Acrescentar qualquer um desses campos exige revogar o ADR-0001.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Limites contra schema hostil (T-013 AC-6): rejeitar por limite, sem estourar
# a pilha nem consumir memoria.
MAX_BLOCOS = 12
MAX_PARAMS = 12
MAX_ESCLARECER = 4


class Bloco(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tipo: str
    params: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ViewSchema(BaseModel):
    """A composicao inteira: ~60 tokens para uma tela de tres componentes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    versao: Literal[1]
    titulo: str | None = None
    # `blocos` PODE ser vazio, e isso é uma resposta — não uma falha.
    #
    # O prompt instrui: "se a pergunta não puder ser respondida com o catálogo,
    # devolva blocos vazio". Exigir min_length=1 aqui punia o modelo por
    # obedecer, e a suíte de avaliação registrava os 6 casos negativos como
    # schema inválido — quando "não compor" era exatamente o certo.
    blocos: tuple[Bloco, ...] = Field(max_length=MAX_BLOCOS)
    # Pergunta vaga ("quero registrar") que cabe em mais de um componente: o
    # modelo devolve os IDS candidatos em vez de escolher por conta propria.
    # Ids, nunca texto — o que a pessoa le e' o `label` do registry, escrito por
    # nos. Um campo de pergunta livre seria o `titulo` do A-42 outra vez.
    esclarecer: tuple[str, ...] = Field(default=(), max_length=MAX_ESCLARECER)
