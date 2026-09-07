# Sistema de Controle de Estoque com Assistente

Bertoni Distribuidora Farmacêutica · **Ciclo 1** · caso fictício

> **Estado:** documentação de engenharia completa. **Nenhum código escrito ainda.**
> Próximo passo: [T-001 — Bootstrap](./tasks/T-001-bootstrap.md).

---

## Por onde começar

**Vai executar uma tarefa?** → [Acordo de Trabalho](./tasks/README.md) → [BOARD](./tasks/BOARD.md) → sua tarefa.
Não é preciso ler mais nada. Cada arquivo de tarefa é auto-contido.

**Quer entender o projeto?** → [O cliente](./01-o-cliente.md) → [PRD-001](./prd/PRD-001-ciclo-1.md) → [ADRs](./adr/).

**Quer saber onde algo está implementado?** → [Rastreabilidade](./RASTREABILIDADE.md).

---

## Os dois níveis de documentação

| Nível | Documentos | Papel |
|---|---|---|
| **Contexto** | 00 a 04 | Narrativa. De onde as decisões vieram e por quê |
| **Engenharia** | PRD · ADR · Contratos · Tarefas | **Normativo.** É o que se executa |

Hierarquia em caso de conflito: **`RN-*` > ADR > PRD > tarefa.**

---

## Documentos de engenharia

| Documento | O que é | Autoridade |
|---|---|---|
| [**PRD-001**](./prd/PRD-001-ciclo-1.md) | Requisitos, personas, 11 histórias com critérios de aceite, métricas, riscos, critérios de release | Normativo para **requisitos** |
| [**ADR 0001–0015**](./adr/) | Decisões técnicas, com alternativas descartadas e como cada uma é verificada em código | Normativo para **decisões** |
| [**CONTRATOS**](./tasks/CONTRATOS.md) | Interfaces congeladas: identidade, erros, domínio, registry, schema, borda HTTP | Normativo para **interfaces** |
| [**Acordo de Trabalho**](./tasks/README.md) | Como várias sessões trabalham em paralelo sem colidir. DoR, DoD, git, quando parar | Normativo para **processo** |
| [**BOARD**](./tasks/BOARD.md) | 34 tarefas, 6 ondas, 5 trilhas, grafo de dependências, caminho crítico | Normativo para **execução** |
| [**Rastreabilidade**](./RASTREABILIDADE.md) | `RN` → `CA` → tarefa → teste. Cobertura de ADR | Referência cruzada |
| [Relatórios](./relatorios/) | R-001 a R-004 — o que foi medido | Produzido durante a execução |

## Documentos de contexto

| # | Documento | O que é |
|---|---|---|
| 00 | [Achados da POC v1](./00-achados-v1.md) | O que a primeira POC provou e o que **não** provou |
| 01 | [O cliente](./01-o-cliente.md) | A empresa, as pessoas, os episódios que motivaram o projeto |
| 02 | [Regras de negócio](./02-regras-de-negocio.md) | **Normativo.** Regras numeradas, estados, matriz de permissões, critérios de aceite |
| 03 | [Arquitetura v2](./03-arquitetura-v2.md) | A visão técnica narrada. As decisões viraram ADRs |
| 04 | [Escopo do ciclo 1](./04-escopo-ciclo-1.md) | Histórico. Conteúdo normativo migrado para PRD-001 e ADR-0010 |

---

## O ciclo 1 em uma tela

**Entrega:** estoque por lote com duas superfícies — telas com rota para a operação
de alta frequência, e um assistente que compõe a interface a partir de 23
componentes registrados, sem gerar código e sem nunca autorizar escrita.

**Fora do escopo:** contagem, ajuste, transferência, off-line
([ADR-0010](./adr/0010-corte-de-escopo-ciclo-1.md), [ADR-0015](./adr/0015-assistente-exige-conexao.md)).
Os oito critérios de aceite do cliente continuam dentro — nenhum depende do que saiu.

**Fecha quando:** CA-01 a CA-08 e CS-01 a CS-06 passam como teste **e** os quatro
números do [PRD §9](./prd/PRD-001-ciclo-1.md) são medidos com modelo real.

### As três ideias que sustentam o desenho

1. **O modelo escolhe a composição. Nunca o código, nunca os dados, nunca a
   autorização.** ([ADR-0001](./adr/0001-ui-por-schema.md))
2. **A saída do modelo autoriza renderizar. Nunca autoriza escrever.**
   ([ADR-0002](./adr/0002-plano-render-plano-escrita.md))
3. **Autorização em três momentos; só o terceiro protege** — o que roda em cada
   `load` e cada `command`, com a identidade real.
   ([ADR-0004](./adr/0004-autorizacao-em-tres-momentos.md))

### A tarefa que pode matar o projeto

[**T-017**](./tasks/T-017-spike-medicao.md) mede, com um modelo real e seis
componentes, a taxa de schema válido — a pergunta que a POC v1 deixou aberta. Está
em segundo lugar na ordem de execução, e não no fim, de propósito: se a hipótese
não se sustentar, isso aparece antes de existirem 23 componentes escritos.

---

## Pendências com o cliente

As cinco pendências do [documento 02 §10](./02-regras-de-negocio.md) **não travam o
ciclo 1** — todas caem no que ficou fora. São **critério de entrada do ciclo 2**, e
duas mudam regra:

- O limite de R$ 5.000 é por item ou por contagem inteira?
- Uberlândia off-line: dois usuários contam o mesmo endereço, quem ganha?
