"""T-040 · rate limit — AC-5 a AC-8.

`auth/` estava vazio: nada limitava tentativas de senha (A-002, achado A-03).

O relógio entra por parâmetro em todo teste. Teste de janela que dorme é lento
e instável; teste que controla o tempo é nenhum dos dois.
"""

from estoque.auth.limite import Limitador


# --- AC-5: por conta -------------------------------------------------------
def test_ac5_tentativas_na_mesma_conta_disparam_limite() -> None:
    lim = Limitador(tentativas_conta=3, tentativas_ip=99)
    for _ in range(3):
        assert not lim.bloqueado(conta="cleide", ip="1.1.1.1", agora=0)
        lim.registrar_falha(conta="cleide", ip="1.1.1.1", agora=0)
    assert lim.bloqueado(conta="cleide", ip="1.1.1.1", agora=0)


def test_ac5_outra_conta_nao_e_afetada() -> None:
    """Bloquear a conta errada é negação de serviço contra quem não fez nada."""
    lim = Limitador(tentativas_conta=2, tentativas_ip=99)
    for _ in range(3):
        lim.registrar_falha(conta="cleide", ip="1.1.1.1", agora=0)
    assert lim.bloqueado(conta="cleide", ip="1.1.1.1", agora=0)
    assert not lim.bloqueado(conta="helena", ip="1.1.1.1", agora=0)


# --- AC-6: por IP ----------------------------------------------------------
def test_ac6_limite_por_ip_pega_o_ataque_que_o_de_conta_deixa_passar() -> None:
    """Testar `senha123` em mil contas passa por baixo de um limite só por
    conta: cada conta acumula uma tentativa e nenhuma estoura."""
    lim = Limitador(tentativas_conta=5, tentativas_ip=3)
    for i in range(3):
        conta = f"vitima{i}@x.com"
        assert not lim.bloqueado(conta=conta, ip="9.9.9.9", agora=0)
        lim.registrar_falha(conta=conta, ip="9.9.9.9", agora=0)
    # Nenhuma conta chegou perto do próprio limite — e o IP estourou.
    assert lim.bloqueado(conta="vitima99@x.com", ip="9.9.9.9", agora=0)


def test_ac6_outro_ip_nao_e_afetado() -> None:
    lim = Limitador(tentativas_conta=99, tentativas_ip=2)
    for _ in range(3):
        lim.registrar_falha(conta="a@x.com", ip="9.9.9.9", agora=0)
    assert lim.bloqueado(conta="b@x.com", ip="9.9.9.9", agora=0)
    assert not lim.bloqueado(conta="b@x.com", ip="8.8.8.8", agora=0)


# --- AC-8: a janela reabre -------------------------------------------------
def test_ac8_a_janela_reabre_sozinha() -> None:
    """Limite que exige intervenção manual vira negação de serviço contra o
    próprio usuário: um erro de digitação bloquearia para sempre."""
    lim = Limitador(tentativas_conta=2, tentativas_ip=99, janela_s=60)
    lim.registrar_falha(conta="cleide", ip="1.1.1.1", agora=0)
    lim.registrar_falha(conta="cleide", ip="1.1.1.1", agora=10)
    assert lim.bloqueado(conta="cleide", ip="1.1.1.1", agora=20)
    # 61s depois da primeira: ela sai da janela e sobra uma tentativa
    assert not lim.bloqueado(conta="cleide", ip="1.1.1.1", agora=71)
    # 71s depois da segunda: janela vazia
    assert not lim.bloqueado(conta="cleide", ip="1.1.1.1", agora=81)


def test_janela_desliza_e_nao_zera_de_uma_vez() -> None:
    """Deslizante, não fixa: com janela fixa o atacante espera o corte e gasta
    o dobro da cota de uma vez."""
    lim = Limitador(tentativas_conta=3, tentativas_ip=99, janela_s=100)
    for t in (0, 50, 90):
        lim.registrar_falha(conta="c", ip="i", agora=t)
    assert lim.bloqueado(conta="c", ip="i", agora=95)
    assert not lim.bloqueado(conta="c", ip="i", agora=101)  # a de t=0 saiu
    lim.registrar_falha(conta="c", ip="i", agora=101)
    assert lim.bloqueado(conta="c", ip="i", agora=102)


# --- login bem-sucedido limpa ---------------------------------------------
def test_login_certo_nao_carrega_as_tentativas_erradas() -> None:
    """Quem trabalha o dia inteiro não pode se bloquear por errar duas vezes
    de manhã e voltar à tarde."""
    lim = Limitador(tentativas_conta=3, tentativas_ip=99)
    lim.registrar_falha(conta="cleide", ip="1.1.1.1", agora=0)
    lim.registrar_falha(conta="cleide", ip="1.1.1.1", agora=1)
    lim.limpar_conta("cleide")
    for t in range(3):
        assert not lim.bloqueado(conta="cleide", ip="1.1.1.1", agora=10 + t)
        lim.registrar_falha(conta="cleide", ip="1.1.1.1", agora=10 + t)


def test_so_a_falha_conta() -> None:
    """`bloqueado()` consulta sem registrar — senão a própria checagem gastaria
    a cota, e um usuário legítimo se bloquearia ao abrir a tela."""
    lim = Limitador(tentativas_conta=2, tentativas_ip=99)
    for _ in range(10):
        assert not lim.bloqueado(conta="cleide", ip="1.1.1.1", agora=0)


# --- AC-7: a recusa é auditada --------------------------------------------
def test_ac7_recusa_por_limite_e_auditada() -> None:
    """Tentativa bloqueada é sinal, não ruído: é o que denuncia força bruta."""
    import inspect

    from estoque.server import app

    fonte = inspect.getsource(app.entrar)
    assert "login_bloqueado" in fonte
    assert "aud.registrar" in fonte
    # a auditoria acontece ANTES do raise, senão nunca chega a gravar
    assert fonte.index("aud.registrar") < fonte.index('ErroDominio("limite"')


def test_ac7_a_conta_bloqueada_nao_gasta_hash() -> None:
    """Verificar senha de quem já está bloqueado é trabalho a favor do
    atacante: argon2 é caro de propósito."""
    import inspect

    from estoque.server import app

    fonte = inspect.getsource(app.entrar)
    assert fonte.index("LIMITE.bloqueado") < fonte.index("PH.hash")
