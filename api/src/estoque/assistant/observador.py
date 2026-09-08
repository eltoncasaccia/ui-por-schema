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
"""

from typing import Protocol

from estoque.assistant.trace import Trace


class Observador(Protocol):
    """Recebe o que aconteceu. Nunca levanta — falha de telemetria não pode
    derrubar a requisição que ela observa."""

    def composicao(
        self, *, trace: Trace, ator_id: str, papel: str | None, catalogo: int
    ) -> None: ...

    def nota(self, *, nome: str, valor: float, comentario: str = "") -> None: ...

    def descarregar(self) -> None: ...


class ObservadorNulo:
    """Padrão. Não faz nada, e é a implementação certa quando não há para onde
    mandar — melhor que um `if observador is not None` espalhado."""

    def composicao(
        self, *, trace: Trace, ator_id: str, papel: str | None, catalogo: int
    ) -> None:
        return

    def nota(self, *, nome: str, valor: float, comentario: str = "") -> None:
        return

    def descarregar(self) -> None:
        return
