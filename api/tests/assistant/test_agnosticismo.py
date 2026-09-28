"""O provedor é trocável por configuração, não por código.

A porta `AdaptadorModelo` já existia, mas o servidor instanciava OpenRouter
direto: a abstração existia e a fiação a ignorava. Estes testes garantem que a
troca continue sendo uma variável de ambiente.
"""

import inspect

import pytest

from estoque.application.registry.registry import catalogo_de
from estoque.assistant.adapter import (
    ErroDeModelo,
    ferramenta_do_catalogo,
    json_schema_do_catalogo,
)
from estoque.assistant.fabrica import PADRAO_POR_PROVEDOR, criar_adaptador
from estoque.domain.identidade import Ator
from estoque.server.rotas import assistente


def test_o_servidor_nao_amarra_um_provedor() -> None:
    fonte = inspect.getsource(assistente._adaptador)
    assert "criar_adaptador" in fonte
    assert "AdaptadorOpenRouter" not in fonte, "instanciar direto anula a porta"


def test_mock_e_explicito_e_nunca_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem chave o adaptador LEVANTA. Cair no mock em silêncio foi o erro que
    fez a v1 publicar números de um simulador."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("PROVEDOR", raising=False)
    with pytest.raises(ErroDeModelo):
        criar_adaptador()
    assert criar_adaptador("mock") is not None


def test_provedor_desconhecido_falha_com_as_opcoes(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ErroDeModelo, match="PROVEDOR desconhecido"):
        criar_adaptador("gemini-caseiro")


def test_compativel_exige_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """`compativel` cobre Ollama, vLLM, Groq — mas precisa saber para onde ir."""
    monkeypatch.setenv("LLM_API_KEY", "x")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    with pytest.raises(ErroDeModelo, match="LLM_BASE_URL"):
        criar_adaptador("compativel")

    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1/chat/completions")
    assert criar_adaptador("compativel") is not None


def test_llm_base_url_nao_vaza_para_outro_provedor(monkeypatch: pytest.MonkeyPatch) -> None:
    """O teste negativo da troca de provedor.

    `LLM_BASE_URL` pertence a `compativel`. Enquanto ela valia para todos, um
    resto de configuracao de Ollama mandava a chave e o modelo da Anthropic
    para `localhost:11434` — sem aviso, e com um erro que nao dizia a causa.
    Trocar de provedor precisa bastar uma linha no `.env`.
    """
    from estoque.assistant.adapter import AdaptadorOpenRouter

    ollama = "http://host.docker.internal:11434/v1/chat/completions"
    monkeypatch.setenv("LLM_BASE_URL", ollama)
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("LLM_API_KEY", "x")

    for provedor in ("openrouter", "anthropic"):
        a = criar_adaptador(provedor)
        assert isinstance(a, AdaptadorOpenRouter)
        assert a._base == PADRAO_POR_PROVEDOR[provedor][0], provedor
        assert "11434" not in a._base, f"{provedor} foi parar no modelo local"

    # E o positivo: `compativel` continua sendo quem honra a variavel.
    c = criar_adaptador("compativel")
    assert isinstance(c, AdaptadorOpenRouter)
    assert c._base == ollama


def test_cada_provedor_tem_chave_e_modelo_padrao() -> None:
    for nome, (_, chave, modelo) in PADRAO_POR_PROVEDOR.items():
        assert chave.endswith("_KEY"), nome
        assert modelo, nome


# --- os dois envelopes de saída ------------------------------------------
def test_ferramenta_usa_o_mesmo_schema_do_modo_restrito(personas: dict[str, Ator]) -> None:
    """Duas construções do mesmo schema divergiriam, e a divergência só
    apareceria em produção."""
    cat = catalogo_de(personas["cleide"])
    assert ferramenta_do_catalogo(cat)["function"]["parameters"] == json_schema_do_catalogo(cat)


def test_a_ferramenta_e_forcada_e_nomeada() -> None:
    from estoque.assistant.adapter import AdaptadorOpenRouter

    corpo = inspect.getsource(AdaptadorOpenRouter._corpo)
    assert '"tool_choice"' in corpo, "sem forçar, o modelo pode responder em prosa"


def test_a_cadeia_de_fallback_termina_em_livre() -> None:
    """`livre` funciona em qualquer provedor — é o último recurso, e é também
    o modo que mede a pergunta original da v1."""
    from estoque.assistant.adapter import _cadeia

    for modo in ("restrito", "ferramenta", "livre"):
        assert _cadeia(modo)[-1] == "livre", modo
    assert _cadeia("restrito") == ("restrito", "ferramenta", "livre")


def test_a_resposta_e_lida_nos_dois_formatos() -> None:
    """Modo ferramenta devolve o JSON em `tool_calls[].function.arguments`,
    não em `content`. Ler só um formato quebraria metade dos provedores."""
    from estoque.assistant.adapter import _primeiro_conteudo

    direto = {"choices": [{"message": {"content": '{"versao":1}'}}]}
    ferramenta = {
        "choices": [{"message": {"tool_calls": [{"function": {"arguments": '{"versao":1}'}}]}}]
    }
    assert _primeiro_conteudo(direto) == _primeiro_conteudo(ferramenta) == '{"versao":1}'
