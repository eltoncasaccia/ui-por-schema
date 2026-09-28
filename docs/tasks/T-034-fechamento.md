# T-034 — Relatório de fechamento do ciclo 1

| | |
|---|---|
| **Onda** | W5 |
| **Trilha** | E |
| **Tamanho** | M |
| **Depende de** | T-031, T-032, T-033 |
| **Bloqueia** | — |
| **Requisitos** | PRD §11 |

## Objetivo

Fechar o ciclo com o mesmo padrão do [documento 00](../00-achados-v1.md): **o que
não se sustentou aparece com o mesmo destaque do que se sustentou.**

Este é o documento que o ciclo 2 vai ler primeiro.

## Arquivos de propriedade exclusiva

```
docs/relatorios/R-004-fechamento-ciclo-1.md
docs/05-achados-ciclo-1.md
```

## Escopo

### Faz

1. **Checklist de release do PRD §11**, item a item, com evidência — link para o
   teste, não afirmação.
2. **Os quatro números do PRD §9**, por modelo, com a recomendação de qual usar em
   produção e o porquê.
3. **O que não se sustentou.** Seção obrigatória. Se estiver vazia, não foi
   escrita com honestidade.
4. **Achados**, consolidados do BOARD, classificados: muda regra → pergunta ao
   cliente; muda decisão técnica → ADR; muda escopo → revisão do PRD.
5. **Custo real medido**: tokens por pergunta, com o catálogo de 23 em produção.
6. **Pendências para o ciclo 2**, com as cinco perguntas do cliente destacadas —
   elas são critério de entrada, não de saída.
7. **O que faríamos diferente.**

### Não faz
Código. Nenhuma linha.

## Critérios de aceite

- [x] **AC-1** Todo item do checklist do PRD §11 tem evidência linkada.
      [R-004 §1](../relatorios/R-004-fechamento-ciclo-1.md#1-checklist-de-release-do-prd-11)
      — 5 verdes, 2 parciais, 1 vermelho, cada um com link. Um item (RF-01 a
      RF-20) tem evidência por família de regra, não RF a RF, e o relatório
      diz isso explicitamente.
- [x] **AC-2** Os quatro números estão publicados, com o modelo identificado e o
      trace comprovando que **não** foi o mock. *(o erro central da v1)*
      [R-002](../relatorios/R-002-avaliacao-ciclo-1.md) — `principal()` recusa
      o mock por código (T-032 AC-7), e os dois modelos estão nomeados em
      cada linha da tabela.
- [x] **AC-3** A seção "o que não se sustentou" é não-vazia e específica.
      [R-004 §4](../relatorios/R-004-fechamento-ciclo-1.md#4-o-que-não-se-sustentou)
      — 8 itens, cada um com número ou causa, não afirmação vaga.
- [x] **AC-4** Toda decisão tomada durante a execução que divergiu de um ADR virou
      **ADR novo**, não comentário em código. Nenhuma decisão desta tarefa
      divergiu de ADR — é medição e síntese, não implementação.
- [x] **AC-5** As cinco pendências do documento 02 estão listadas como critério de
      entrada do ciclo 2. [R-004 §7](../relatorios/R-004-fechamento-ciclo-1.md#7-pendências-para-o-ciclo-2).
- [x] **AC-6** Se CS-04 não passou, o achado está registrado com a decisão tomada.
      CS-04 **passou** (R-003) — condição não se aplica. O efeito colateral
      relacionado (A-42, `titulo` sem teto) já está registrado, à parte.
- [x] **AC-7** A pergunta da seção 13 da arquitetura v2 — *com que frequência um
      modelo real emite schema válido?* — está **respondida com número**.
      83,7%–95,3% conforme o modelo, 43 casos reais — [R-002](../relatorios/R-002-avaliacao-ciclo-1.md).

## Armadilhas

A tentação, no fim de um ciclo, é escrever o relatório que justifica o que foi
feito. O valor do documento 00 veio de fazer o contrário. **AC-3 existe para forçar
isso.**
