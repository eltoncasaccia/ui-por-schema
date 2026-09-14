"""Observabilidade do assistente — porta, não dependência.

Por que uma porta e não chamar o SDK direto: o `Trace` deste projeto já existe
e alimenta o painel de Execution Trace, que é como a POC é julgada. Uma
ferramenta externa deve OBSERVAR esse conceito, não substituí-lo — senão a
própria evidência do projeto passa a depender de um serviço de terceiro estar
no ar.

Diferença deliberada em relação ao adaptador de modelo: sem chave, o adaptador
FALHA (o erro central da v1 foi medir um simulador sem perceber). Aqui, sem
chave, o observador é NULO e o sistema segue. Observabilidade ausente degrada o
diagnóstico; modelo ausente falsifica o resultado.

Dois caminhos (T-043): `ao_vivo` envolve o trabalho enquanto ele acontece, e a
duração de cada etapa é a real; `composicao` registra depois do fato, e existe
para a eval, que só tem o `Trace` pronto.
"""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol

from estoque.assistant.trace import Trace


class Etapa(Protocol):
    """Uma etapa medida ao vivo. `detalhar` anexa o que só se sabe no fim dela."""

    def detalhar(self, *, trace: Trace) -> None: ...


class Observacao(Protocol):
    """Uma composição em andamento. Nunca levanta."""

    def etapa(self, nome: str) -> AbstractContextManager[Etapa]: ...

    def concluir(self, *, trace: Trace, catalogo: int) -> None: ...


class Observador(Protocol):
    """Recebe o que aconteceu. Nunca levanta — falha de telemetria não pode
    derrubar a requisição que ela observa."""

    def ao_vivo(
        self, *, pergunta: str, ator_id: str, papel: str | None
    ) -> AbstractContextManager[Observacao]: ...

    def composicao(
        self, *, trace: Trace, ator_id: str, papel: str | None, catalogo: int
    ) -> None: ...

    def nota(self, *, nome: str, valor: float, comentario: str = "") -> None: ...

    def descarregar(self) -> None: ...


class EtapaNula:
    def detalhar(self, *, trace: Trace) -> None:
        return


class ObservacaoNula:
    @contextmanager
    def etapa(self, nome: str) -> Iterator[Etapa]:
        yield EtapaNula()

    def concluir(self, *, trace: Trace, catalogo: int) -> None:
        return


class ObservadorNulo:
    """Padrão. Não faz nada, e é a implementação certa quando não há para onde
    mandar — melhor que um `if observador is not None` espalhado."""

    @contextmanager
    def ao_vivo(
        self, *, pergunta: str, ator_id: str, papel: str | None
    ) -> Iterator[Observacao]:
        yield ObservacaoNula()

    def composicao(
        self, *, trace: Trace, ator_id: str, papel: str | None, catalogo: int
    ) -> None:
        return

    def nota(self, *, nome: str, valor: float, comentario: str = "") -> None:
        return

    def descarregar(self) -> None:
        return
