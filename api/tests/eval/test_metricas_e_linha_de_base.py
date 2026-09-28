"""T-032 — AC-4 (regressão contra linha de base), AC-6 (schema inválido é
falha diferente de composição errada) e AC-7 (mock nunca produz número)."""

from estoque.eval.__main__ import Resultado, principal, regrediu, resumo
from estoque.eval.casos import Caso


def _resultado(
    *, schema_valido: bool, composicao_correta: bool, modo: str = "restrito"
) -> Resultado:
    return Resultado(
        caso=Caso(id="x", persona="cleide", pergunta="?", esperado=frozenset()),
        modo=modo,
        schema_valido=schema_valido,
        composicao_correta=composicao_correta,
        ms=100,
        tokens_entrada=10,
        custo_usd=None,
        obtido=frozenset(),
    )


class TestRegrediu:
    def test_queda_maior_que_a_tolerancia_e_regressao(self) -> None:
        assert regrediu(atual=0.90, base=0.97) is True  # 7pp > 5pp

    def test_queda_dentro_da_tolerancia_nao_e_regressao(self) -> None:
        assert regrediu(atual=0.93, base=0.97) is False  # 4pp <= 5pp

    def test_exatamente_no_limite_nao_e_regressao(self) -> None:
        """`> tolerancia`, não `>=` — 5pp exatos é o limiar do ADR-0013, não
        além dele."""
        assert regrediu(atual=0.92, base=0.97) is False

    def test_melhora_nunca_e_regressao(self) -> None:
        assert regrediu(atual=0.99, base=0.90) is False


class TestLinhaDeBase:
    def test_primeira_execucao_grava_e_nao_falha(self, monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """(negativo) Sem linha de base anterior, não há o que comparar — o
        ADR-0013 é explícito: a primeira execução DEFINE a linha de base, não
        reprova por falta de uma."""
        import estoque.eval.__main__ as m

        monkeypatch.setattr(m, "LINHA_DE_BASE", tmp_path / "linha-de-base.json")
        monkeypatch.setenv("PROVEDOR", "mock")

        # AC-7 barra antes de qualquer coisa — usado aqui só para não gastar
        # token; a gravação da linha de base é exercitada abaixo, direto.
        assert m.carregar_linha_de_base() == {}
        m.gravar_linha_de_base({"restrito": 0.97})
        assert m.carregar_linha_de_base() == {"restrito": 0.97}


class TestMockNuncaProduzNumero:
    async def test_provedor_mock_recusa_rodar(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """(negativo) — é o erro que a v1 cometeu: publicar número de um
        simulador sem perceber. `principal` tem que recusar ANTES do 1º caso."""
        monkeypatch.setenv("PROVEDOR", "mock")
        codigo = await principal(["restrito"], None)
        assert codigo == 2


class TestDistingueSchemaInvalidoDeComposicaoErrada:
    """AC-6. Um agregado só de 'acertos' esconde que um modelo não sabe emitir
    JSON e outro escolhe o componente errado — e a correção de cada um é
    oposta. As duas taxas têm que poder discordar."""

    def test_schema_invalido_pode_ter_composicao_certa_por_coincidencia(self) -> None:
        # obtido == esperado (frozenset vazio == frozenset vazio) mesmo com
        # schema inválido: a métrica de composição não devia "herdar" o erro.
        rs = [_resultado(schema_valido=False, composicao_correta=True)]
        s = resumo(rs, "restrito")
        assert s["schema_valido"] == 0.0
        assert s["composicao_correta"] == 1.0

    def test_schema_valido_pode_ter_composicao_errada(self) -> None:
        rs = [_resultado(schema_valido=True, composicao_correta=False)]
        s = resumo(rs, "restrito")
        assert s["schema_valido"] == 1.0
        assert s["composicao_correta"] == 0.0

    def test_as_duas_taxas_sao_independentes_num_lote_misto(self) -> None:
        rs = [
            _resultado(schema_valido=True, composicao_correta=True),
            _resultado(schema_valido=True, composicao_correta=False),
            _resultado(schema_valido=False, composicao_correta=False),
            _resultado(schema_valido=False, composicao_correta=False),
        ]
        s = resumo(rs, "restrito")
        assert s["schema_valido"] == 0.5
        assert s["composicao_correta"] == 0.25
