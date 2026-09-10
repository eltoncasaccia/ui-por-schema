# T-031 — Superfície tradicional: telas com rota

| | |
|---|---|
| **Onda** | W5 — Garantias |
| **Trilha** | D |
| **Tamanho** | **G** |
| **Depende de** | T-026, T-027, T-028 |
| **Bloqueia** | T-034 |
| **ADRs** | [0005](../adr/0005-l2-leitura-l1-escrita.md) |
| **Requisitos** | `RNF-04` · PRD §5.3 |

## Objetivo

Provar o ganho colateral do ADR-0005: **o mesmo componente registrado serve à rota
tradicional e ao assistente.** Uma declaração, duas superfícies.

E aplicar a regra §11.5 da arquitetura: **o assistente não é o app.** A operação de
alta frequência não tem modelo no caminho.

## PARE — uma decisão antes de abrir editor

**Não há biblioteca de rota no projeto.** Conferido em 2026-09-10: nada de
`react-router` no `web/package.json`. O que existe é `web/src/app/rotas.tsx`, 84
linhas escritas à mão na T-016, servindo **uma** rota com parâmetro (`/v/:viewId`)
— e a própria T-016 registrou que a decisão *"se revisa na T-031"*. É aqui.

Esta tarefa acrescenta 7 rotas, duas delas com parâmetro, mais navegação lateral,
botão voltar e recarregar (AC-6). **Acrescentar dependência exige perguntar
antes** ([ADR-0028](../adr/0028-processo-de-decisao.md)) — e a pergunta é esta,
com a recomendação:

> **Recomendação: adotar `react-router-dom`.** O AC-6 pede URL, histórico e
> recarregar funcionando em 9 rotas; escrever isso à mão é reimplementar uma
> biblioteca madura dentro de uma tarefa que já é **G**, e o resultado seria
> testado por nós em vez de pelo mundo. O custo é uma dependência de cliente,
> sem efeito no servidor nem no catálogo.
>
> **A alternativa** — estender o `rotas.tsx` à mão — só se paga se a resposta ao
> `RNF` de tamanho de bundle for apertada, e não há esse requisito no PRD.

**Sem essa resposta a tarefa não começa.** Ela muda o tamanho, os arquivos e os
testes.

## Antes de começar — o que já está decidido

**Skill:** nenhuma nova; é cliente. As convenções estão em `web/CLAUDE.md`
(camadas, sistema visual, o que `views/` não pode fazer) e em
`web/.claude/skills/testes-web`.

**AC-5 já está provado no servidor — não refaça.** `api/tests/server/test_t016_ac.py`
(T-016 AC-5/AC-6) prova que abrir uma view não devolve dado e que bloco fora do
catálogo de quem abre some. O que sobra para cá é o caminho do **cliente**: a
rota direta não deve *parecer* funcionar antes de o servidor recusar.

**AC-3 (p95 ≤ 2 s) é medição, e medição é da T-034.** É o mesmo tratamento que
`RNF-01` recebeu na T-021 e `RNF-04` na T-023: aqui prova-se a **forma** (AC-2 —
zero chamadas ao modelo no caminho da operação), e o número real, contra Postgres
com volume, fica no relatório de fechamento. **Deixe o AC-3 em branco aqui e
aponte para a T-034** — marcar por otimismo é o que a auditoria A-002 pegou.

## Arquivos de propriedade exclusiva

```
web/src/app/telas/*.tsx   web/src/app/layout/*.tsx   web/src/app/telas/*.test.tsx
```

## Toca, com registro (fora da propriedade exclusiva — declarar no fechamento)

```
web/src/app/rotas.tsx     é da T-016, e passa a ser o roteador de 9 rotas
web/package.json          só se a resposta à pergunta acima for "adotar"
```

> A colisão com `rotas.tsx` é esperada e não é sinal de corte errado: a T-016
> entregou a rota do assistente e anotou que a revisão era desta tarefa.

## Só leitura

`api/src/estoque/application/registry/componentes/**`

## Escopo

### Faz
- Rotas para a operação de alta frequência, sem passar pelo modelo:

| Rota | Componente registrado |
|---|---|
| `/recebimento/novo` | `recebimento_registrar` |
| `/quarentena` | `quarentena_fila` |
| `/quarentena/:loteId` | `quarentena_liberar` |
| `/saida` | `movimento_saida` |
| `/lotes` | `lote_lista` |
| `/lotes/:id` | `lote_detalhe` |
| `/vencimento` | `fila_vencimento` |
| `/controlados` | `controlado_autorizar` |

> **A 8ª rota entrou na revisão de 2026-09-10**, com a W4 fechada. A lista
> original foi escrita quando só existiam os componentes de leitura. Critério
> para entrar: **é fila de trabalho de alguém**, isto é, operação de alta
> frequência que o §11.5 quer sem modelo no caminho. `controlado_autorizar` é a
> fila da Helena e sustenta o `CA-04`.
>
> **Ficam de fora, e é decisão:** `movimento_estorno`, `movimento_descarte` e
> `lote_status_acao`. São correções e exceções — quem as usa chega por uma
> pergunta ("preciso estornar aquela saída"), que é exatamente o caso em que o
> assistente ganha da navegação. Se aparecerem nas perguntas reais da T-032 como
> caminho frequente, viram achado e rota no ciclo 2.

- Navegação lateral filtrada por permissão do ator.
- O assistente é **uma** superfície, acessível de qualquer tela, nunca a única.

### Não faz
Componentes novos. **Zero registro nesta tarefa** — se precisar de um componente
novo, o corte está errado.

## Critérios de aceite

- [ ] **AC-1** Cada rota renderiza o **mesmo** componente registrado usado pelo
      assistente. Teste afirma a identidade da referência. *(ADR-0005 — o critério
      central)*
- [ ] **AC-2** Nenhuma rota de operação chama o modelo. No cliente não há
      "adapter" a espionar: a asserção verificável é sobre o **tráfego** — a rota
      pede `/api/componentes/{id}/dados` e **nunca** `/api/assistente/compor`.
      Espione o `fetch` e afirme zero chamadas ao segundo. *(negativo — §11.5)*
- [ ] **AC-3** p95 de cada rota de operação ≤ 2 s. *(`RNF-04`)* — **medição é da
      [T-034](./T-034-fechamento.md)**, como `RNF-01` (T-021) e `RNF-04` de
      temperatura (T-023). Fica em branco aqui, de propósito.
- [ ] **AC-4** Navegação lateral de Cleide não contém entrada para liberar
      quarentena. *(negativo — matriz)*
- [ ] **AC-5** Acessar `/quarentena/:id` diretamente como Cleide é recusado **no
      servidor**, não só escondido. *(negativo — `RN-A03`)* — o lado servidor já
      está provado em `api/tests/server/test_t016_ac.py`; o que falta é o cliente
      não fingir que funcionou antes da recusa chegar.
- [ ] **AC-6** URL, botão voltar e recarregar funcionam em todas as rotas.
- [ ] **AC-7** Contagem de catálogo inalterada: **23**.

## Armadilhas

AC-1 é a prova de que o ADR-0005 se pagou. Se a tela com rota precisar de um
componente diferente do que o assistente usa, o desenho tem duplicação — e é
melhor descobrir agora do que no ciclo 2.
