"""Motor de permissao. ADR-0004, ADR-0014.

Este e' o componente que DE FATO protege. Os outros dois momentos de
autorizacao — catalogo filtrado e revalidacao de schema — controlam o que e'
OFERECIDO. Este controla o que e' ACESSIVEL.

Papel nao e' nivel, e' conjunto: o Diretor NAO libera quarentena (RN-R02) e NAO
exclui movimento (CA-08). Qualquer atalho `if papel == 'diretor': return True`
quebraria as duas regras de uma vez.
"""

from collections.abc import Iterable

from estoque.domain.erros import ErroDominio, nao_autorizado, nao_encontrado
from estoque.domain.identidade import Ator, Permissao, UnidadeId


def pode_executar(ator: Ator, requeridas: Iterable[Permissao]) -> bool:
    return all(ator.pode(p) for p in requeridas)


def escopo_de(ator: Ator) -> frozenset[UnidadeId]:
    """Ator inativo tem escopo vazio — RN-A06, com efeito imediato."""
    return ator.unidades if ator.ativo else frozenset()


def autorizar_ou_falhar(ator: Ator, requeridas: Iterable[Permissao], alvo: str = "") -> None:
    if not ator.ativo:
        raise nao_autorizado(f"a {alvo}" if alvo else "a este recurso")
    faltando = [p for p in requeridas if not ator.pode(p)]
    if faltando:
        # `nao_autorizado` porque a operacao e' um recurso DECLARADO que o ator
        # ja' sabe que existe. Registro individual e' outro caso — ver abaixo.
        raise nao_autorizado(f"a {alvo}" if alvo else "a esta operacao")


def autorizar_unidade_ou_falhar(ator: Ator, unidade: UnidadeId) -> None:
    """ADR-0014: escopo DECLARADO nega explicitamente.

    Odair pedindo Ribeirao Preto recebe negativa clara. A existencia da unidade
    nao e' segredo — e' a propria empresa dele. Devolver vazio ensinaria que
    Ribeirao nao tem estoque, o que e' falso e pior.
    """
    if unidade not in escopo_de(ator):
        raise nao_autorizado(f"a unidade {unidade}")


def registro_ou_falhar[T](registro: T | None) -> T:
    """ADR-0014: registro INDIVIDUAL nega de forma indistinguivel de inexistente.

    Distinguir "existe mas voce nao pode" de "nao existe" e' um oraculo de
    enumeracao: iterando ids, descobre-se quais existem.
    """
    if registro is None:
        raise nao_encontrado()
    return registro


def autorizar_params_ou_falhar(
    proibidos: dict[str, set[str]], params: dict[str, object]
) -> None:
    """Terceiro momento do ADR-0004, para `RequiresPorValor`.

    ACHADO EM TESTE PONTA A PONTA: o endpoint de dados conferia apenas as
    permissoes BASE do componente. Cleide passava em `lote.ler` e o `load` de
    `estoque_indicador` rodava com `metrica=valor_em_estoque` — um schema
    forjado enviado direto ao endpoint, sem passar pelo modelo, exatamente o
    caso do CS-01.

    O dano foi contido por acidente feliz: a porta de dados remove o custo de
    quem nao tem `custo.ler`, entao o total voltou zerado. Mas a requisicao NAO
    foi recusada, e defesa em profundidade que salva por acaso e' uma camada que
    falhou.
    """
    for campo, valores in proibidos.items():
        v = params.get(campo)
        if v is not None and str(v) in valores:
            raise nao_autorizado("a este recorte")


def autorizar_unidade_do_param(ator: Ator, unidade: object) -> None:
    """ADR-0014: escopo DECLARADO nega explicitamente.

    ACHADO NO MESMO TESTE: Odair pedindo `unidade_id=cd-matriz` recebia lista
    VAZIA, porque o repositorio apenas intersectava com o escopo dele. Vazio
    ensina um fato falso — que a Matriz nao tem nada vencendo — e o ADR-0014
    rejeita isso explicitamente. A unidade existe e Odair sabe que existe: a
    negativa pode e deve ser clara.
    """
    if unidade is None:
        return
    if str(unidade) not in escopo_de(ator):
        raise nao_autorizado(f"a unidade {unidade}")


def mesma_pessoa(a: str, b: str | None) -> bool:
    """Separacao de funcoes — RN-A04, RN-C01, RN-I01. Quem conta nao aprova."""
    return b is not None and a == b


def negar_se_mesma_pessoa(autor_id: str, autorizador_id: str | None) -> None:
    if mesma_pessoa(autor_id, autorizador_id):
        raise ErroDominio(
            "invalido",
            "Autor e autorizador precisam ser pessoas diferentes.",
        )
