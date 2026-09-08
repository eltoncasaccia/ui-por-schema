# T-012 — Registry runtime e catálogo por ator

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | C |
| **Tamanho** | M |
| **Depende de** | T-004, T-009 |
| **Bloqueia** | T-013, T-015, toda a W3 |
| **ADRs** | [0003](../adr/0003-catalogo-por-ator.md), [0006](../adr/0006-contrato-unico-de-componente.md), [0011](../adr/0011-teto-de-catalogo.md) |
| **Requisitos** | CS-02, RNF-08 |

## Objetivo

O registry em runtime e a derivação do catálogo por ator. **O modelo nunca vê o
que o ator não pode.**

## Arquivos de propriedade exclusiva

```
api/src/estoque/registry/registry.py   api/src/estoque/registry/catalogo.py
api/src/estoque/registry/orcamento.py  api/src/estoque/registry/*.test.py
scripts/gerar-indice.ts
```

## Escopo

### Faz
- Registro em runtime; id duplicado é erro fatal na inicialização.
- `catalogoDe(ator)` — filtra por `requires` e aplica escopo de unidade.
- Serialização do catálogo para o prompt: id, label, description, examples, params.
- `orcamentoDe(catalogo)` — contagem de tokens.
- `scripts/gerar-indice.ts` gera `registry/indice.ts` varrendo
  `registry/componentes/*`. **Nunca editado à mão** (acordo §4).

### Não faz
Registrar componentes (W3/W4). Validar schema (T-013).

## Critérios de aceite

> **Verificado por** `tests/registry/test_catalogo_por_ator.py` — auditado em [A-002](../relatorios/A-002-auditoria-de-execucao.md).

- [ ] **AC-1** Para cada uma das 7 personas, o conjunto de ids no catálogo é
      **exatamente** o esperado. Entrar ou sair um componente quebra o teste.
      *(ADR-0003)*
- [ ] **AC-2** Nenhum componente com `requires` contendo `custo.ler` aparece no
      catálogo de Cleide, Helena, Ivo ou Odair. *(negativo — `CS-02`, `CA-05`)*
- [ ] **AC-3** Apenas o catálogo de Helena contém `quarentena_liberar`.
      *(`RN-R02`)*
- [ ] **AC-4** `catalogo.length <= 25`; o build falha acima. *(`RNF-08`, ADR-0011)*
- [ ] **AC-5** Orçamento de tokens do maior catálogo é reportado no teste e alerta
      acima de 4k.
- [ ] **AC-6** Id duplicado derruba a inicialização com mensagem clara. *(negativo)*
- [ ] **AC-7** `indice.ts` regenerado é idêntico ao versionado — CI falha se alguém
      editou à mão.

## Armadilhas

O catálogo é a **higiene**, não a garantia (ADR-0004). Passar nos testes daqui não
autoriza afrouxar a checagem no `load`.
