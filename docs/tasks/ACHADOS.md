# Achados

Registro do que a execução descobriu e o documento não previa: conflito entre
regras `RN-*`, decisão de negócio sem documento, promessa sem código.

> **Próximo número: `A-55`.** Está aqui para ninguém precisar abrir o arquivo
> só para descobrir o número seguinte. *(Estava desatualizado em "A-50" antes
> desta edição — A-51 a A-54 já existiam na §3. Corrigido ao gravar o A-50.)*

**Este arquivo só tem o que ainda exige ação.** Os 33 achados já fechados foram
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
| **A-50** | **Pelo menos 5 casos da suíte de avaliação (T-032) têm `esperado` questionável.** `neg-liberar-helena`, `status-helena`, `neg-controlado-ivo` e `neg-status-cleide` falharam nas 4 combinações de modelo/modo com uma composição alternativa DEFENSÁVEL (o ator tem permissão para o que foi composto, só não é o componente mais específico); `sandra-rastreio` é ambíguo entre `rastreabilidade` e `lote_movimentos`. Detalhe em [R-002 §5](../relatorios/R-002-avaliacao-ciclo-1.md#5-achado-pelo-menos-5-casos-com-esperado-questionável). Um sexto caso, `temperatura-marco`, não tem essa saída — o modelo nunca compõe, e vale investigar a `description` de `temperatura_historico` | *sem tarefa própria — ajuste em `api/src/estoque/eval/casos.py` na próxima medição real, não urgente* |

*(A-46 fechou com a T-055.)*

> A-44 fechou em 2026-09-14, com a [T-052](./T-052-banco-de-teste-isolado.md).
> A-47 fechou em 2026-09-28, com a [T-056](./T-056-erratum-r-001.md) — o
> erratum está no [R-001 §8](../relatorios/R-001-medicao-modelo-real.md).
> A-46 fechou em 2026-09-28, com a [T-055](./T-055-filtro-interativo.md).

---

## 3. Abertos, anotados como limite conhecido

Não viram tarefa: são decisões conscientes de não fazer agora, e existem para
não serem redescobertas como se fossem novidade.

| # | Achado | Origem | Consequência |
|---|---|---|---|
| A-51 | **`LLM_BASE_URL` valia para todos os provedores, e não só para `compativel`.** Quem tinha Ollama configurado e trocava para `PROVEDOR=openrouter` mandava a chave e o modelo da Anthropic para `localhost:11434`, sem aviso, e o erro que voltava não dizia a causa. O `make modelo` ecoava a variável crua e **confirmava o destino errado** | auditoria A-003, ao trocar de modelo | **Corrigido.** `LLM_BASE_URL` só vale para `compativel`; `make modelo` agora pergunta à fábrica em vez de ecoar o ambiente. Teste negativo em `tests/assistant/test_agnosticismo.py`, conferido em vermelho antes de valer |
| A-52 | **A saída por venda deixava enviar com cliente e nota fiscal vazios.** `podeEnviar` em `movimento_saida.tsx` cobria a justificativa do FEFO e esquecia o destinatário: o botão habilitava, a view mandava `cliente_id: ""`, e o servidor recusava com `422 Entrada invalida.` — genérico, e **depois** de o operador já ter confirmado. O mesmo formulário trata a justificativa com cuidado (botão travado e o texto citando `RN-L03`); o destinatário não tinha nada | e2e novo de saída (A-003) | **Corrigido.** `faltaDestinatario` entra na condição do botão, com aviso no mesmo tom do FEFO, e a view manda `null` em vez de string vazia. Dois negativos em `web/e2e/saida.spec.ts`, conferidos em vermelho antes de valer |
| A-53 | **O leitor de código de barras não resolve produto nenhum — a tela de recebimento não recebe.** A view promete no próprio comentário que *"o componente repede os próprios dados com `ean=<lido>`"*, e escreve `data-ean` no campo. **Ninguém lê esse atributo.** A rota manda `params: () => ({})`, `views/` não pode buscar dado (ADR-0007), e não existe o equivalente ao `TelaSaida.tsx`, que resolve o mesmo problema segurando o campo FORA da view. Conferido no navegador: depois do Enter, nenhuma segunda requisição sai, e a tela fica em "0 itens". Os 12 testes do `vitest` passam porque entregam `vm.lido` pronto — provam que o formulário **desenha** o produto lido, nunca que alguém consegue lê-lo | experimento A-004 | **Corrigido.** `render/repedir.ts` dá à view o mesmo canal de evento que `comando.ts` já dava para escrita — o contrato `View<Id>` não muda — e `TelaRecebimento.tsx` é quem ouve e é dona do param. Junto veio um segundo defeito: param novo deixava a query `pending`, o `Esqueleto` substituía a view e **o estado local morria** — a cada caixa lida o conferente perdia a lista. Resolvido com `placeholderData` no `motor.tsx`, restrito ao MESMO componente. 4 testes em `web/e2e/recebimento.spec.ts`, conferidos em vermelho antes de valer |
| A-54 | **A suíte de e2e não era idempotente contra o próprio banco.** `liberacao.spec.ts` AC-4 afirmava `registros.length === 1` — o total de liberações daquele lote na trilha. Mas `make e2e` depende de `db-teste`, o seed devolve o lote à quarentena a cada execução, e `auditoria` é append-only e **nunca zera**: a contagem subia a cada rodada e o teste quebrava na enésima. Passava só porque ninguém tinha rodado a suíte muitas vezes seguidas | verificação dos sete commits da A-004, em sequência | **Corrigido.** A asserção passa a ser sobre a **diferença** (`antes + 1`), nunca o total — descrever o banco que o autor tem na frente não é descrever a invariante. Conferido com três execuções seguidas. Ressalva: não foi possível sabotá-la, porque a máquina de estados barra a segunda liberação antes do `If-Match` — a contagem é guarda, e quem prova o `If-Match` é a asserção da mensagem |
| A-14 | **Onde persiste a autorização de RN-L05 não está em documento nenhum.** "Só o RT libera, com justificativa" — mas o bloqueio por validade é derivado da data (ADR-0022) e não há coluna para desfazê-lo. Implementado como fato da trilha de auditoria | execução da T-027 | **T-028** precisa consultar a trilha ao decidir a saída; se não couber, vira ADR e coluna |
| A-22 | **O AC-6 da T-030 pedia recusa num fluxo que o ADR-0010 cortou.** `RN-C02` é sobre ajuste de saldo, e ajuste está fora do ciclo 1. A própria seção "Não faz" da tarefa excluía `RN-C04` pelo mesmo motivo e esqueceu este | execução da T-030 | AC-6 fica em branco, com a razão registrada. Volta quando inventário entrar |
| A-38 | **Estorno de ENTRADA não tem representação no esquema.** `RN-M03` diz que correção se faz por estorno, sem distinguir o tipo do original — mas o sinal de `estorno` é fixo e positivo na view `saldo_lote` (migração 0001, congelada): gravado como está, o estorno de uma entrada **somaria de novo** a quantidade que se queria desfazer. No ciclo 1 só saída se estorna, e o comando recusa o resto dizendo isso | execução da T-029 | Entrada errada não tem correção no ciclo 1. Descrito nas duas telas e nos dois testes negativos. Sair disso exige um tipo novo (`ajuste_negativo`, que o ADR-0010 cortou) ou sinal por movimento — **decisão técnica, vira ADR** quando o inventário entrar |
| A-28 | `react-hooks/rules-of-hooks` desligada em `src/views/**`: a regra identifica componente pelo NOME em maiúscula, e CONTRATOS §6 (congelado) exporta `view` minúsculo. Hook dentro de `if` numa view deixa de ser pego por qualquer verificador | execução da T-005 | anotado em `web/eslint.config.js`; volta se o contrato mudar, ou vira 7ª regra do `arch-check` |
| A-08b | Spike sem relatório R-001, e perguntas não commitadas antes da execução | A-002 | **R-001 entregue** (2026-09-09), T-017 fechada. **Não fecha** ([T-056](./T-056-erratum-r-001.md), 2026-09-28): existiu uma rodada com pré-commitação (30 perguntas, `tarefa/T-017`), mas é a rodada **publicada** — 17 casos, sem essa proteção — que sustenta a recomendação do §7 e o número que o PRD §9 cita. O texto correto não é "não recuperável", é "recuperável, mas não vale para a rodada publicada". A disciplina passa a valer para os casos novos da [T-032](./T-032-suite-de-avaliacao.md) — ver [R-001 §8](../relatorios/R-001-medicao-modelo-real.md) |
| A-42 | **`titulo` do schema é texto livre sem teto — e é onde a injeção pega.** Blocos e params têm teto de 12; o título, nenhum: `POST /api/views` aceita 1 MB, grava e devolve. Com `qwen2.5:7b` real, o texto hostil colado na pergunta chegou ao título em 5 de 6 perguntas, literalmente em 2. Não autoriza nada, mas é o único texto da composição escolhido de fora, exibido com cara de tela oficial | execução da T-033 ([R-003 §3](../relatorios/R-003-seguranca-ciclo-1.md)) | **Sem dono — decisão da equipe.** Recomendação: corrigir no ciclo, com teto (~120 caracteres) em `ViewSchema.titulo` e `NovaView.titulo`. Restrição nova em contrato congelado (§7) → tarefa de contrato. `test_cs01_titulo_de_um_megabyte_e_recusado` está `xfail(strict=True)` e reprova sozinho quando o teto entrar |
| A-43 | **Escrita composta junto de leitura é aceita, e a checagem que deveria decidir nunca dispara.** `validar.py:113` exige `len(bloco.params) >= 0` (sempre verdadeiro) e `tamanho != "inteira"` (todo componente com `commands` é `inteira`, invariante 4). O RT compõe `[lote_lista, quarentena_liberar]` e os dois passam. O ADR-0005 diz "não é composto junto de outros **no mesmo bloco**", e isso tem duas leituras | execução da T-033 ([R-003 §3](../relatorios/R-003-seguranca-ciclo-1.md)) | Não é furo de autorização: gravar exige `POST /api/comandos`, com `requires`, CSRF e `If-Match`. **Decisão técnica, vira emenda ao ADR-0005**; qualquer que seja a leitura, a condição morta sai (`validar.py` é da T-013) |

---

## 4. Resolvidos

**38 achados**, com o texto inteiro em
[`docs/relatorios/achados-resolvidos.md`](../relatorios/achados-resolvidos.md).

Os ids continuam citáveis: `A-01` a `A-07` (auditoria A-001), `A-02b` a `A-10`
(auditoria A-002), `A-11` (auditoria de testes), e `A-12`, `A-13`, `A-15` a
`A-18`, `A-20`, `A-21`, `A-24` a `A-27`, `A-29`, `A-30`, `A-31`, `A-32`, `A-34`, `A-36`,
`A-37`, `A-39`, `A-40`, `A-41` (execução).

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
