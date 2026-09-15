# Board — Ciclo 1

**39 tarefas · 6 ondas · 5 trilhas · 2 linguagens.**
Regras: [Acordo de Trabalho](./README.md) · Interfaces: [CONTRATOS](./CONTRATOS.md)
Ondas, trilhas e grafo: [PLANO](./PLANO.md) · Achados: [ACHADOS](./ACHADOS.md)

Legenda: `⬜ disponível` · `🔵 em andamento` · `🔴 bloqueada` · `🟡 em revisão` · `✅ concluída`

> **Assumir tarefa = editar a linha dela nesta tabela.** Esse commit é o lock.
>
> **Concluir = marcar os ACs verificados no arquivo da tarefa E mudar o status
> aqui, no MESMO commit.** Este board já foi ficção uma vez: dizia que nada
> tinha sido feito enquanto 19 tarefas estavam prontas
> ([A-002](../relatorios/A-002-auditoria-de-execucao.md)). O detalhe por tarefa
> está em [PROGRESSO](./PROGRESSO.md).

---

## 0. Esperando decisão do cliente

**Quatro perguntas paradas, e nenhuma é da equipe.** Estavam enterradas numa
tabela de 42 achados que só auditoria lia inteira — registrado e invisível é o
mesmo que não registrado. Ficam aqui até serem respondidas.

| # | Pergunta | Trava |
|---|---|---|
| [A-19](./ACHADOS.md) | As **três** listas de motivos derivadas do enum estão certas? Saída (T-028), estorno e descarte (T-029). `RN-M05` exige lista fechada por tipo e não há nenhuma em documento | ~~T-029~~ — ela fechou com as listas derivadas, como a T-028: a regra está implementada e testada; falta o cliente confirmar **quais** valores |
| [A-23](./ACHADOS.md) | O livro de controlados **exportável** (`RN-C05`) entra no ciclo 1? Custa +1 no catálogo e uma tarefa | `RN-C05` |
| [A-33](./ACHADOS.md) | O `status` do recebimento basta como "conferência registrada", ou `RN-R03` exige integridade e validade como itens separados, com coluna? | ~~T-026~~ — ela fechou sem a resposta: o checklist de `RN-R03` já existe na **liberação** (T-027, `EntradaLiberacao`). O que segue em aberto é o `recebimento_detalhe` **exibir** os itens conferidos, e uma auditoria de `RN-R03` ponta a ponta |
| [A-35](./ACHADOS.md) | Auditar **navegação** (catálogo, identidade) é exigência regulatória, ou basta auditar leitura de dado? | recorte de `CS-05` |

---

## 1. Tarefas

### W0 — Ambiente e contratos · serial

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-035](./T-035-docker-compose.md) | **Docker Compose, Makefile, README** | E | M | — | ✅ |
| [T-001](./T-001-bootstrap.md) | Bootstrap `api/` e `web/`, CI | E | M | T-035 | ✅ |
| [T-002](./T-002-dominio-tipos-erros.md) | Domínio: 7 tipos, erros, identidade | A | M | T-001 | ✅ |
| [T-003](./T-003-contrato-registry.md) | Contrato do registry (sem `render`) | C | M | T-002 | ✅ |
| [T-004](./T-004-contratos-de-borda.md) | Schema, `viewKey`/`viewId`, envelope | C | M | T-002, T-003 | ✅ |
| [T-039](./T-039-codegen-e-bijecao.md) | **Codegen OpenAPI→TS + bijeção** · congela | C | M | T-003, T-004 | ✅ |
| [T-005](./T-005-arch-check.md) | Verificadores: `import-linter` + `arch:check` | E | M | T-002 | ✅ |

### W1 — Núcleo · até 13 sessões

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-036](./T-036-schema-postgres.md) | **Schema Postgres, migrações, restrições** | A | G | T-002, T-035 | ✅ |
| [T-006](./T-006-fixtures.md) | Dados da Bertoni (seed determinístico) | A | M | T-036 | ✅ |
| [T-007](./T-007-repositorios.md) | Porta de dados e repositórios SQLAlchemy | A | M | T-036 | ✅ |
| [T-008](./T-008-regras-puras.md) | FEFO, validade, **status efetivo**, saldo | A | M | T-002 | ✅ |
| [T-009](./T-009-motor-de-permissao.md) | Motor de permissão e escopo | B | M | T-004 | ✅ |
| [T-010](./T-010-auditoria.md) | Trilha de auditoria append-only | B | M | T-004 | ✅ |
| [T-037](./T-037-autenticacao.md) | **Autenticação, sessão, CSRF** | B | G | T-004, T-036 | ✅ |
| [T-011](./T-011-servidor.md) | Servidor FastAPI, autorização por registro | B | G | T-009, T-010, T-037 | ✅ |
| [T-012](./T-012-catalogo.md) | Registry runtime e catálogo por ator | C | M | T-004, T-009 | ✅ |
| [T-013](./T-013-validador-schema.md) | Validador de schema e revalidação | C | M | T-012 | ✅ |
| [T-014](./T-014-adapter-modelo.md) | Adapter Claude e Execution Trace | C | M | T-004 | ✅ |
| [T-015](./T-015-motor-de-render.md) | Motor de render e política de layout | D | M | T-039 | ✅ |
| [T-016](./T-016-query-e-viewkey.md) | TanStack Query, `viewId`, rotas | D | M | T-013, T-015 | ✅ |

> **T-016 fechou, e com ela a W1 inteira.** A rota `/v/:viewId` existe
> (`web/src/app/rotas.tsx`), **sem biblioteca de rota** — é a única rota com
> parâmetro do ciclo 1, e a decisão se revisa na T-031. AC-5 e AC-6, que só
> existem no servidor, ganharam teste em `api/tests/server/test_t016_ac.py`:
> abrir uma view **não devolve dado**, e o bloco fora do catálogo de quem abre
> some. Lista de arquivos da tarefa corrigida ([A-36](./ACHADOS.md)).

> **T-011 fechou.** Os 8 ACs passaram a ser verificados **por HTTP contra o app
> real** — antes, três deles eram `inspect.getsource` afirmando que o handler
> existe no código. **`CS-06` não existia** (achado [A-34](./ACHADOS.md)): a
> T-040 entregou rate limit no *login* e o rotulou CS-06, mas o requisito é o
> endpoint do assistente — implementado aqui, com teto por ator conferido antes
> de falar com o modelo. AC-8 verificado no recorte "leitura de dado de domínio"
> ([A-35](./ACHADOS.md)). As quatro proteções foram sabotadas de propósito e os
> testes reprovaram nas quatro.

### W2 — Furo de risco · 1 sessão

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-017](./T-017-spike-medicao.md) | **SPIKE: medição com modelo real** | C | M | T-011, T-014, T-016 | ✅ |

> **A tarefa que pode matar o projeto**, e por isso está aqui e não no fim.
> **Nenhuma tarefa de W3 começa antes de o relatório R-001 ser lido.**
> R-001 entregue em 2026-09-09 ([relatório](../relatorios/R-001-medicao-modelo-real.md)):
> 100% de schema válido nos dois modelos e nos dois modos — **seguir**. Lacunas
> do spike (AC-1, 17 casos em vez de 30) em R-001 §8 e achado A-08b.

### W3 — Leitura · até 7 sessões · 15 componentes

| Id | Tarefa | Componentes | Tam. | Status |
|---|---|---|---|---|
| [T-018](./T-018-componentes-lote.md) | Lote | `lote_lista` `lote_detalhe` `lote_movimentos` `quarentena_fila` | G | ✅ |
| [T-019](./T-019-componentes-produto.md) | Produto e custo restrito | `produto_ficha` `produto_saldo_por_unidade` | M | ✅ |
| [T-020](./T-020-vencimento-indicador.md) | Vencimento, indicador e curva | `fila_vencimento` `estoque_indicador` `vencimento_grafico` | G | ✅ |
| [T-021](./T-021-rastreabilidade.md) | Rastreabilidade `CA-01` | `rastreabilidade` | M | ✅ |

> **T-019 fechou com AC-7 em branco:** `RN-P06` (mín/máx por unidade) não tem
> armazenamento no sistema. Achado [A-30](./ACHADOS.md), tarefa
> [T-046](./T-046-minimo-maximo-por-unidade.md).
>
> **T-021 fechou:** o recorte de período do `RN-D04` foi feito no `load` porque
> `RepoMovimento.por_cliente` ignora `de`/`ate` (achado [A-31](./ACHADOS.md),
> conserto em T-007/T-042). `RNF-01` medido de verdade fica para T-034.
| [T-022](./T-022-recebimento-leitura.md) | Recebimento | `recebimento_lista` `recebimento_detalhe` | M | ✅ |
| [T-023](./T-023-temperatura.md) | Cadeia fria `CA-07` | `temperatura_historico` `temperatura_excursoes` | M | ✅ |
| [T-024](./T-024-movimento-auditoria.md) | Movimento e trilha | `movimento_lista` `auditoria_trilha` | M | ✅ |
| [T-047](./T-047-repos-recebimento-temperatura.md) | **Repos de recebimento e temperatura** — escopo deferido da T-007 ([A-32](./ACHADOS.md)) | G | ✅ |

> **T-047 fechou:** `RepoRecebimentoSQL` / `RepoTemperaturaSQL` existem, `deps.py`
> não passa mais `None`, o seed tem 6 recebimentos (divergência, controlado,
> termolábil), e a bateria de escopo roda contra fake **e** banco. **T-022 e
> T-023 desbloqueadas.** "Lotes gerados" (`lote.recebimento_id`) segue sem
> schema — item descopado da T-022.
>
> **T-022 fechou:** `recebimento_lista` (params `unidade_id?` `status?`
> `periodo` — `de`/`ate` viraram enum, risco R-5) e `recebimento_detalhe`
> registrados, com escopo negativo por Odair, `status` enum fechado e custo
> invisível provados. **AC-1 em branco** — "gerou lote em quarentena" depende de
> `lote.recebimento_id`, que não existe. **RN-R03 sem armazenamento** para
> integridade/validade como conferências registradas: achado
> [A-33](./ACHADOS.md).
>
> **T-023 fechou:** `temperatura_historico` (série com faixa 2–8 °C, agregação
> automática acima de 480 pontos, `csv` no viewmodel) e `temperatura_excursoes`
> (ocorrências fora da faixa + lotes presentes até o fim da janela, `RN-F04`).
> AC-1..AC-6 verificados. **Exportação (AC-2) é client-side a partir do
> viewmodel** — não há endpoint de export no ciclo 1 ([A-23](./ACHADOS.md)); os
> mesmos dados da tela, por construção.

### W4 — Escrita · até 5 sessões · 7 componentes

| Id | Tarefa | Componentes | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-025](./T-025-pipeline-de-comando.md) | Pipeline de comando e confirmação | *(nenhum — ver nota)* | G | T-011, T-015 | ✅ |
| [T-026](./T-026-recebimento-registrar.md) | Registrar recebimento | `recebimento_registrar` | G | T-025, T-022, T-048 | ✅ |
| [T-027](./T-027-quarentena-e-status.md) | Quarentena e status | `quarentena_liberar` `lote_status_acao` | G | T-025, T-018 | ✅ |
| [T-028](./T-028-saida-fefo.md) | Saída com FEFO | `movimento_saida` | G | T-025, T-008 | ✅ |
| [T-029](./T-029-estorno-descarte.md) | Estorno e descarte | `movimento_estorno` `movimento_descarte` | M | T-025, T-024 | ✅ |
| [T-030](./T-030-controlado-autorizar.md) | Dupla identificação `CA-04` | `controlado_autorizar` | G | T-028, T-024 | ✅ |

> **T-029 fechou, e com ela a W4 inteira.** `CA-08` deixou de ser promessa: não
> há rota que apague ou substitua nada — a varredura sai do `openapi()` do app
> real, e uma rota `DELETE` acrescentada de propósito reprovou o AC-1 **e** o
> AC-2. Corrigir se faz por estorno, que é `INSERT`, e o original fica **byte a
> byte** igual. O descarte é o segundo fluxo de duas pessoas do ciclo 1 (§4.1:
> Gerente + RT): **nem o Diretor descarta**, mesmo tendo `movimento.descartar` na
> matriz do §6 — a permissão deixa entrar, a tabela de estados recusa.
> **Achado novo, [A-38](./ACHADOS.md):** estorno de **entrada** não tem
> representação no esquema — o sinal de `estorno` é fixo e positivo na view
> `saldo_lote` (migração 0001, congelada), e gravá-lo somaria de novo o que se
> queria desfazer. Só saída se estorna no ciclo 1, e o comando diz isso.

> **T-026 fechou, e com ela a `US-02`.** O leitor de código de barras funciona:
> o `ean` é **param do componente**, o `load` resolve por `RepoProduto.por_ean`
> ([T-048](./T-048-porta-produto-por-ean.md)), e a tela mantém o foco no scan
> entre leituras — que é o que separa "funciona na demonstração" de "funciona na
> esteira". `RN-R01` em três camadas, e as nove regras citadas com par negativo.
> **Fora de escopo, anotado:** `lote.recebimento_id` segue sem schema ([A-32](./ACHADOS.md)),
> e o formulário não avisa sobre `RN-P02`/`RN-P03` antes porque exigiria
> `RepoUnidade` — o comando recusa, e por ADR-0004 o cliente nunca foi a garantia.

> **`confirm_action` saiu do catálogo** (achado A-05). Confirmação é decisão do
> motor de render diante de `CommandDef.confirm`, não composição que o modelo
> escolhe — mesmo tratamento de `sem_acesso`.

### Abertas pela auditoria A-002

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-040](./T-040-csrf-e-rate-limit.md) | **CSRF e rate limit** — segurança prometida e ausente | B | M | T-037 | ✅ |
| [T-041](./T-041-ci.md) | CI no GitHub Actions | E | P | T-001 | ✅ |
| [T-042](./T-042-contract-test-repositorios.md) | **Contract test** fake ↔ repositório real — bateria única, 12 métodos cobertos, fecha A-11 e A-31, decide A-39 | A | M | T-007 | ✅ |
| [T-043](./T-043-instrumentacao-ao-vivo.md) | Instrumentação ao vivo do pipeline do assistente (duração real de span) — tarefa escrita na execução; fecha A-10 | C | M | T-011 | ✅ |
| [T-044](./T-044-relatorio-movimentacao.md) | `relatorio_movimentacao` — relatório parametrizado ([ADR-0029](../adr/0029-relatorio-como-componente.md)) | C | M | T-024 | ✅ |

| [T-045](./T-045-borda-http-por-router.md) | **Borda HTTP por router** — `app.py` tinha 817 linhas e 4 tarefas escreviam nele ([ADR-0032](../adr/0032-borda-http-por-router.md)) | E | M | — | ✅ |

| [T-048](./T-048-porta-produto-por-ean.md) | **`RepoProduto.por_ean`** — o leitor de código de barras não tinha para onde apontar ([A-37](./ACHADOS.md)). **Tarefa de contrato**, aditiva: CONTRATOS §4 rev. 2.3 | A | P | T-007, T-036 | ✅ |

| [T-046](./T-046-minimo-maximo-por-unidade.md) | **Mín/máx por produto e unidade** (`RN-P06`) — sem armazenamento no sistema; é também tarefa de contrato (CONTRATOS §4). Aberta pela T-019 ([A-30](./ACHADOS.md)) | A | M | T-002, T-007, T-036, T-006 | ✅ |
| [T-049](./T-049-dispatcher-de-comando.md) | **Dispatcher de comando no cliente** — nenhum botão de escrita chama o servidor. Tarefa de contrato (CONTRATOS §6/§8). Aberta pela leitura da T-031 ([A-40](./ACHADOS.md)) | B/D | G | T-011, T-025..T-030 | ✅ |
| [T-050](./T-050-etag-na-leitura.md) | **Etag na leitura** — 6 dos 7 comandos exigem `If-Match` e nenhuma leitura devolve etag. Aberta testando a T-049 contra o servidor real ([A-41](./ACHADOS.md)) | A/C | G | T-049 | ✅ |
| [T-051](./T-051-etag-multiplo-e-porta.md) | **Etag por linha** — `movimento_saida`/`movimento_descarte`/`movimento_estorno` (a pessoa escolhe o candidato depois de ler) e `controlado_autorizar` (bloc-level). Cortada da T-050 no levantamento; a "porta faltando" do levantamento original estava errada, corrigido no arquivo | A/C | G | T-050 | ✅ |

### Abertas em 2026-09-14 — banco de teste e ponta a ponta

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-052](./T-052-banco-de-teste-isolado.md) | **Banco de teste isolado** — os testes escreviam no banco de desenvolvimento, e append-only não se limpa ([A-44](./ACHADOS.md)) | E | M | — | 🔵 Claude · 2026-09-14 |
| [T-053](./T-053-e2e-playwright.md) | **Testes de ponta a ponta com Playwright** — navegação, sessão real e catálogo por ator no navegador ([ADR-0033](../adr/0033-e2e-playwright-banco-proprio.md)); prende o bug do menu ([A-45](./ACHADOS.md)) num `test.fail()` | E/D | M | T-052 | ⬜ |

### W5 — Garantias e fechamento · até 4 sessões

| Id | Tarefa | Trilha | Tam. | Depende | Status |
|---|---|---|---|---|---|
| [T-031](./T-031-telas-com-rota.md) | Superfície tradicional: telas com rota | D | G | T-026, T-027, T-028, T-049, T-050, T-051 | ✅ |
| [T-038](./T-038-gestao-de-usuarios.md) | **Gestão de usuários** (fora do catálogo) — `POST`, não `PATCH` (CA-08) | D | M | T-037, T-031 | ✅ |

> **T-031 fechou.** `react-router-dom` adotado só para as 8 rotas de operação
> (`app/layout/Roteador.tsx`, `BrowserRouter` autocontido) — `/` e `/v/:viewId`
> continuam sob o `useRotaView` da T-016, inalterado. AC-1 provado por
> **igualdade de HTML** entre a rota e o assistente com o bloco equivalente, não
> só "os dois usam a mesma função". Achado sem entrada em `ACHADOS.md` (não é
> ambiguidade de regra): `movimento_saida.produto_id` é obrigatório e `/saida`
> não tem `:id` — não há busca de produto no catálogo do ciclo 1, e a tela pede
> o id digitado (mesmo padrão de `lote_detalhe`/`quarentena_liberar`), com
> `?produto_id=` para link direto. Detalhe em
> [T-031](./T-031-telas-com-rota.md).
| [T-032](./T-032-suite-de-avaliacao.md) | Suíte de avaliação, 40 perguntas | E | G | T-017, W3 | 🟡 |
| [T-033](./T-033-testes-de-seguranca.md) | Segurança CS-01 a CS-06 | E | G | W3, W4 | ✅ |
| [T-034](./T-034-fechamento.md) | Relatório de fechamento | E | M | T-031, T-032, T-033 | ⬜ |

> **T-033 fechou, e o CS-04 passou.** Nenhum dado do banco chega ao modelo:
> prompt e JSON Schema idênticos **byte a byte** com e sem dado hostil — inclusive
> no nome do próprio ator —, canário provando que o dado estava no caminho dele,
> e a mesma igualdade com `qwen2.5:7b` real. CS-01/02/05 ganharam o que faltava
> (schema gigante, catálogo exato por persona, custo plantado na trilha real).
> Quatro proteções sabotadas, quatro vermelhos. **Dois achados sem dono**, com
> recomendação: [A-42](./ACHADOS.md) — `titulo` sem teto, e é onde o modelo real
> obedece à injeção colada na pergunta (tarefa de contrato, CONTRATOS §7) — e
> [A-43](./ACHADOS.md) — escrita composta com leitura é aceita porque a checagem
> do ADR-0005 em `validar.py:113` nunca dispara (vira emenda de ADR). Relatório:
> [R-003](../relatorios/R-003-seguranca-ciclo-1.md). **T-034 espera só a T-032.**

> **As quatro tarefas abertas foram revisadas em 2026-09-10** — arquivos, listas
> fechadas, qual exemplar imitar e o que já está provado em outro lugar. O que a
> revisão mudou, e que ninguém descobriria sem executar:
>
> - **T-031 abre com uma pergunta:** não há biblioteca de rota no projeto, e ela
>   acrescenta 8 rotas com parâmetro e histórico. Adotar `react-router-dom` é
>   dependência nova, e dependência se pergunta antes (ADR-0028). **A tarefa não
>   começa sem essa resposta.** A rota `/controlados` entrou na lista, agora que
>   a W4 fechou; estorno e descarte ficaram de fora, com o motivo escrito.
>   **Decisão registrada em 2026-09-14: adotar `react-router-dom`.**
> - **T-031 ganhou uma dependência nova, e maior que a pergunta acima:**
>   nenhum botão de escrita chama o servidor, em nenhuma das duas superfícies —
>   as cinco tarefas de escrita (T-026 a T-030) entregaram só a view, e ninguém
>   cortou a tarefa que liga o clique ao `POST /api/comandos/{nome}`. Achado
>   [A-40](../relatorios/achados-resolvidos.md), tarefa
>   [T-049](./T-049-dispatcher-de-comando.md), **fechada**. Revelou uma
>   segunda: 6 dos 7 comandos exigem `If-Match`, e nenhuma leitura devolvia
>   etag — achado [A-41](../relatorios/achados-resolvidos.md), tarefas
>   [T-050](./T-050-etag-na-leitura.md) (`quarentena_liberar`,
>   `lote_status_acao`) e [T-051](./T-051-etag-multiplo-e-porta.md)
>   (`controlado_autorizar`, e etag POR LINHA para `movimento_saida`,
>   `movimento_descarte`, `movimento_estorno`), **as duas fechadas**. As
>   quatro rotas de escrita da T-031 estão destrancadas.
> - **T-042 ganhou escopo:** o conserto do `por_cliente` (A-31) é dela, porque é
>   o adaptador. E ela vai encontrar o [A-39](./ACHADOS.md).
> - **T-044 tem dois furos que a tarefa não previa:** o teto de 500 do
>   `RepoMovimento.listar` (A-39) e o caminho do custo, que atravessa três
>   entidades sem `RepoLote.por_ids`. Os dois com recomendação registrada.
> - **T-046 tem precedente exato na T-048** — migração `0007`, CONTRATOS rev.
>   2.4 — e a faixa passa a ser exibida em `produto_saldo_por_unidade`, não em
>   `produto_ficha`: `RN-P06` é por par (produto, unidade), e a ficha não tem
>   eixo de unidade.

---

## 2. Contagem de catálogo

Teto de 25 ([ADR-0011](../adr/0011-teto-de-catalogo.md)), verificado por `RNF-08`.

| Onda | Componentes | Acumulado |
|---|---|---|
| W3 | 15 de leitura + `vencimento_grafico` | 16 |
| W4 | 7 de escrita | **23** |

> **T-044 acrescenta +1 ao catálogo: 24, folga 1.** Um segundo relatório estoura
> o teto de 25 e vira discussão de escopo (ADR-0011).

**Registrados hoje: 24** — `relatorio_movimentacao` (T-044), `fila_vencimento` `estoque_indicador` `vencimento_grafico`
(T-020), `lote_lista` `lote_detalhe` `lote_movimentos` `quarentena_fila` (T-018),
`quarentena_liberar` `lote_status_acao` (T-027), `movimento_saida` (T-028),
`controlado_autorizar` (T-030), `movimento_lista` `auditoria_trilha` (T-024),
`produto_ficha` `produto_saldo_por_unidade` (T-019), `rastreabilidade` (T-021),
`recebimento_lista` `recebimento_detalhe` (T-022), `temperatura_historico`
`temperatura_excursoes` (T-023), `recebimento_registrar` (T-026) e
`movimento_estorno` `movimento_descarte` (T-029).
**7 de escrita, teto 25.**

**24 registrados, folga de 1** — a T-044 entrou com `relatorio_movimentacao`.
Um segundo relatório estoura o teto e vira discussão de escopo (ADR-0011).
Toda tarefa que registra componente atualiza esta tabela no mesmo commit. Acima
de 25 o build quebra, e a discussão é de escopo.

---
