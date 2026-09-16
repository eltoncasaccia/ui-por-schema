"""Adaptadores de modelo. ADR-0023, ADR-0024.

Tres implementacoes, e a existencia das tres e' o que faz esta abstracao valer:
abstracao com um implementador e' decoracao; com tres, e' fronteira.

    AdaptadorOpenRouter   producao e medicao — API compativel com OpenAI
    AdaptadorAnthropic    nativo, quando houver ANTHROPIC_API_KEY
    AdaptadorMock         SO' testes, determinista, identificado no trace

REGRA QUE NAO SE NEGOCIA: sem chave configurada, o adaptador real FALHA. Nunca
cai para o mock em silencio. Esse foi o erro central da POC v1 — todos os numeros
publicados vieram de um parser simulado, e ninguem percebeu. Um fallback
silencioso repetiria isso, desta vez com numeros que parecem reais.
"""

import json
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from estoque.assistant.prompt import montar
from estoque.assistant.trace import Modo, Origem, Trace

TIMEOUT_S = 30.0
MAX_TOKENS = 1024


@dataclass(frozen=True, slots=True)
class Resposta:
    bruto: str
    trace: Trace


class AdaptadorModelo(Protocol):
    async def compor(
        self, pergunta: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo = "restrito"
    ) -> Resposta: ...


# --------------------------------------------------------------------------
# JSON Schema derivado do catalogo — ADR-0024
# --------------------------------------------------------------------------
def json_schema_do_catalogo(catalogo: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Constroi o schema de saida restrito para ESTE ator.

    Uniao discriminada por `tipo`: cada componente traz os SEUS params, com os
    valores de enum que o ator nao pode ja' removidos. O modelo fica incapaz de
    nomear um componente fora do catalogo dele E de escolher um valor proibido.

    ACHADO EM USO (ADR-0024 previu, e aconteceu): a primeira versao declarava
    apenas `params: {"type": "object"}`. O modelo OBEDECE O SCHEMA e ignora a
    prosa do prompt — entao emitia `params: {}` e todo componente com param
    obrigatorio era rejeitado. O catalogo e' serializado duas vezes, como texto
    e como JSON Schema, e as duas divergiram.

    Isto NAO substitui a validacao no servidor (ADR-0004): o cliente ainda pode
    forjar um schema e enviar direto ao endpoint, onde decodificacao restrita
    nao existe.
    """
    ramos: list[dict[str, Any]] = []
    for c in catalogo:
        ramos.append(
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["tipo", "params"],
                "properties": {
                    "tipo": {"const": c["id"]},
                    "params": _schema_de_params(c["params"]),
                },
            }
        )
    ids = [c["id"] for c in catalogo]
    return {
        "type": "object",
        "additionalProperties": False,
        # `esclarecer` e' obrigatorio aqui porque `strict` exige toda propriedade
        # em `required`; vazio e' o caso comum.
        "required": ["versao", "titulo", "blocos", "esclarecer"],
        "properties": {
            "versao": {"type": "integer", "const": 1},
            "titulo": {"type": ["string", "null"]},
            "blocos": {
                "type": "array",
                "maxItems": 12,
                "items": {"anyOf": ramos} if ramos else {"type": "object"},
            },
            "esclarecer": {
                "type": "array",
                "maxItems": 4,
                "items": {"enum": ids} if ids else {"type": "string"},
            },
        },
    }


def _schema_de_params(descricao: dict[str, Any]) -> dict[str, Any]:
    """Traduz a descricao de params do catalogo para JSON Schema estrito.

    Modo estrito exige que TODA propriedade esteja em `required`. Param
    opcional vira anulavel — `["string","null"]` — em vez de ausente, senao o
    provedor recusa o schema inteiro.
    """
    props: dict[str, Any] = {}
    for nome, info in descricao.items():
        valores = info.get("valores")
        obrigatorio = bool(info.get("obrigatorio"))
        if valores:
            props[nome] = (
                {"enum": list(valores)}
                if obrigatorio
                else {"anyOf": [{"enum": list(valores)}, {"type": "null"}]}
            )
        else:
            tipo = _tipo_json(str(info.get("tipo", "str")))
            props[nome] = {"type": tipo if obrigatorio else [tipo, "null"]}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(props),
        "properties": props,
    }


def _tipo_json(tipo_python: str) -> str:
    if "int" in tipo_python:
        return "integer"
    if "float" in tipo_python:
        return "number"
    if "bool" in tipo_python:
        return "boolean"
    return "string"


def ferramenta_do_catalogo(catalogo: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """O MESMO schema, embrulhado como ferramenta.

    Tool calling tem suporte mais amplo que `response_format: json_schema` —
    modelos abertos servidos por Ollama, vLLM ou Groq costumam ter um e nao o
    outro. Como a restricao e' identica, o resultado e' equivalente; muda so' o
    envelope.

    Derivado da MESMA funcao do modo restrito, de proposito: duas construcoes
    do mesmo schema divergiriam, e a divergencia so' apareceria em producao.
    """
    return {
        "type": "function",
        "function": {
            "name": "compor_tela",
            "description": "Compõe a tela escolhendo componentes do catálogo.",
            "parameters": json_schema_do_catalogo(catalogo),
        },
    }


class ErroDeModelo(RuntimeError):
    """Falha do provedor. Erro tratado, nunca tela quebrada."""


# --------------------------------------------------------------------------
class AdaptadorOpenRouter:
    """API compativel com OpenAI. ADR-0023."""

    BASE = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        chave: str | None = None,
        modelo: str | None = None,
        base: str | None = None,
        origem: Origem = "openrouter",
        nome_da_chave: str = "OPENROUTER_API_KEY",
    ) -> None:
        self._chave = chave or os.environ.get(nome_da_chave, "")
        self._modelo = modelo or os.environ.get(
            "MODELO_ASSISTENTE", "anthropic/claude-haiku-4.5"
        )
        self._base = base or self.BASE
        self._origem: Origem = origem
        self._nome_da_chave = nome_da_chave
        if not self._chave:
            msg = (
                f"{nome_da_chave} ausente. O adaptador real NAO cai para o mock: "
                "foi assim que a POC v1 publicou numeros de um parser simulado "
                "sem perceber. Configure a chave ou use AdaptadorMock explicitamente."
            )
            raise ErroDeModelo(msg)

    async def compor(
        self, pergunta: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo = "restrito"
    ) -> Resposta:
        prompt = montar(pergunta, catalogo)
        trace = Trace(
            origem=self._origem,
            modelo=self._modelo,
            pergunta=pergunta,
            modo=modo,
            modo_efetivo=modo,
        )
        inicio = time.perf_counter()

        # Nem todo provedor aceita `json_schema` estrito. Em vez de exigir, o
        # adaptador tenta e CAI para a proxima forma — registrando qual valeu.
        # Cair em silencio atribuiria o numero medido ao experimento errado.
        for tentativa in _cadeia(modo):
            corpo = self._corpo(prompt, catalogo, tentativa)
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT_S) as cli:
                    r = await cli.post(
                        self._base,
                        headers={
                            "Authorization": f"Bearer {self._chave}",
                            "X-Title": "Estoque Bertoni",
                        },
                        json=corpo,
                    )
                if r.status_code == 400 and tentativa != "livre":
                    # 400 aqui e' quase sempre "nao suporto este envelope".
                    trace.rejeitados.append((tentativa, "provedor recusou o envelope"))
                    continue
                r.raise_for_status()
                dados = r.json()
            except httpx.HTTPError as e:
                trace.erro = type(e).__name__
                trace.ms_total = int((time.perf_counter() - inicio) * 1000)
                return Resposta("", trace)

            trace.modo_efetivo = tentativa
            trace.ms_total = int((time.perf_counter() - inicio) * 1000)
            trace.ms_ate_primeiro_token = trace.ms_total  # sem streaming no ciclo 1
            uso = dados.get("usage") or {}
            trace.tokens_entrada = int(uso.get("prompt_tokens", 0))
            trace.tokens_saida = int(uso.get("completion_tokens", 0))
            # Custo RELATADO pelo provedor. Nao estimamos por tabela: tabela
            # envelhece, e o roteador pode servir por caminhos de preco distinto.
            if uso.get("cost") is not None:
                trace.custo_usd = float(uso["cost"])
            trace.provedor_efetivo = str(dados.get("provider") or "")
            conteudo = _primeiro_conteudo(dados)
            trace.resposta_bruta = conteudo
            return Resposta(conteudo, trace)

        trace.erro = "nenhum modo de saída aceito pelo provedor"
        trace.ms_total = int((time.perf_counter() - inicio) * 1000)
        return Resposta("", trace)

    def _corpo(
        self, prompt: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo
    ) -> dict[str, Any]:
        corpo: dict[str, Any] = {
            "model": self._modelo,
            "max_tokens": MAX_TOKENS,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
            # Pede o custo de volta; provedor que ignora simplesmente nao manda.
            "usage": {"include": True},
        }
        if modo == "restrito":
            corpo["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "view_schema",
                    "strict": True,
                    "schema": json_schema_do_catalogo(catalogo),
                },
            }
        elif modo == "ferramenta":
            corpo["tools"] = [ferramenta_do_catalogo(catalogo)]
            corpo["tool_choice"] = {
                "type": "function",
                "function": {"name": "compor_tela"},
            }
        return corpo


def _cadeia(modo: Modo) -> tuple[Modo, ...]:
    """Ordem de tentativa. `livre` fecha a fila porque funciona em toda parte."""
    if modo == "restrito":
        return ("restrito", "ferramenta", "livre")
    if modo == "ferramenta":
        return ("ferramenta", "livre")
    return ("livre",)


def _primeiro_conteudo(dados: dict[str, Any]) -> str:
    """Le a resposta nas duas formas: conteudo direto ou argumento da ferramenta."""
    escolhas = dados.get("choices") or []
    if not escolhas:
        return ""
    msg = escolhas[0].get("message") or {}
    chamadas = msg.get("tool_calls") or []
    if chamadas:
        return str((chamadas[0].get("function") or {}).get("arguments") or "")
    return str(msg.get("content") or "")


# --------------------------------------------------------------------------
class AdaptadorMock:
    """Determinista, para teste. SEMPRE identificado no trace como `mock`.

    Nenhum numero produzido por este adaptador entra em relatorio: a suite de
    avaliacao rejeita execucao com origem `mock` (T-032 AC-7).
    """

    def __init__(self, respostas: dict[str, dict[str, Any]] | None = None) -> None:
        self._respostas = respostas or {}

    async def compor(
        self, pergunta: str, catalogo: Sequence[Mapping[str, Any]], modo: Modo = "restrito"
    ) -> Resposta:
        trace = Trace(origem="mock", modelo="mock", pergunta=pergunta, modo=modo)
        chave = pergunta.strip().lower()
        resposta = self._respostas.get(chave)
        if resposta is None and catalogo:
            resposta = {
                "versao": 1,
                "blocos": [{"tipo": catalogo[0]["id"], "params": {}}],
            }
        bruto = json.dumps(resposta or {"versao": 1, "blocos": []}, ensure_ascii=False)
        trace.resposta_bruta = bruto
        return Resposta(bruto, trace)


def extrair_json(bruto: str) -> object:
    """Extrai o objeto JSON da resposta.

    Em modo restrito o corpo ja' vem limpo. Em modo livre o modelo pode envolver
    em cerca de codigo ou escrever antes e depois — e a frequencia com que isso
    acontece E' PARTE DA MEDICAO (ADR-0024). Por isso a extracao e' tolerante,
    mas o trace registra que precisou intervir.
    """
    texto = bruto.strip()
    if texto.startswith("```"):
        texto = texto.split("```")[1] if "```" in texto[3:] else texto[3:]
        texto = texto.removeprefix("json").strip()
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        msg = "resposta sem objeto JSON"
        raise ValueError(msg)
    return json.loads(texto[inicio : fim + 1])
