"""Rate limit no login. T-040, CS-06.

DUAS chaves, e as duas importam:

  por CONTA   impede força bruta contra uma senha específica
  por IP      impede o ataque inverso — testar `senha123` em mil contas, que
              passa por baixo de um limite só por conta

Janela deslizante em memória. **Limitação registrada:** o contador não sobrevive
a reinício do processo nem é compartilhado entre réplicas. Para o ciclo 1, com
um container, é aceitável; num cenário com mais de uma réplica isso vira um
limite por réplica, e a proteção se dilui. A alternativa — contador no banco —
custa uma tabela e uma migração, e foi adiada conscientemente.

Toda recusa é auditada: tentativa bloqueada é sinal, não ruído.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

# Valores escolhidos para conter força bruta sem punir quem erra a senha duas
# vezes. A janela reabre sozinha: limite que exige intervenção manual vira
# negação de serviço contra o próprio usuário.
TENTATIVAS_POR_CONTA = 5
TENTATIVAS_POR_IP = 20
JANELA_S = 300.0


@dataclass(slots=True)
class Limitador:
    tentativas_conta: int = TENTATIVAS_POR_CONTA
    tentativas_ip: int = TENTATIVAS_POR_IP
    janela_s: float = JANELA_S
    _por_chave: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def _limpar(self, chave: str, agora: float) -> deque[float]:
        fila = self._por_chave[chave]
        while fila and agora - fila[0] > self.janela_s:
            fila.popleft()
        return fila

    def bloqueado(self, *, conta: str, ip: str, agora: float | None = None) -> bool:
        """Consulta sem registrar. Chamada ANTES de verificar a senha."""
        t = agora if agora is not None else time.monotonic()
        return (
            len(self._limpar(f"c:{conta}", t)) >= self.tentativas_conta
            or len(self._limpar(f"i:{ip}", t)) >= self.tentativas_ip
        )

    def registrar_falha(self, *, conta: str, ip: str, agora: float | None = None) -> None:
        """Só a FALHA conta. Login bem-sucedido não gasta cota — senão quem
        trabalha o dia inteiro se bloqueia sozinho."""
        t = agora if agora is not None else time.monotonic()
        self._limpar(f"c:{conta}", t).append(t)
        self._limpar(f"i:{ip}", t).append(t)

    def limpar_conta(self, conta: str) -> None:
        """Chamada no login bem-sucedido: quem provou a identidade não carrega
        as tentativas erradas de antes."""
        self._por_chave.pop(f"c:{conta}", None)
