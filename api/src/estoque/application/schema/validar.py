"""A fronteira de seguranca. ADR-0001, ADR-0004, ADR-0013.

Tres coisas que este modulo faz e que a v1 nao fazia:

1. Valida contra o CATALOGO DO ATOR, nao contra o registry global. Um componente
   registrado mas ausente do catalogo do ator e' rejeitado — e' o furo de
   permissao que passaria em todos os outros testes.
2. Trata o schema como PAYLOAD NAO-CONFIAVEL, venha do modelo ou nao. O cliente
   pode montar um schema a mao e enviar direto ao endpoint.
3. Registra os rejeitados no trace, com motivo.
"""

from dataclasses import dataclass, field

from pydantic import ValidationError

from estoque.application.registry import registry
from estoque.application.schema.contrato import MAX_PARAMS, Bloco, ViewSchema
from estoque.domain.erros import ErroDominio
from estoque.domain.identidade import Ator


@dataclass(slots=True)
class Rejeicao:
    tipo: str
    motivo: str


@dataclass(slots=True)
class ResultadoValidacao:
    schema: ViewSchema | None
    aceitos: list[str] = field(default_factory=list)
    rejeitados: list[Rejeicao] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Schema utilizavel. Composicao vazia conta — e' uma resposta."""
        return self.schema is not None

    @property
    def vazia(self) -> bool:
        return self.schema is not None and not self.aceitos


def validar_schema(bruto: object, ator: Ator) -> ResultadoValidacao:
    """Valida um schema contra o catalogo DESTE ator.

    Nunca levanta por schema hostil: devolve resultado com os rejeitados, para
    que o trace registre o que foi tentado. Levantar esconderia a evidencia.
    """
    try:
        schema = ViewSchema.model_validate(bruto)
    except ValidationError as e:
        return ResultadoValidacao(None, rejeitados=[Rejeicao("<schema>", _resumir(e))])

    permitidos = registry.ids_permitidos(ator)
    aceitos: list[str] = []
    rejeitados: list[Rejeicao] = []
    blocos_ok: list[Bloco] = []

    for bloco in schema.blocos:
        erro = _validar_bloco(bloco, ator, permitidos)
        if erro is not None:
            rejeitados.append(Rejeicao(bloco.tipo, erro))
            continue
        aceitos.append(bloco.tipo)
        blocos_ok.append(bloco)

    # Opcao de esclarecimento fora do catalogo DESTE ator cai como qualquer bloco
    # fora dele: oferecer o que a pessoa nao pode pedir conta que a porta existe.
    opcoes: list[str] = []
    for opcao in schema.esclarecer:
        if opcao not in permitidos:
            rejeitados.append(Rejeicao(opcao, "esclarecer: fora do catalogo do ator"))
        elif opcao not in opcoes:
            opcoes.append(opcao)

    # Composicao intencionalmente vazia e' VALIDA: o modelo olhou o catalogo e
    # concluiu que nada serve. Distinta de "tudo foi rejeitado", que e' falha.
    if not blocos_ok and not opcoes and rejeitados:
        return ResultadoValidacao(None, aceitos, rejeitados)

    limpo = ViewSchema(
        versao=1, titulo=schema.titulo, blocos=tuple(blocos_ok), esclarecer=tuple(opcoes)
    )
    return ResultadoValidacao(limpo, aceitos, rejeitados)


def _validar_bloco(bloco: Bloco, ator: Ator, permitidos: frozenset[str]) -> str | None:
    comp = registry.buscar(bloco.tipo)
    if comp is None:
        return "componente nao registrado"
    if bloco.tipo not in permitidos:
        # Registrado, mas fora do catalogo DESTE ator. O caso que a v1 nao tinha
        # como testar, porque o catalogo dela era global.
        return "componente fora do catalogo do ator"
    if len(bloco.params) > MAX_PARAMS:
        return "params demais"

    # Chaves perigosas antes de qualquer coisa tocar o modelo Pydantic.
    for chave in bloco.params:
        if chave.startswith("__") or chave in {"constructor", "prototype"}:
            return f"chave de param proibida: {chave}"

    fora = registry.valores_proibidos(comp, ator)
    for campo, proibidos in fora.items():
        valor = bloco.params.get(campo)
        if valor is not None and str(valor) in proibidos:
            # Ex.: Cleide pedindo metrica `valor_em_estoque` sem `custo.ler`.
            return f"valor nao permitido para {campo}"

    # `null` significa "nao informado". O modo estrito do provedor exige que
    # TODA propriedade esteja em `required` (ADR-0024), entao param opcional vai
    # ao modelo como anulavel — e ele devolve `null` quando nao quer usar.
    # Sem esta limpeza, `janela: null` batia em `literal_error` e derrubava uma
    # composicao correta.
    informados = {k: v for k, v in bloco.params.items() if v is not None}
    try:
        comp.params.model_validate(informados)
    except ValidationError as e:
        return _resumir(e)

    # ADR-0005: componente com commands e' unidade inteira, nunca composto.
    if comp.commands and len(bloco.params) >= 0 and comp.tamanho != "inteira":
        return "componente de escrita precisa ser bloco inteiro"
    return None


def _resumir(e: ValidationError) -> str:
    """Resumo do erro SEM eco do valor recebido.

    Ecoar o valor devolveria conteudo hostil para dentro do trace e, de la',
    potencialmente para o proximo prompt.
    """
    partes = [
        f"{'.'.join(str(x) for x in err['loc'])}: {err['type']}" for err in e.errors()[:4]
    ]
    return "; ".join(partes) or "schema invalido"


def revalidar_ou_falhar(bruto: object, ator: Ator) -> ViewSchema:
    """Usada na borda HTTP: schema recebido e' payload como qualquer outro."""
    r = validar_schema(bruto, ator)
    if r.schema is None:
        raise ErroDominio("invalido", "Composicao invalida.", detalhe_interno=r.rejeitados)
    return r.schema
