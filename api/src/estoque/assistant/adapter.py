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
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx

from estoque.assistant.prompt import montar
from estoque.assistant.trace import Trace

Modo = Literal["restrito", "livre"]

TIMEOUT_S = 30.0
MAX_TOKENS = 1024


@dataclass(frozen=True, slots=True)
class Resposta:
    bruto: str
    trace: Trace


class AdaptadorModelo(Protocol):
    async def compor(
        self, pergunta: str, catalogo: list[dict[str, Any]], modo: Modo = "restrito"
    ) -> Resposta: ...


# --------------------------------------------------------------------------
# JSON Schema derivado do catalogo — ADR-0024
# --------------------------------------------------------------------------
def json_schema_do_catalogo(catalogo: list[dict[str, Any]]) -> dict[str, Any]:
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
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["versao", "titulo", "blocos"],
        "properties": {
            "versao": {"type": "integer", "const": 1},
            "titulo": {"type": ["string", "null"]},
            "blocos": {
                "type": "array",
                "maxItems": 12,
                "items": {"anyOf": ramos} if ramos else {"type": "object"},
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


class ErroDeModelo(RuntimeError):
    """Falha do provedor. Erro tratado, nunca tela quebrada."""


# --------------------------------------------------------------------------
class AdaptadorOpenRouter:
    """API compativel com OpenAI. ADR-0023."""

    BASE = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, chave: str | None = None, modelo: str | None = None) -> None:
        self._chave = chave or os.environ.get("OPENROUTER_API_KEY", "")
        self._modelo = modelo or os.environ.get(
            "MODELO_ASSISTENTE", "anthropic/claude-haiku-4.5"
        )
        if not self._chave:
            msg = (
                "OPENROUTER_API_KEY ausente. O adaptador real NAO cai para o mock: "
                "foi assim que a POC v1 publicou numeros de um parser simulado "
                "sem perceber. Configure a chave ou use AdaptadorMock explicitamente."
            )
            raise ErroDeModelo(msg)

    async def compor(
        self, pergunta: str, catalogo: list[dict[str, Any]], modo: Modo = "restrito"
    ) -> Resposta:
        prompt = montar(pergunta, catalogo)
        trace = Trace(origem="openrouter", modelo=self._modelo, pergunta=pergunta, modo=modo)
        corpo: dict[str, Any] = {
            "model": self._modelo,
            "max_tokens": MAX_TOKENS,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
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

        inicio = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_S) as cli:
                r = await cli.post(
                    self.BASE,
                    headers={
                        "Authorization": f"Bearer {self._chave}",
                        "X-Title": "Estoque Bertoni",
                    },
                    json=corpo,
                )
                r.raise_for_status()
                dados = r.json()
        except httpx.HTTPError as e:
            trace.erro = f"{type(e).__name__}"
            trace.ms_total = int((time.perf_counter() - inicio) * 1000)
            return Resposta("", trace)

        trace.ms_total = int((time.perf_counter() - inicio) * 1000)
        trace.ms_ate_primeiro_token = trace.ms_total  # sem streaming no ciclo 1
        uso = dados.get("usage") or {}
        trace.tokens_entrada = int(uso.get("prompt_tokens", 0))
        trace.tokens_saida = int(uso.get("completion_tokens", 0))
        trace.provedor_efetivo = str(dados.get("provider") or "")
        conteudo = _primeiro_conteudo(dados)
        trace.resposta_bruta = conteudo
        return Resposta(conteudo, trace)


def _primeiro_conteudo(dados: dict[str, Any]) -> str:
    escolhas = dados.get("choices") or []
    if not escolhas:
        return ""
    msg = escolhas[0].get("message") or {}
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
        self, pergunta: str, catalogo: list[dict[str, Any]], modo: Modo = "restrito"
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
