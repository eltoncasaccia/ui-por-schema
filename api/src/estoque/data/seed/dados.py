"""Dados da Bertoni. Deterministicos: mesma seed, mesmo resultado.

Uma fixture que so' tem o caminho feliz esconde exatamente o que este ciclo
precisa provar. Este conjunto carrega os casos dificeis DE PROPOSITO:

  - mesmo numero de lote em duas unidades          RN-L08
  - validade em 15, 45, 89, 91 e 200 dias          fronteiras de RN-L04/L05
  - lote vencido COM saldo                         RN-L06
  - lote em cada status registrado                 maquina de estados
  - termolabil so' em refrigerado                  RN-P02
  - controlado so' na Matriz (sala-cofre)          RN-P03
  - lote com saldo zero                            `esgotado` derivado
  - lote de recall com muitas saidas               CA-01 e RNF-01
"""

import random
from datetime import UTC, date, datetime, timedelta

from estoque.domain.identidade import PERMISSOES_POR_PAPEL

# Data de referencia FIXA. Fixture com data relativa a `hoje` quebra o teste em
# datas diferentes.
HOJE = date(2026, 9, 7)
SEED = 20260907

UNIDADES = [
    ("cd-matriz", "CD Matriz", "seco", True),
    ("cd-refrigerado", "CD Refrigerado", "refrigerado", False),
    ("filial-uberlandia", "Filial Uberlandia", "seco", False),
]

# As sete personas do documento 02. A senha de todas e' `demo` (MODO_DEMO).
USUARIOS = [
    (
        "u-marco",
        "Marco Bertoni",
        "marco@bertoni.com.br",
        "diretor",
        ["cd-matriz", "cd-refrigerado", "filial-uberlandia"],
    ),
    (
        "u-helena",
        "Helena Prado",
        "helena@bertoni.com.br",
        "rt",
        ["cd-matriz", "cd-refrigerado", "filial-uberlandia"],
    ),
    ("u-ivo", "Ivo Nakamura", "ivo@bertoni.com.br", "gerente", ["cd-matriz", "cd-refrigerado"]),
    ("u-odair", "Odair Santos", "odair@bertoni.com.br", "gerente", ["filial-uberlandia"]),
    (
        "u-cleide",
        "Cleide Ramos",
        "cleide@bertoni.com.br",
        "conferente",
        ["cd-matriz", "cd-refrigerado"],
    ),
    (
        "u-rafael",
        "Rafael Lima",
        "rafael@bertoni.com.br",
        "comprador",
        ["cd-matriz", "cd-refrigerado", "filial-uberlandia"],
    ),
    (
        "u-sandra",
        "Sandra Alves",
        "sandra@bertoni.com.br",
        "auditoria",
        ["cd-matriz", "cd-refrigerado", "filial-uberlandia"],
    ),
]

PRODUTOS = [
    # id, ean, nome, fabricante, principio, classe, curva, ativo, centavos
    (
        "p-losartana",
        "7891234000011",
        "Losartana Potassica 50mg",
        "Medley",
        "losartana potassica",
        "comum",
        "A",
        True,
        1250,
    ),
    (
        "p-amoxicilina",
        "7891234000028",
        "Amoxicilina 500mg",
        "EMS",
        "amoxicilina",
        "antimicrobiano",
        "A",
        True,
        2340,
    ),
    (
        "p-clonazepam",
        "7891234000035",
        "Clonazepam 2mg",
        "Roche",
        "clonazepam",
        "controlado",
        "B",
        True,
        890,
    ),
    (
        "p-insulina",
        "7891234000042",
        "Insulina Glargina",
        "Sanofi",
        "insulina glargina",
        "termolabil",
        "A",
        True,
        18900,
    ),
    (
        "p-vacina-hep",
        "7891234000059",
        "Vacina Hepatite B",
        "Butantan",
        "antigeno hbsag",
        "termolabil",
        "B",
        True,
        7650,
    ),
    (
        "p-dipirona",
        "7891234000066",
        "Dipirona 500mg",
        "Neo Quimica",
        "dipirona sodica",
        "comum",
        "C",
        True,
        420,
    ),
    (
        "p-omeprazol",
        "7891234000073",
        "Omeprazol 20mg",
        "Eurofarma",
        "omeprazol",
        "comum",
        "B",
        True,
        680,
    ),
    (
        "p-descontinuado",
        "7891234000080",
        "Cimetidina 200mg",
        "Generico",
        "cimetidina",
        "comum",
        "C",
        False,
        310,
    ),
]

CLIENTES = [
    "Farmacia Sao Joao",
    "Drogaria Central",
    "Rede Popular",
    "Farmacia do Bairro",
    "Hospital Santa Casa",
]


def _d(dias: int) -> date:
    return HOJE + timedelta(days=dias)


def lotes() -> list[tuple[str, str, str, str, date, date, str, str | None]]:
    """Cada linha carrega um caso de teste nomeado no comentario."""
    return [
        # RN-L08: MESMO numero, unidades diferentes, registros distintos
        (
            "l-los-a1-mat",
            "p-losartana",
            "A1",
            "cd-matriz",
            _d(-400),
            _d(200),
            "liberado",
            "R1-A",
        ),
        (
            "l-los-a1-ube",
            "p-losartana",
            "A1",
            "filial-uberlandia",
            _d(-400),
            _d(180),
            "liberado",
            "U1-A",
        ),
        # fronteiras de validade — RN-L04 (90d) e RN-L05 (30d)
        ("l-dip-15d", "p-dipirona", "D15", "cd-matriz", _d(-300), _d(15), "liberado", "R2-B"),
        ("l-dip-45d", "p-dipirona", "D45", "cd-matriz", _d(-300), _d(45), "liberado", "R2-C"),
        ("l-omp-89d", "p-omeprazol", "O89", "cd-matriz", _d(-200), _d(89), "liberado", "R3-A"),
        ("l-omp-91d", "p-omeprazol", "O91", "cd-matriz", _d(-200), _d(91), "liberado", "R3-B"),
        # lote VENCIDO com saldo — RN-L06
        (
            "l-amx-venc",
            "p-amoxicilina",
            "AV1",
            "cd-matriz",
            _d(-500),
            _d(-10),
            "liberado",
            "R4-A",
        ),
        # um lote em cada status registrado
        (
            "l-amx-quar",
            "p-amoxicilina",
            "AQ1",
            "cd-matriz",
            _d(-30),
            _d(300),
            "quarentena",
            None,
        ),
        (
            "l-amx-bloq",
            "p-amoxicilina",
            "AB1",
            "cd-matriz",
            _d(-60),
            _d(250),
            "bloqueado",
            "R5-A",
        ),
        ("l-dip-desc", "p-dipirona", "DD1", "cd-matriz", _d(-400), _d(-60), "descartado", None),
        # RN-P02: termolabil SO' em refrigerado
        ("l-ins-1", "p-insulina", "I1", "cd-refrigerado", _d(-90), _d(220), "liberado", "F1-A"),
        (
            "l-vac-1",
            "p-vacina-hep",
            "V1",
            "cd-refrigerado",
            _d(-120),
            _d(70),
            "liberado",
            "F1-B",
        ),
        (
            "l-ins-quar",
            "p-insulina",
            "I2",
            "cd-refrigerado",
            _d(-5),
            _d(400),
            "quarentena",
            None,
        ),
        # RN-P03: controlado SO' na Matriz (unica com sala-cofre)
        (
            "l-clo-1",
            "p-clonazepam",
            "C1",
            "cd-matriz",
            _d(-150),
            _d(500),
            "liberado",
            "COFRE-1",
        ),
        # saldo ZERO -> `esgotado` derivado, sem coluna
        (
            "l-omp-zero",
            "p-omeprazol",
            "OZ1",
            "cd-matriz",
            _d(-300),
            _d(300),
            "liberado",
            "R6-A",
        ),
        # Uberlandia
        (
            "l-dip-ube",
            "p-dipirona",
            "DU1",
            "filial-uberlandia",
            _d(-100),
            _d(60),
            "liberado",
            "U2-A",
        ),
        (
            "l-omp-ube",
            "p-omeprazol",
            "OU1",
            "filial-uberlandia",
            _d(-100),
            _d(150),
            "liberado",
            "U2-B",
        ),
        (
            "l-amx-ube-quar",
            "p-amoxicilina",
            "AU1",
            "filial-uberlandia",
            _d(-3),
            _d(320),
            "quarentena",
            None,
        ),
    ]


def lotes_em_volume() -> list[tuple[str, str, str, str, date, date, str, str | None]]:
    """Volume para a fila de vencimento ter o que rolar.

    Os casos NOMEADOS acima continuam sendo a fixture de teste — cada um existe
    por uma regra. Estes aqui sao massa: 130 lotes espalhados pelo ano, para
    exercitar paginacao, scroll infinito e a curva de vencimento com forma de
    verdade em vez de tres barras.
    """
    rnd = random.Random(SEED + 2)
    saida: list[tuple[str, str, str, str, date, date, str, str | None]] = []
    produtos_secos = ["p-losartana", "p-amoxicilina", "p-dipirona", "p-omeprazol"]
    frios = ["p-insulina", "p-vacina-hep"]

    for i in range(160):
        # Distribuicao com picos, como um estoque real: o que foi comprado
        # junto vence junto.
        base = rnd.choice([8, 18, 25, 25, 38, 50, 50, 62, 80, 80, 110, 145, 200, 280])
        dias = max(-25, base + rnd.randint(-12, 12))
        frio = i % 7 == 0
        pid = rnd.choice(frios if frio else produtos_secos)
        uid = (
            "cd-refrigerado"
            if frio
            else rnd.choice(["cd-matriz", "cd-matriz", "filial-uberlandia"])
        )
        saida.append(
            (
                f"l-v{i:03d}",
                pid,
                f"V{i:03d}",
                uid,
                _d(-rnd.randint(120, 500)),
                _d(dias),
                "liberado" if dias > -1 or rnd.random() > 0.4 else "bloqueado",
                f"{'F' if frio else 'R'}{rnd.randint(1, 9)}-{rnd.choice('ABCD')}",
            )
        )
    return saida


def movimentos() -> list[dict[str, object]]:
    """Entradas, saidas com cliente e nota (CA-01), e um controlado pendente."""
    rnd = random.Random(SEED)
    saida: list[dict[str, object]] = []
    n = 0

    def novo(**kw: object) -> None:
        nonlocal n
        n += 1
        kw.setdefault("id", f"m-{n:05d}")
        kw.setdefault("status", "efetivado")
        saida.append(kw)

    todos = [*lotes(), *lotes_em_volume()]
    for lid, _pid, _num, uid, _fab, _val, status, _end in todos:
        if status == "descartado":
            continue
        qtd = 0 if lid == "l-omp-zero" else rnd.randint(200, 900)
        if qtd:
            novo(
                lote_id=lid,
                unidade_id=uid,
                tipo="entrada",
                quantidade=qtd,
                motivo="recebimento",
                autor_id="u-cleide",
                criado_em=datetime.combine(_d(-200), datetime.min.time(), UTC),
            )

    # CA-01 / RNF-01: o lote de recall precisa de VOLUME. Medir com tres
    # movimentos prova nada.
    base = datetime.combine(_d(-180), datetime.min.time(), UTC)
    for i in range(60):
        novo(
            lote_id="l-los-a1-mat",
            unidade_id="cd-matriz",
            tipo="saida",
            quantidade=rnd.randint(1, 12),
            motivo="venda",
            autor_id="u-ivo",
            criado_em=base + timedelta(days=i),
            cliente_id=CLIENTES[i % len(CLIENTES)],
            nota_fiscal=f"NF-{100000 + i}",
        )

    for lid, uid in [
        ("l-dip-15d", "cd-matriz"),
        ("l-omp-89d", "cd-matriz"),
        ("l-dip-ube", "filial-uberlandia"),
        ("l-ins-1", "cd-refrigerado"),
    ]:
        for i in range(8):
            novo(
                lote_id=lid,
                unidade_id=uid,
                tipo="saida",
                quantidade=rnd.randint(1, 20),
                motivo="venda",
                autor_id="u-ivo",
                criado_em=base + timedelta(days=i * 7),
                cliente_id=CLIENTES[i % len(CLIENTES)],
                nota_fiscal=f"NF-{200000 + i}",
            )

    # RN-C01 / CA-04: controlado pendente. NAO altera o saldo enquanto pendente.
    novo(
        lote_id="l-clo-1",
        unidade_id="cd-matriz",
        tipo="saida",
        quantidade=30,
        motivo="venda",
        autor_id="u-cleide",
        status="aguardando_autorizacao",
        criado_em=datetime.combine(_d(-1), datetime.min.time(), UTC),
    )

    return saida


def temperaturas() -> list[tuple[str, str, datetime, float]]:
    """RNF-06 exige 5 anos. O seed carrega 180 dias com DUAS excursoes — o
    suficiente para o componente e para os testes, sem inflar o banco."""
    rnd = random.Random(SEED + 1)
    saida = []
    inicio = datetime.combine(_d(-180), datetime.min.time(), UTC)
    for i in range(180 * 4):  # de 6 em 6 horas
        t = inicio + timedelta(hours=i * 6)
        c = round(rnd.uniform(3.2, 6.8), 2)
        if 300 <= i < 306:  # excursao 1: calor
            c = round(rnd.uniform(9.5, 12.0), 2)
        elif 500 <= i < 503:  # excursao 2: congelamento
            c = round(rnd.uniform(-1.0, 1.4), 2)
        saida.append((f"t-{i:05d}", "cd-refrigerado", t, c))
    return saida


def recebimentos() -> list[
    tuple[str, str, str, str, str, str, str | None, float | None, bool, datetime]
]:
    """Casos da Bertoni para T-022, cada um nomeando uma regra.

    RN-R01: nao existe recebimento que nasca liberado sem passar por quarentena
    — aqui o status e' `rascunho`/`conferido`/`liberado`, nunca "entrada direta".
    """

    def _dt(dias: int) -> datetime:
        return datetime.combine(_d(dias), datetime.min.time(), UTC)

    return [
        # normal
        (
            "r-0001",
            "cd-matriz",
            "NF-500123",
            "Distribuidora Alfa",
            "conferido",
            "u-cleide",
            None,
            None,
            False,
            _dt(-12),
        ),
        # RN-R04: divergencia entre nota e fisico -> pendencia, nao impede
        (
            "r-0002",
            "cd-matriz",
            "NF-500124",
            "Distribuidora Beta",
            "conferido",
            "u-cleide",
            None,
            None,
            True,
            _dt(-9),
        ),
        # RN-R05: controlado -> dupla identificacao (conferente E RT)
        (
            "r-0003",
            "cd-matriz",
            "NF-500125",
            "Cristalia",
            "liberado",
            "u-cleide",
            "u-helena",
            None,
            False,
            _dt(-7),
        ),
        # RN-F01: termolabil -> temperatura de chegada registrada
        (
            "r-0004",
            "cd-refrigerado",
            "NF-500126",
            "Instituto Butantan",
            "conferido",
            "u-cleide",
            None,
            5.6,
            False,
            _dt(-5),
        ),
        # rascunho, ainda em conferencia
        (
            "r-0005",
            "cd-matriz",
            "NF-500127",
            "Distribuidora Alfa",
            "rascunho",
            "u-cleide",
            None,
            None,
            False,
            _dt(-2),
        ),
        # unidade diferente — para o teste de escopo (Odair ve so' este)
        (
            "r-0006",
            "filial-uberlandia",
            "NF-500128",
            "Distribuidora Gama",
            "conferido",
            "u-odair",
            None,
            None,
            False,
            _dt(-4),
        ),
    ]


def permissoes_do_papel(papel: str) -> list[str]:
    return sorted(PERMISSOES_POR_PAPEL[papel])  # type: ignore[index]
