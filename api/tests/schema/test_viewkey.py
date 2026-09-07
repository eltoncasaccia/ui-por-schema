"""ADR-0021 — os dois identificadores, e por que sao dois."""

from estoque.schema.contrato import Bloco, ViewSchema
from estoque.schema.viewkey import novo_view_id, view_key


def s(*blocos: Bloco, titulo: str | None = None) -> ViewSchema:
    return ViewSchema(versao=1, titulo=titulo, blocos=blocos)


def test_ordem_de_chaves_nao_muda_a_chave() -> None:
    a = s(Bloco(tipo="fila_vencimento", params={"janela": "90", "unidade_id": "cd-matriz"}))
    b = s(Bloco(tipo="fila_vencimento", params={"unidade_id": "cd-matriz", "janela": "90"}))
    assert view_key(a) == view_key(b)


def test_ordem_de_blocos_muda_a_chave() -> None:
    """Ordem e' significado: trocar dois blocos de lugar e' outra tela."""
    x = Bloco(tipo="fila_vencimento", params={})
    y = Bloco(tipo="estoque_indicador", params={"metrica": "lotes_bloqueados"})
    assert view_key(s(x, y)) != view_key(s(y, x))


def test_titulo_nao_entra_na_chave() -> None:
    """A mesma tela com titulo diferente continua sendo a mesma tela."""
    x = Bloco(tipo="fila_vencimento", params={})
    assert view_key(s(x, titulo="A")) == view_key(s(x, titulo="B"))


def test_chave_e_estavel_entre_processos() -> None:
    """sha256, nao `hash()` do Python — que e' salgado por processo e daria
    chave diferente a cada reinicio, ressuscitando o bug do favorito da v1."""
    esperado = view_key(s(Bloco(tipo="fila_vencimento", params={"janela": "90"})))
    assert esperado == view_key(s(Bloco(tipo="fila_vencimento", params={"janela": "90"})))
    assert len(esperado) == 64


def test_view_id_e_sempre_diferente_e_opaco() -> None:
    """Recompor a mesma view da' view_id NOVO e view_key IGUAL.

    E' o ponto do ADR-0021: revogar o endereco nao apaga a identidade, entao o
    favorito sobrevive a revogacao.
    """
    ids = {novo_view_id() for _ in range(200)}
    assert len(ids) == 200
    assert all(len(i) >= 20 for i in ids)
