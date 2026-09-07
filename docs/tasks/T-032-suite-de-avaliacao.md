# T-032 — Suíte de avaliação, 40 perguntas

| | |
|---|---|
| **Onda** | W5 |
| **Trilha** | E — Qualidade |
| **Tamanho** | **G** |
| **Depende de** | T-017, W3 completa |
| **Bloqueia** | T-034 |
| **ADRs** | [0013](../adr/0013-suite-de-avaliacao.md), [0011](../adr/0011-teto-de-catalogo.md) |
| **Requisitos** | PRD §9 · risco R-5 |

## Objetivo

A rede de regressão de uma UI não-determinística. Sem ela, mudar uma palavra numa
`description` degrada o sistema **sem quebrar nenhum teste**.

## Arquivos de propriedade exclusiva

```
eval/casos/*.yaml   eval/executar.ts   eval/relatorio.ts   eval/*.test.ts
docs/relatorios/R-002-avaliacao-ciclo-1.md
```

## Escopo

### Faz
- ~40 casos: pergunta, persona, catálogo esperado, composição esperada (conjunto de
  ids, **não** ordem exata), regra ou critério que justifica o caso.
- **Casos negativos por persona** — onde composição correta significa **não**
  compor:

| Caso negativo | Esperado |
|---|---|
| Cleide pergunta o custo de um produto | Nenhum componente com custo |
| Odair pede saldo de Ribeirão Preto | Negativa, não composição vazia |
| Ivo pede para liberar quarentena | Componente ausente do catálogo |
| Conferente pede a trilha de auditoria | Componente ausente do catálogo |

- **Auditoria de enums** (risco R-5): para cada recorte que um operador sabe pedir,
  verificar que existe valor nomeado no catálogo. Recorte sem enum alarga a
  resposta em silêncio.
- Execução com os dois modelos; relatório com as quatro métricas do PRD §9.
- CI: suíte completa quando catálogo, prompt ou modelo mudam; subconjunto de fumaça
  nos demais commits.

### Não faz
Corrigir o prompt — se a taxa for baixa, o achado vai ao BOARD e vira tarefa.

## Critérios de aceite

- [ ] **AC-1** 40 casos cobrindo as 7 personas e os 8 critérios de aceite.
- [ ] **AC-2** Pelo menos 8 casos negativos, com "não compor" como resultado
      esperado. *(negativo)*
- [ ] **AC-3** Relatório publica as quatro métricas do PRD §9, por modelo.
- [ ] **AC-4** CI falha se a taxa de schema válido cair mais de 5 pontos
      percentuais em relação à execução registrada anterior. *(ADR-0013)*
- [ ] **AC-5** A auditoria de enums roda sobre o catálogo real e lista todo recorte
      sem valor nomeado. *(risco R-5)*
- [ ] **AC-6** A suíte distingue **schema inválido** de **schema válido com
      composição errada** — são falhas diferentes com causas diferentes.
- [ ] **AC-7** Nenhum caso usa o adapter mock. Execução com mock é rejeitada pelo
      relatório. *(negativo — o erro da v1)*

## Armadilhas

**AC-6 é o que torna a suíte útil.** Um número agregado de "acertos" esconde a
diferença entre um modelo que não sabe emitir JSON e um que escolhe o componente
errado — e as duas correções são opostas.
