# T-015 — Motor de render e política de layout

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | D — Render e interface |
| **Tamanho** | M |
| **Depende de** | T-012 |
| **Bloqueia** | T-016, T-025, toda a W3 |
| **ADRs** | [0006](../adr/0006-contrato-unico-de-componente.md), [0007](../adr/0007-camadas-e-arch-check.md) |

## Objetivo

Schema validado → React. E a regra de layout que a v1 aprendeu errando.

## Arquivos de propriedade exclusiva

```
web/src/render/motor.tsx   web/src/render/layout.tsx   web/src/render/*.test.tsx
web/src/components/base/*.tsx
```

## Escopo

### Faz
- Percorre `ViewSchema`, resolve cada bloco no registry, chama `load` autorizado,
  aplica `select`, renderiza `render`.
- **Layout obedece ao componente, não ao modelo**: cada componente declara
  `tamanho`; o motor arranja. O schema não tem campo de layout.
- Estados por bloco: carregando, erro, sem acesso, vazio.
- **`sem_acesso` é decisão do motor**, não componente do catálogo — o modelo não
  sabe que existe (ADR-0014).
- Componentes base de apresentação: tabela, cartão, lista, indicador, vazio, erro.

### Não faz
Buscar dado direto (T-016 orquestra via TanStack Query). Registrar componentes de
domínio (W3).

## Critérios de aceite

- [ ] **AC-1** Um bloco com erro **não derruba os demais** — cada bloco tem
      fronteira de erro própria.
- [ ] **AC-2** Componente `tamanho: 'inteira'` nunca é espremido em coluna estreita.
      *(a tabela em tile de 200px da v1)*
- [ ] **AC-3** O motor **ignora** qualquer sugestão de layout que apareça no schema
      — mesmo que um campo chegue. *(negativo)*
- [ ] **AC-4** Bloco negado por permissão renderiza `sem_acesso` sem revelar o que
      seria mostrado. *(ADR-0014)*
- [ ] **AC-5** `arch:check` confirma zero `useEffect` em `components/**`.
- [ ] **AC-6** `components/base/**` não importa `data/`, `application/` nem
      `@tanstack/react-query`. *(negativo — ADR-0008)*
- [ ] **AC-7** Nenhum componente base aceita `dangerouslySetInnerHTML`. *(negativo)*

## Armadilhas

AC-3 protege contra a regressão mais provável: alguém acrescenta `layout` ao schema
"só para este caso", e o modelo passa a decidir aparência (ADR-0001, §11.4 da
arquitetura).
