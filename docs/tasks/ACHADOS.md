# Achados

Registro do que a execução descobriu e o documento não previa: conflito entre
regras `RN-*`, decisão de negócio sem documento, promessa sem código.

> **Próximo número: `A-39`.** Está aqui para ninguém precisar abrir o arquivo
> só para descobrir o número seguinte.

**Este arquivo só tem o que ainda exige ação.** Os 30 achados já fechados foram
para [`docs/relatorios/achados-resolvidos.md`](../relatorios/achados-resolvidos.md)
— eram 56% do arquivo, descrevendo problemas que não existem mais, e todo
fechamento de tarefa passava por cima deles.

> Achado que muda regra vira **pergunta ao cliente** · que muda decisão técnica
> vira **ADR** · que é trabalho vira **tarefa no [BOARD](./BOARD.md)**.
>
> **Achado fechado sai daqui**, para o histórico. Deixá-lo é o que fez este
> arquivo virar o maior dos documentos de tarefa.

---

## 1. Esperando decisão do cliente

**Estes quatro estão parados, e a decisão não é da equipe.** Ficam no topo
porque estavam enterrados numa tabela de 42 linhas e ninguém sabia que existiam
— o que é o mesmo que não ter registrado.

| # | A pergunta que precisa de resposta | Trava o quê |
|---|---|---|
| **A-19** | As listas de motivos derivadas do enum estão certas? Não há lista fechada em documento nenhum, e `RN-M05` exige uma **por tipo**. Hoje são três, todas derivadas: **saída** (`venda` `avaria` `furto` `erro_de_separacao`, T-028), **estorno** (`erro_de_separacao` `estorno`, T-029) e **descarte** (`vencimento` `avaria`, T-029) | qualquer relatório por motivo. ~~T-029~~ — ela fechou com a lista derivada, como a T-028: a regra que `RN-M05` exige (lista fechada, texto livre como complemento) está implementada e testada; o que falta é o cliente confirmar **quais** valores |
| **A-23** | O livro de controlados **exportável** (`RN-C05`) entra no ciclo 1? Custa +1 no catálogo e uma tarefa | fechamento do `RN-C05` |
| **A-33** | O `status` do recebimento basta como "conferência registrada", ou `RN-R03` exige integridade e validade como itens separados? | T-026, e o AC de conferência |
| **A-35** | Auditar **navegação** (catálogo, identidade) é exigência regulatória, ou basta auditar leitura de dado? | recorte do AC-8 / `CS-05` |

---

## 2. Abertos, já endereçados por tarefa

Têm dono no [BOARD](./BOARD.md). Ficam aqui só para o vínculo achado → tarefa
não se perder.

| # | Achado | Tarefa |
|---|---|---|
| A-10 | Observador do LangFuse com três defeitos, mudos por causa do `except` | **T-043** |
| A-11 | Os fakes reimplementam a interseção de escopo da porta — se o adaptador real parar de intersectar, a suíte segue verde | **T-042** |
| A-30 | `RN-P06` (mín/máx por unidade) não tem armazenamento nenhum | **T-046** |
| A-31 | `RepoMovimento.por_cliente` ignora `de` e `ate` — no fake **e** no real | **T-007** / **T-042** |

---

## 3. Abertos, anotados como limite conhecido

Não viram tarefa: são decisões conscientes de não fazer agora, e existem para
não serem redescobertas como se fossem novidade.

| # | Achado | Origem | Consequência |
|---|---|---|---|
| A-14 | **Onde persiste a autorização de RN-L05 não está em documento nenhum.** "Só o RT libera, com justificativa" — mas o bloqueio por validade é derivado da data (ADR-0022) e não há coluna para desfazê-lo. Implementado como fato da trilha de auditoria | execução da T-027 | **T-028** precisa consultar a trilha ao decidir a saída; se não couber, vira ADR e coluna |
| A-22 | **O AC-6 da T-030 pedia recusa num fluxo que o ADR-0010 cortou.** `RN-C02` é sobre ajuste de saldo, e ajuste está fora do ciclo 1. A própria seção "Não faz" da tarefa excluía `RN-C04` pelo mesmo motivo e esqueceu este | execução da T-030 | AC-6 fica em branco, com a razão registrada. Volta quando inventário entrar |
| A-38 | **Estorno de ENTRADA não tem representação no esquema.** `RN-M03` diz que correção se faz por estorno, sem distinguir o tipo do original — mas o sinal de `estorno` é fixo e positivo na view `saldo_lote` (migração 0001, congelada): gravado como está, o estorno de uma entrada **somaria de novo** a quantidade que se queria desfazer. No ciclo 1 só saída se estorna, e o comando recusa o resto dizendo isso | execução da T-029 | Entrada errada não tem correção no ciclo 1. Descrito nas duas telas e nos dois testes negativos. Sair disso exige um tipo novo (`ajuste_negativo`, que o ADR-0010 cortou) ou sinal por movimento — **decisão técnica, vira ADR** quando o inventário entrar |
| A-28 | `react-hooks/rules-of-hooks` desligada em `src/views/**`: a regra identifica componente pelo NOME em maiúscula, e CONTRATOS §6 (congelado) exporta `view` minúsculo. Hook dentro de `if` numa view deixa de ser pego por qualquer verificador | execução da T-005 | anotado em `web/eslint.config.js`; volta se o contrato mudar, ou vira 7ª regra do `arch-check` |
| A-08b | Spike sem relatório R-001, e perguntas não commitadas antes da execução | A-002 | **R-001 entregue** (2026-09-09), T-017 fechada. A parte "perguntas antes do resultado" é **não recuperável** para o spike (usou os 17 casos da T-032); a disciplina passa a valer para os casos novos da [T-032](./T-032-suite-de-avaliacao.md) — ver [R-001 §8](../relatorios/R-001-medicao-modelo-real.md) |

---

## 4. Resolvidos

**30 achados**, com o texto inteiro em
[`docs/relatorios/achados-resolvidos.md`](../relatorios/achados-resolvidos.md).

Os ids continuam citáveis: `A-01` a `A-07` (auditoria A-001), `A-02b` a `A-09`
(auditoria A-002), e `A-12`, `A-13`, `A-15` a `A-18`, `A-20`, `A-21`, `A-24` a
`A-27`, `A-29`, `A-32`, `A-34`, `A-36` (execução).

---

## O que estes 42 achados ensinaram

Classificação feita na 37ª entrega, olhando os 42 de uma vez. **Metade é o
processo funcionando; a outra metade tem três causas com nome.**

| Família | Qtd | Causa raiz |
|---|---|---|
| Bug achado por teste ou execução | 11 | — é para isso que os testes existem |
| Contrato incompleto, descoberto no uso | 8 | — normal num ciclo 1 |
| **Documento prometeu, código não tem** | 10 | status declarado **sem verificação** |
| **Regra sem lastro no modelo de dados** | 4 | ninguém perguntou "cada `RN` tem coluna?" antes de congelar CONTRATOS |
| **Documentos se contradizem** | 5 | cada um foi escrito bem, **isolado**; ninguém cruzou um contra o outro |
| **Corte de tarefa errado** | 4 | listas de arquivo escritas **antes do código** e nunca reconferidas |

As três causas de baixo já viraram regra: *"Status é entrega, não relatório"* no
[`CLAUDE.md`](../../CLAUDE.md) existe **porque** a primeira aconteceu dez vezes.

**A segunda ainda não tem antídoto.** A [matriz de
rastreabilidade](../RASTREABILIDADE.md) mapeia por **família** (`RN-R` → T-022,
T-026), não por regra: ela responde *"onde mora `RN-R`?"* e nunca poderia
responder *"`RN-R03` tem armazenamento?"* — que é exatamente a pergunta que
produziu A-33, A-30, A-14 e A-19. **59 regras, nenhuma rastreada
individualmente.** Enquanto for assim, essa família volta.
