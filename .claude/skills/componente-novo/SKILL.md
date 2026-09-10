---
name: componente-novo
description: Cria um componente do catálogo do assistente, dos dois lados — registro Python em api/src/estoque/application/registry/componentes/ e view React em web/src/views/. Use ao executar T-019, T-021 a T-030, ou quando a tarefa disser "registra o componente X", "novo componente", ou listar ids na coluna Componentes do BOARD. Cobre params, requires, load, select, viewmodel, a bijeção e os testes obrigatórios.
---

# Componente novo, dos dois lados

Um componente do catálogo tem **duas metades obrigatórias**
([ADR-0017](../../../docs/adr/0017-registry-servidor-views-cliente.md)):
registro na API e view no cliente. Entregar uma só quebra o CI.

**São 23 registrados, e W3 e W4 fecharam** — nenhum componente do ciclo 1 está
pendente. O teto do catálogo é 25 ([ADR-0011](../../../docs/adr/0011-teto-de-catalogo.md))
e o build quebra acima disso: sobra folga para **2**, e a T-044
(`relatorio_movimentacao`) já reserva uma. Passar do teto é discussão de escopo,
não de código.

> Este número sai do BOARD §2, e é para ser reconferido lá — não daqui. Ele já
> esteve errado: dizia "faltam 12" com a onda inteira entregue.

---

## 0. Leia o exemplo canônico antes de escrever

`api/src/estoque/application/registry/componentes/fila_vencimento.py` e
`web/src/views/fila_vencimento.tsx`. Eles têm a forma, o estilo e a densidade de
comentário que o projeto usa. **Imite-os.**

Depois, os testes: `api/tests/registry/test_lote_lista.py` mostra como se prova
escopo, enum fechado, custo invisível e pureza do `select`.

---

## 1. Lado servidor — `registry/componentes/<id>.py`

```python
class Params(BaseModel):
    # Enum FECHADO. Nunca data solta, nunca texto livre.
    janela: Literal["30", "60", "90"] = "90"
    unidade_id: UnidadeId | None = None

class VM(BaseModel):
    """É EXATAMENTE isto que atravessa a rede."""

class Dados(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    # o que o load buscou, incluindo `hoje: date`

async def carregar(params: Params, ctx: LoadContext) -> Dados: ...
def projetar(d: Dados) -> VM: ...

COMPONENTE = registrar(ComponentDef(
    id="...", label="...",
    description="...",          # ≥40 chars, vai LITERALMENTE para o prompt
    examples=("...", "..."),    # perguntas reais, SEM citar unidade
    params=Params, requires="lote.ler", tamanho="inteira",
    load=carregar, select=projetar,
))
```

### As armadilhas, em ordem de gravidade

**Param de texto livre.** Todo recorte que o operador sabe pedir precisa existir
como valor nomeado. Filtro que falta **alarga a resposta em silêncio**, e uma
lista maior parece uma resposta boa — é o risco R-5 do PRD, o achado mais
perigoso da v1. Se a tarefa pedir `validadeAte`, prefira `janela: 30|60|90`.

**Custo no viewmodel.** Nenhum componente que não seja `produto_ficha` leva
custo. O que não entra no `VM` não chega ao navegador (`CA-05`, ADR-0020). Não
coloque `Produto` inteiro no `Dados` — coloque só o nome.

**`select` impuro.** Sem I/O, sem `date.today()`. A data chega pelo `Dados`,
senão duas chamadas sobre a mesma carga divergem na virada do dia.

**`description` que cita enum filtrado.** O enum de params é filtrado por
permissão; a prosa não é. Se a descrição repete um valor que o filtro removeu, o
vazamento volta pela porta dos fundos — o modelo aprende que existe algo que não
pode propor, e tenta.

**`examples` citando nome de unidade.** O catálogo é o vocabulário **daquele
ator**; sugerir unidade que ele não alcança é oferecer uma porta fechada.

**Escopo.** Não filtre por unidade no `load`: o `LoadContext` já vem com o
escopo intersectado (`RN-A01`). Sua responsabilidade é não contorná-lo.

**Status.** Filtre pelo **efetivo**, não pela coluna
([ADR-0022](../../../docs/adr/0022-status-registrado-e-efetivo.md)): `vencido` e
`esgotado` saem de data e saldo, e não existem no banco.

---

## 2. Lado cliente — `web/src/views/<id>.tsx`

```tsx
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
type VM = ViewModel<'meu_id'>          // GERADO. Nunca declare o tipo à mão.

export const view: View<'meu_id'> = ({ vm }) => ( ... )
```

Reuse `ui/Tabela`, `ui/Indicador`, `ui/BarraFaixas`, `ui/Etiqueta` e os mapas de
`ui/estados.ts`. Nada de cor ou espaçamento literal — só tokens.

A view **não** busca dado, **não** usa `useEffect`, **não** importa TanStack
Query. Recebe `vm` e desenha. `scripts/arch-check.ts` verifica.

---

## 3. Regenerar

```bash
make gerar-indice     # registry/indice.py e views/indice.ts
make types            # generated/contrato.json e generated/componentes.ts
```

Rode `make types` **depois** de o componente Python existir — ele lê o registry.

---

## 4. Testes obrigatórios — `api/tests/registry/test_<id>.py`

Use `tests/registry/fakes.py` (repositórios falsos, estoque montado para os
casos difíceis). Cubra, no mínimo:

| O que provar | Como |
|---|---|
| **escopo** *(negativo)* | Odair **pedindo** `cd-matriz` recebe zero linhas — o param não contorna a interseção |
| **negativa que não vaza** *(negativo)* | id fora de escopo e id inexistente produzem erro **idêntico**: código, mensagem e `repr` |
| **enum fechado** *(negativo)* | `Params.model_validate({"campo": "valor_invalido"})` levanta `ValidationError` |
| **custo invisível** | `vm.model_dump_json()` não contém `"custo"` nem o valor do fixture, **nem para quem tem `custo.ler`** |
| **`select` puro** | `projetar(dados) == projetar(dados)` |
| **catálogo por persona** | quem não tem a permissão **não vê o id** em `ids_permitidos(ator)` |

O teste de catálogo por persona mora em `tests/registry/test_catalogo_por_ator.py`
— acrescente seus ids lá (é o DoD, T-012 AC-1).

---

## 5. Antes de commitar

```bash
cd api && uv run pytest -q && uv run mypy --strict src && uv run ruff check src tests
cd web && npx tsc --noEmit && npx vitest run
make arch
```

O `bijecao.test.ts` tem de passar com N registros e N views. Se ele reclamar de
"view órfã" ou "componente sem view", você entregou meia tarefa.

Atualize a contagem de catálogo no BOARD §5 e siga o passo 7 da skill
`executar-tarefa`.
