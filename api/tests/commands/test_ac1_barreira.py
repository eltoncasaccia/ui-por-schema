"""T-025 AC-1 — a barreira entre plano de render e plano de escrita. ADR-0002.

    A saida do modelo autoriza renderizar. Nunca autoriza escrever.

Este e' o teste que sustenta a tese do projeto. Se ele quebrar, a separacao
deixou de existir e nenhum outro teste vai perceber — todos os demais continuam
verdes num sistema onde o assistente virou agente de escrita.

Sao tres afirmacoes independentes, porque a barreira tem tres formas de cair:

  1. por IMPORT      — `assistant` alcanca `commands`, direto ou em N saltos
  2. por REFERENCIA  — um `CommandDef` do catalogo passa a carregar um callable
  3. por DIVERGENCIA — um comando executavel sem contrapartida declarada, ou
                       com `requires` mais fraco que o declarado

A primeira ja' e' verificada pelo `import-linter` (contrato 3). Esta duplicata
existe porque aquela vive num arquivo de configuracao: uma linha removida do
`.importlinter` some com a garantia sem falhar teste nenhum. Aqui a garantia esta
em codigo, e some junto com um teste vermelho.
"""

import collections.abc
import dataclasses
from typing import Any, get_args, get_origin, get_type_hints

import grimp
import pytest

# Importar o indice AQUI, e nao confiar em outro modulo de teste ter feito isso.
# ACHADO ao rodar este arquivo isolado: sem esta linha o registro de comandos fica
# vazio, a bijecao nao tem o que comparar e o teste passa por ausencia de dado —
# verde por nao ter olhado nada, que e' o pior modo de falha possivel para o
# teste que sustenta o ADR-0002.
import estoque.commands.indice  # noqa: F401
from estoque.commands import pipeline
from estoque.commands.tipos import Comando
from estoque.registry.definir import CommandDef
from estoque.registry.registry import todos

RAIZ = "estoque"
ASSISTENTE = "estoque.assistant"
ESCRITA = "estoque.commands"


@pytest.fixture(scope="module")
def grafo() -> grimp.ImportGraph:
    """`cache_dir=None` — sem cache, e a razão é de segurança, não de higiene.

    ACHADO ao sabotar este teste de propósito: o `.grimp_cache` continuou
    devolvendo o grafo COM a violação depois de o import ter sido removido. Se
    ele pode servir um grafo velho, pode servir o velho no outro sentido — o
    import proibido é acrescentado, o cache ainda não viu, e o teste que sustenta
    o ADR-0002 fica verde sobre uma barreira que já caiu.

    Um teste de segurança não pode depender de invalidação de cache estar certa.
    """
    return grimp.build_graph(RAIZ, cache_dir=None)


# ------------------------------------------------- 1. barreira por import
def test_ac1_assistente_nao_alcanca_os_comandos(grafo: grimp.ImportGraph) -> None:
    """`as_packages=True`: vale para os submodulos, e para caminho indireto.

    O import direto e' obvio e alguem barraria na revisao. O perigoso e'
    `assistant -> qualquer_util -> commands`, que ninguem enxerga lendo um
    arquivo de cada vez."""
    caminho = grafo.find_shortest_chain(importer=ASSISTENTE, imported=ESCRITA, as_packages=True)
    assert caminho is None, f"o assistente alcanca a escrita por {' -> '.join(caminho or ())}"


def test_ac1_a_busca_de_caminho_encontra_caminho_que_existe(grafo: grimp.ImportGraph) -> None:
    """O par negativo do teste acima, e a razao de ele valer alguma coisa.

    Um `find_shortest_chain` que devolvesse `None` para tudo — pacote com nome
    errado, grafo vazio — faria o teste anterior passar para sempre. `server`
    importa `commands` de verdade, pela borda HTTP; se este caminho tambem
    sumisse, o problema seria a ferramenta, nao a arquitetura."""
    caminho = grafo.find_shortest_chain(
        importer="estoque.server", imported=ESCRITA, as_packages=True
    )
    assert caminho is not None, "o grafo nao esta vendo import nenhum"
    assert caminho[0].startswith("estoque.server")


def test_ac1_o_grafo_tem_os_dois_pacotes(grafo: grimp.ImportGraph) -> None:
    """Pacote ausente daria ausencia de caminho — e um verde que nao significa
    nada. E' a mesma armadilha do `Could not find package` do lint-imports."""
    modulos = grafo.modules
    assert any(m.startswith(ASSISTENTE) for m in modulos)
    assert any(m.startswith(ESCRITA) for m in modulos)


# --------------------------------------------- 2. barreira por referencia
def _e_invocavel(anotacao: object) -> bool:
    """O tipo anotado e' algo que se CHAMA?

    Nao basta procurar a palavra "Callable" no texto da anotacao: os callables
    deste projeto sao Protocols nomeados (`Aplicador`, `LeitorDeEtag`), e o nome
    nao denuncia nada. A pergunta certa e' estrutural — o tipo define `__call__`?

    `type[X]` fica de fora de proposito: um campo que guarda uma CLASSE (o schema
    de validacao) nao e' um caminho de execucao, e recursar nele acusaria
    qualquer classe com metaclasse chamavel.
    """
    origem = get_origin(anotacao)
    if origem is collections.abc.Callable:
        return True
    if origem is type:
        return False
    if isinstance(anotacao, type) and "__call__" in vars(anotacao):
        return True
    return any(_e_invocavel(a) for a in get_args(anotacao))


def _campos_chamaveis(tipo: type) -> list[str]:
    """Campos cujo tipo declarado e' invocavel — o que transformaria uma
    descricao em algo que se executa."""
    dicas = get_type_hints(tipo)
    return [c.name for c in dataclasses.fields(tipo) if _e_invocavel(dicas.get(c.name))]


def test_ac1_command_def_nao_carrega_funcao() -> None:
    """`CommandDef` e' o que o catalogo publica para o modelo. Ele descreve um
    comando — endpoint, schema, `requires` — e nao tem o que chamar.

    Se um dia ganhasse um `aplicar`, a composicao do modelo passaria a segurar
    uma referencia executavel, e a barreira viraria uma convencao sobre nao
    chama-la."""
    assert _campos_chamaveis(CommandDef) == []


def test_ac1_o_detector_de_funcao_acha_funcao_onde_existe() -> None:
    """Par negativo: `Comando`, do plano de escrita, TEM callables. Se o detector
    nao os visse, o teste acima passaria por cegueira."""
    assert "aplicar" in _campos_chamaveis(Comando)


def test_ac1_nenhum_componente_expoe_execucao_no_viewmodel() -> None:
    """O que atravessa a rede e' o viewmodel. Um componente que colocasse um
    `CommandDef` ali entregaria a descricao do comando ao cliente junto com os
    dados — e o cliente e' payload nao-confiavel (ADR-0004)."""
    for comp in todos().values():
        vm = get_type_hints(comp.select).get("return")
        if vm is None or not isinstance(vm, type):
            continue
        for nome, tipo in get_type_hints(vm).items():
            assert "CommandDef" not in str(tipo), f"{comp.id}.{nome} carrega um CommandDef"


# --------------------------------------------- 3. barreira por divergencia
def _declarados() -> dict[str, CommandDef]:
    """Todo `CommandDef` publicado pelo catalogo, por nome de comando."""
    return {nome: cd for comp in todos().values() for nome, cd in comp.commands.items()}


def conferir_bijecao(
    declarados: dict[str, CommandDef], executaveis: dict[str, Comando]
) -> list[str]:
    """Falhas entre o que o catalogo promete e o que o pipeline executa.

    Extraida como funcao para que o teste negativo abaixo possa alimenta-la com
    um par divergente. Regra que nunca falhou nao e' evidencia de nada.
    """
    faltas = []
    for nome, cd in declarados.items():
        cmd = executaveis.get(nome)
        if cmd is None:
            faltas.append(f"{nome}: declarado no catalogo, sem comando executavel")
            continue
        base = cd.requires if isinstance(cd.requires, tuple) else (cd.requires,)
        if isinstance(cd.requires, tuple | str) and set(base) - set(cmd.requires):
            faltas.append(
                f"{nome}: o executavel exige {cmd.requires}, "
                f"menos que o declarado {base} — a permissao mais fraca e' a que vale"
            )
    return faltas


def test_ac1_todo_comando_declarado_tem_executavel_com_a_mesma_exigencia() -> None:
    """A partir da T-026 isto passa a ter conteudo. Hoje e' o guarda que impede o
    primeiro comando de nascer torto: declarar `requires` forte no catalogo e
    exigir menos na execucao seria filtrar a interface e liberar o endpoint."""
    assert conferir_bijecao(_declarados(), dict(pipeline.registrados())) == []


def test_ac1_a_conferencia_de_bijecao_reprova_o_que_deve_reprovar() -> None:
    """Duas divergencias construidas de proposito. Sem este teste, o de cima
    passaria por o catalogo ainda nao declarar comando nenhum."""
    from pydantic import BaseModel

    class Vazio(BaseModel):
        pass

    async def _nunca(entrada: Any, ctx: Any) -> Any:  # pragma: no cover
        raise AssertionError

    orfao = CommandDef(
        endpoint="/api/comandos/orfao",
        schema=Vazio,
        requires=("lote.liberar",),
        confirm=True,
        idempotent=False,
    )
    fraco = CommandDef(
        endpoint="/api/comandos/fraco",
        schema=Vazio,
        requires=("lote.liberar", "controlado.autorizar"),
        confirm=True,
        idempotent=False,
    )
    executavel_fraco = Comando(
        nome="fraco", requires=("lote.liberar",), schema=Vazio, aplicar=_nunca
    )

    faltas = conferir_bijecao({"orfao": orfao, "fraco": fraco}, {"fraco": executavel_fraco})
    assert len(faltas) == 2
    assert any("sem comando executavel" in f for f in faltas)
    assert any("menos que o declarado" in f for f in faltas)
