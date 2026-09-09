# T-003 — Contrato do registry e do componente

| | |
|---|---|
| **Onda** | W0 — Contratos · **serial** |
| **Trilha** | C — Registry |
| **Tamanho** | M |
| **Depende de** | T-002 |
| **Bloqueia** | T-004 |
| **ADRs** | [0017](../adr/0017-registry-servidor-views-cliente.md), [0004](../adr/0004-autorizacao-em-tres-momentos.md), [0005](../adr/0005-l2-leitura-l1-escrita.md), [0020](../adr/0020-select-no-servidor.md) |

## Objetivo

`defineComponent` e seus tipos — a seção 5 de [CONTRATOS.md](./CONTRATOS.md).
**Tipos e invariantes, sem componente nenhum registrado.**

## Arquivos de propriedade exclusiva

```
api/src/estoque/application/registry/definir.py   api/src/estoque/application/registry/tipos.py   api/src/estoque/application/registry/definir.test.py
```

## Só leitura

`api/src/estoque/domain/**`

## Escopo

### Faz
- `ComponentDef`, `CommandDef`, `LoadContext`, `Tamanho`, **`RequiresPorValor`**.
- **Sem campo `render`** — a view vive em `web/src/views` ([ADR-0017](../adr/0017-registry-servidor-views-cliente.md)).
- `defineComponent` com inferência de tipo de `params` → `load` → `select` → `render`.
- Invariantes em tempo de tipo e em tempo de registro.

### Não faz
- Registro de componentes reais (W3/W4). Catálogo (T-012). Render (T-015).

## Critérios de aceite

- [ ] **AC-1** `defineComponent` sem `requires` **não compila**. *(negativo — ADR-0004)*
- [ ] **AC-2** `ComponentDef` **não tem** campo `render`. *(negativo — ADR-0017)*
- [ ] **AC-2b** `select` devolve modelo Pydantic — é o que atravessa a rede.
      `D` não é serializável para fora. *(negativo — [ADR-0020](../adr/0020-select-no-servidor.md))*
- [ ] **AC-2c** `RequiresPorValor` filtra valores de enum do catálogo conforme as
      permissões do ator. *(achado A-05)*
- [ ] **AC-3** Componente com `commands` e `tamanho !== 'inteira'` é rejeitado em
      tempo de registro. *(ADR-0005)*
- [ ] **AC-4** O tipo de `select` é inferido do retorno de `load`; incompatibilidade
      não compila.
- [ ] **AC-5** `description` vazia ou com menos de 40 caracteres é rejeitada — é o
      texto que o modelo lê para decidir.
- [ ] **AC-6** Id fora de `snake_case` é rejeitado no registro.

## Armadilhas

`defineComponent` é o contrato mais caro de mudar depois — toca os 23 componentes.
Vale gastar tempo aqui. Depois de T-004, muda só por ADR.
