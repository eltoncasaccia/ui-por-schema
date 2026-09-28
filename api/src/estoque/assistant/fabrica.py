"""Escolhe o adaptador por CONFIGURAÇÃO, não por código.

O `AdaptadorModelo` já era uma porta, mas o servidor instanciava OpenRouter
direto — a abstração existia e a fiação a ignorava. Trocar de provedor exigia
editar código, que é exatamente o que uma porta deveria evitar.

    PROVEDOR=openrouter   roteador multi-modelo (padrão)
    PROVEDOR=compativel   QUALQUER API compatível com OpenAI, via LLM_BASE_URL
                          — Ollama local, vLLM, Groq, Together, Azure, LM Studio
    PROVEDOR=anthropic    SDK nativo da Anthropic
    PROVEDOR=mock         determinístico, só teste

`compativel` é o que dá agnosticismo de verdade: um adaptador e uma URL cobrem
a maior parte do mercado, inclusive modelo aberto rodando na própria máquina.

O que NÃO muda com o provedor: o catálogo filtrado por ator, a validação do
schema contra esse catálogo, e a autorização em cada carga. O modelo é a peça
mais trocável do sistema — de propósito.
"""

import os

from estoque.assistant.adapter import (
    AdaptadorMock,
    AdaptadorModelo,
    AdaptadorOpenRouter,
    ErroDeModelo,
)

PADRAO_POR_PROVEDOR: dict[str, tuple[str, str, str]] = {
    # provedor -> (url base, variavel da chave, modelo padrao)
    "openrouter": (
        "https://openrouter.ai/api/v1/chat/completions",
        "OPENROUTER_API_KEY",
        "anthropic/claude-haiku-4.5",
    ),
    "compativel": ("", "LLM_API_KEY", "gpt-4o-mini"),
    "anthropic": (
        "https://api.anthropic.com/v1/chat/completions",
        "ANTHROPIC_API_KEY",
        "claude-haiku-4-5-20251001",
    ),
}


def criar_adaptador(provedor: str | None = None, modelo: str | None = None) -> AdaptadorModelo:
    """Sem chave, LEVANTA. Nunca cai para o mock em silêncio.

    A assimetria com o observador é deliberada: telemetria ausente degrada o
    diagnóstico; modelo ausente falsifica o resultado. Foi assim que a POC v1
    publicou números de um parser simulado sem perceber.
    """
    nome = (provedor or os.environ.get("PROVEDOR") or "openrouter").lower()
    if nome == "mock":
        return AdaptadorMock()

    if nome not in PADRAO_POR_PROVEDOR:
        msg = (
            f"PROVEDOR desconhecido: {nome!r}. "
            f"Use um de: {', '.join([*PADRAO_POR_PROVEDOR, 'mock'])}."
        )
        raise ErroDeModelo(msg)

    base_padrao, nome_da_chave, modelo_padrao = PADRAO_POR_PROVEDOR[nome]

    # `LLM_BASE_URL` e' variavel do provedor `compativel`, e SO' dele. Honra-la
    # nos outros deixava um resto de configuracao mudar o destino em silencio:
    # quem tinha Ollama configurado e trocava para `openrouter` mandava a chave
    # e o modelo da Anthropic para `localhost:11434`, e o erro que voltava nao
    # dizia nada sobre a causa. Trocar de provedor tem que bastar uma linha.
    base = base_padrao
    if nome == "compativel":
        base = os.environ.get("LLM_BASE_URL") or base_padrao
    if not base:
        msg = (
            "LLM_BASE_URL ausente. O provedor `compativel` serve para qualquer API "
            "compatível com OpenAI — Ollama, vLLM, Groq, Together — mas precisa "
            "saber para onde apontar."
        )
        raise ErroDeModelo(msg)

    # Todos os três falam o mesmo dialeto (compatível com OpenAI); o que muda é
    # a URL, a variável da chave e como o trace identifica a origem.
    return AdaptadorOpenRouter(
        modelo=modelo or os.environ.get("MODELO_ASSISTENTE") or modelo_padrao,
        base=base,
        origem="openrouter" if nome == "openrouter" else "compativel",
        nome_da_chave=nome_da_chave,
    )
