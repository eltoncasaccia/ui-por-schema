# T-017 — SPIKE: medição com modelo real

| | |
|---|---|
| **Onda** | W2 — Furo de risco · **1 sessão, exclusiva** |
| **Trilha** | C |
| **Tamanho** | M |
| **Depende de** | T-011, T-014, T-016 |
| **Bloqueia** | **toda a W3**, T-032 |
| **ADRs** | [0013](../adr/0013-suite-de-avaliacao.md), [0011](../adr/0011-teto-de-catalogo.md) |
| **Requisitos** | O-7, R-1 |

## Objetivo

Responder a pergunta que a POC v1 deixou aberta, **antes** de existirem 23
componentes escritos:

> **Um modelo real emite schemas válidos com que frequência?**

Esta é a tarefa que pode matar o projeto. Está em segundo lugar na ordem de
execução, e não no fim, exatamente por isso.

## Natureza: spike descartável

O código desta tarefa **não vai para produção**. Ela existe para produzir um
**relatório**. Ao final, `api/src/estoque/spike/` é removido; o relatório permanece.

Isso é o que permite medir cedo sem colidir com a propriedade de arquivo de W3.

## Arquivos de propriedade exclusiva

```
api/src/estoque/spike/**            (removido ao final)
docs/relatorios/R-001-medicao-modelo-real.md   (permanece)
```

## Escopo

### Faz
- Seis componentes de leitura **mínimos** dentro de `api/src/estoque/spike/`, usando o registry,
  o catálogo por ator e o adapter reais: `lote_lista`, `lote_detalhe`,
  `fila_vencimento`, `produto_ficha`, `movimento_lista`, `estoque_indicador`.
- 30 perguntas reais de operador, cobrindo as 7 personas — escritas **antes** de
  ver qualquer resposta do modelo.
- Execução com `claude-haiku-4-5-20251001` **e** `claude-sonnet-5`, mesmas perguntas.
- Relatório `R-001` com os quatro números do PRD §9, por modelo.

### Não faz
Componentes definitivos (W3). Suíte de regressão completa (T-032).

## Critérios de aceite

- [ ] **AC-1** As 30 perguntas estão escritas e versionadas **antes** da primeira
      execução. Commit separado, anterior. *(evita ajustar a pergunta ao resultado)*
- [ ] **AC-2** As execuções usam o adapter **real**, com `ANTHROPIC_API_KEY`
      presente. O trace de cada execução comprova. *(o erro central da v1)*
- [ ] **AC-3** Relatório publica, por modelo: taxa de schema válido, taxa de
      composição correta, p50 e p95 até o primeiro componente, tokens de entrada
      por pergunta.
- [ ] **AC-4** O relatório inclui **as falhas**, transcritas: toda pergunta cujo
      schema foi rejeitado, com a razão.
- [ ] **AC-5** Recomendação explícita ao final: **seguir**, **seguir com ajuste no
      prompt ou no catálogo**, ou **rever o desenho**. Com o número que a sustenta.
- [ ] **AC-6** `api/src/estoque/spike/` removido no commit de fechamento; `arch:check` verde.

## Regra de liberação de W3

> **Nenhuma tarefa de W3 começa antes de o relatório R-001 ser lido.**

Se a taxa de schema válido ficar abaixo de 80%, W3 **não abre**: abre-se antes uma
tarefa de ajuste de prompt e de descrições, e o spike é reexecutado. Escrever 15
componentes sobre uma hipótese que não se sustenta é o desperdício que esta ordem
de execução existe para evitar.

## Armadilhas

Ajustar as perguntas depois de ver as respostas produz um número bonito e inútil.
AC-1 existe para tornar isso visível no histórico do git.
