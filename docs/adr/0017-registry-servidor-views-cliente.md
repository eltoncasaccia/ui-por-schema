# ADR-0017 — Registry no servidor, views no cliente, ligados por id

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Fundacional |
| **Substitui** | [ADR-0006](./0006-contrato-unico-de-componente.md) |
| **Verificado** | Bijeção implementada em [T-039](../tasks/T-039-codegen-e-bijecao.md). Até então este ADR era, por sua própria definição, uma regressão |

## Contexto

O ADR-0006 tinha um alvo certo e um mecanismo que a [ADR-0016](./0016-api-python-cliente-typescript.md)
tornou impossível.

O alvo, que continua válido, é evitar o modo de apodrecimento clássico:

> existe a lista de componentes que o modelo conhece, e existe a lista que o
> sistema sabe renderizar. As duas divergem.

O mecanismo era uma declaração única em TypeScript. Com API em Python, a
declaração não pode ser única: `params`, `requires`, `description`, `load` e
`select` vivem no servidor; `render` vive no cliente.

**Trocar de mecanismo sem trocar de alvo** é o que este ADR faz.

## Decisão

> **Duas declarações, uma por runtime, ligadas pelo id do componente — e a
> bijeção entre elas é verificada em CI, não confiada.**

```python
# api/src/estoque/registry/componentes/lote_lista.py
registrar(ComponentDef(
    id="lote_lista",
    label="Lotes",
    description="Lista lotes por produto, unidade, status ou faixa de validade...",
    examples=["lotes da amoxicilina", "o que está em quarentena"],
    params=LoteListaParams,          # Pydantic
    requires="lote.ler",
    tamanho="inteira",
    load=carregar_lotes,
    select=projetar_lotes,           # roda AQUI — ADR-0020
))
```

```tsx
// web/src/views/lote_lista.tsx
export const view: View<'lote_lista'> = ({ vm }) => <TabelaLotes linhas={vm.linhas} />
```

A ligação é o id, e `ComponentId` é **gerado** do OpenAPI da API — o cliente não
inventa ids, recebe a união de literais.

### O teste que substitui a garantia perdida

```
para todo id registrado na API  → existe exatamente uma view no cliente
para toda view no cliente       → existe exatamente um id registrado na API
```

Falha o CI dos dois lados. **É este teste que faz o ADR-0017 valer o que o
ADR-0006 valia.** Sem ele, esta decisão é uma regressão.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Manter tudo em TypeScript (ADR-0006) | Descartado pelo ADR-0016 |
| Gerar as views a partir do registry | Componente gerado é componente ruim: acessibilidade, i18n e design viram template |
| Descrever a view em JSON no servidor | É o L3 do ADR-0001 por outro nome — o servidor passaria a descrever aparência |

## Consequências

**Positivas**
- O que precisa estar junto continua junto **em cada lado**: no servidor, params +
  permissão + carga + projeção; no cliente, um componente React por id.
- O cliente não tem como conhecer `load`, `requires` nem consulta.

**Negativas**
- **Duas listas existem.** O ADR-0006 se orgulhava de não ter a segunda. Agora ela
  existe, e a defesa é um teste em vez de o compilador.
- Acrescentar componente vira dois commits em dois lugares.
- O tipo do viewmodel é gerado, não escrito — erro de projeção aparece no CI, não
  no editor.

**Riscos aceitos**
- Se o teste de bijeção for desligado ou ficar frágil, o sistema volta ao
  apodrecimento que o ADR-0006 descrevia — desta vez sem nada percebendo.

## Conformidade

- `test_bijecao_registry_views` no CI dos dois repositórios.
- `web/src/generated/component-ids.ts` é gerado; edição manual falha o CI.
- `import-linter`: `registry` não importa `server`; `views` não importa `generated/api-client` fora do motor de render.

## Referências
- [ADR-0006](./0006-contrato-unico-de-componente.md) (substituído) · [ADR-0016](./0016-api-python-cliente-typescript.md)
