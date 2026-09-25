# T-057 — O que a T-053 não alcançou: as 6 rotas, a escrita por clique, a view compartilhada e o sair

| | |
|---|---|
| **Trilha** | D/E · interface e qualidade |
| **Tamanho** | M |
| **Depende de** | [T-053](./T-053-e2e-playwright.md) (a suíte existe), [T-051](./T-051-etag-por-linha.md) (etag por linha) |
| **ADRs** | [0033](../adr/0033-e2e-playwright-banco-proprio.md), [0003](../adr/0003-catalogo-por-ator.md), [0004](../adr/0004-autorizacao-em-tres-momentos.md), [0019](../adr/0019-autenticacao-e-cadastro.md) |
| **RN** | nenhuma nova — as regras de liberação já são da T-027 |
| **Origem** | achado [A-48](./ACHADOS.md), de 2026-09-25: plano gerado pela skill `e2e-nav-test` cruzado com a cobertura real da T-053 |
| **Escrita em** | 2026-09-25 |

## Por que existe

**O buraco está dentro da T-053, e é de cobertura, não de código.** O AC-6 dela
roda com o Marco, e o catálogo do diretor tem só duas das seis rotas sem
parâmetro. O critério foi cumprido ao pé da letra — *"cada item de rota do menu
de Marco"* — e mesmo assim `/quarentena`, `/controlados`, `/saida` e
`/recebimento/novo` **nunca têm path e título conferidos por ninguém**.

```
                          rotas no menu, por catálogo
Marco   (diretor)    →  /lotes  /vencimento                                  2 de 6
Helena  (RT)         →  /lotes  /vencimento  /quarentena  /controlados       4 de 6
Cleide  (conferente) →  /lotes  /vencimento  /saida  /recebimento/novo       4 de 6
```

Três personas cobrem as seis. É a correção mais barata desta tarefa, e a que
deveria ter estado na T-053.

**A taxonomia da negativa veio de rodar a skill de verdade.** A corrida de
2026-09-25 gerou 70 fluxos e reprovou 10, todos do tipo *acesso negado por URL*
— e as 10 falhas eram **premissa errada do teste**, não defeito do sistema. O
AC-9 existe para essa lição não se perder: o que a interface esconde e o que o
servidor recusa são coisas diferentes, e é justamente a tese do projeto.

Os outros três fluxos são os únicos que a comparação apontou como **impossíveis
de provar nas outras camadas** — o resto da lista da skill ou já tem teste, ou
está excluído por decisão (ADR-0013 para modelo, ADR-0033 para Firefox e layout
estreito).

## O que já foi conferido

- **O diretor não tem componente de escrita operacional.** Marco não vê
  `quarentena_liberar`, `controlado_autorizar`, `lote_status_acao`,
  `movimento_saida` nem `recebimento_registrar` — separação de funções, medida
  no `/api/catalogo` das 7 personas em 2026-09-25.
- **Escrita pela interface nunca foi exercida num clique real.** O caminho
  `CSRF → cookie → etag → If-Match → comando` foi verificado por `curl`
  (T-050/T-051), por `pytest` e por `vitest` com mock (T-049) — três camadas,
  nenhuma delas o navegador.
- **`/v/:viewId` só tem prova de servidor** ([A-36](./ACHADOS.md)): abrir view
  não devolve dado, e bloco fora do catálogo de quem abre some. No navegador,
  com dois atores de verdade, nunca foi testado.
- **Sair tem um teste em jsdom**, que não tem cookie. Destruir sessão e ser
  recusado na rota seguinte é comportamento de navegador + servidor.
- **Os dois tipos de negativa por URL foram medidos no navegador** (corrida da
  skill `e2e-nav-test`, 2026-09-25, 70 fluxos, 60 passaram). Ausência do menu
  **não** implica negativa na URL, e o sistema está certo nos três casos:

  | Rota | Quem não tem | O que acontece ao digitar a URL |
  |---|---|---|
  | `/recebimento/novo` · `/controlados` | o componente da rota | **negado no carregamento**: "Sem acesso a este componente." |
  | `/quarentena` | só a ação (`quarentena_liberar`) | **carrega a fila** — `quarentena_fila` é `lote.ler`, que todos têm. O menu esconde a entrada porque a *razão* dela é liberar |
  | `/saida` | o componente (`movimento_saida`) | **portão de formulário**: "Informe o id do produto para começar a separação", antes de qualquer busca. A recusa só chega ao submeter |

- **Não falta lote para escrever:** o `estoque_teste` tem **47 lotes em
  quarentena**, e o número cresce a cada corrida do `pytest` (desenho do
  [A-44](./ACHADOS.md)). O seed foi medido como **idempotente** — `make db-teste`
  duas vezes deixou 247 lotes, 47 em quarentena e 1.599 movimentos inalterados.

## Arquivos de propriedade exclusiva

```
web/e2e/**
web/playwright.config.ts
```

> A T-053 está fechada, e a propriedade destes arquivos passa para esta tarefa.
> Nenhuma outra tarefa aberta os declara.

**Acrescentados durante a execução, com registro (achado [A-49](./ACHADOS.md),
já resolvido):** o AC-2 provou, com um clique real, que a escrita de um
componente aberto por ROTA nunca chegava ao servidor — `TelaOperacao.tsx` e
`TelaSaida.tsx` (T-031, fechada) montam o `Bloco` sem `comandos`, campo que só
existe quando o `Bloco` vem de `/api/assistente/compor` ou `/api/views/{id}`
(T-049). Sem os quatro arquivos abaixo, o AC-2 e o AC-9 (caso "portão de
formulário") ficariam permanentemente em branco:

```
api/src/estoque/server/rotas/catalogo.py    comandos por entrada do catálogo
web/src/api.ts                              EntradaCatalogo.comandos
web/src/app/telas/TelaOperacao.tsx          anexa comandos ao Bloco da rota
web/src/app/telas/TelaSaida.tsx             idem, para /saida
```

Nenhum dos quatro tem tarefa aberta que os declare (T-031, T-045, T-047, T-049
e T-054, que já os tocaram, estão todas ✅). A mudança é aditiva — `comandos`
é um campo opcional novo, mesmo tratamento que `exportavel` (T-054) — e não
mexe na assinatura de `ComponentDef`/`CommandDef` (CONTRATOS §5, congelada).

## Critérios de aceite

- [x] **AC-1** O AC-6 da T-053 passa a rodar para **Marco, Helena e Cleide**, e a
      união cobre as **6 rotas sem parâmetro** — path, título e `aria-current`.
      A lista esperada continua **derivada do catálogo** de cada ator, nunca
      fixada no teste. Um teste registra que a união foi 6, e falha se uma rota
      nova entrar na tabela sem entrar no menu de ninguém. `navegacao.spec.ts`
      — teste parametrizado pelas três personas, mais o teste de união.
- [x] **AC-2** Helena libera um lote **pela interface**, em clique real: o lote
      sai da fila de quarentena, a tela reflete, e a trilha de auditoria registra
      a operação com a identidade dela. Contra `estoque_teste`, com o lote
      escolhido dinamicamente entre os que estiverem em quarentena.
      `liberacao.spec.ts`. **Achou o A-49** (escrita por rota nunca chegava ao
      servidor) na primeira tentativa — corrigido, ver acima.
- [x] **AC-3** **(negativo)** Cleide, com a sessão dela, tentando o mesmo comando
      — não pelo menu, que ela não tem, mas forjando a requisição com o CSRF
      válido da própria sessão — é recusada pelo servidor, e o lote continua em
      quarentena. *A prova é a autorização no comando, não a ausência do botão.*
      `liberacao.spec.ts`.
- [x] **AC-4** **(negativo)** Segunda submissão com o **etag velho** devolve
      conflito e **nada é aplicado** — conferido relendo o lote depois.
      `liberacao.spec.ts`. A asserção checa a **mensagem** do `If-Match`
      ("O registro mudou desde a leitura"), não só o código `conflito` — a
      sabotagem do AC-7 provou que só o código não discrimina (a máquina de
      estados devolve `conflito` por outro motivo quando o `If-Match` está
      desligado).
- [x] **AC-5** Uma composição compartilhada por Helena e aberta por Cleide em
      `/v/:viewId` **perde o bloco** que não está no catálogo dela, e a tela não
      quebra: o que sobra continua renderizando. `compartilhamento.spec.ts`.
- [x] **AC-6** Sair destrói a sessão de verdade: `/lotes` depois disso mostra a
      entrada, e uma requisição com o cookie antigo é recusada pelo servidor.
      *(negativo do lado do servidor, não só da tela)* `entrada.spec.ts`.
- [x] **AC-9** **Os dois tipos de negativa por URL, cada um com o teste que lhe
      cabe** — porque tratá-los como um só foi o erro que a corrida da skill
      cometeu, e um teste que espera a mensagem errada falha sem que nada esteja
      quebrado:
      - **negado no carregamento** — Marco em `/recebimento/novo` e em
        `/controlados`: a mensagem do servidor aparece e nenhum dado do
        componente é mostrado;
      - **lido sem poder agir** — Marco em `/quarentena`: a fila **carrega**
        (ele tem `lote.ler`), e o que se afirma é a ausência de caminho para
        liberar: nenhum botão de liberação na tela, nem desabilitado;
      - **portão de formulário** — Marco em `/saida`: o formulário aparece, e o
        teste **submete um produto**, porque é só aí que a recusa do servidor
        existe. *(negativo — sem a submissão, este caso não prova nada)*
      `acesso-por-url.spec.ts`, os quatro casos (as duas rotas do primeiro tipo
      em testes separados).
- [x] **AC-10** A pergunta que o AC-9 levanta fica respondida no fechamento:
      oferecer o formulário de `/saida` a quem não tem `movimento_saida` é
      aceitável, ou vira achado? Não há leitura indevida — a recusa é do
      servidor —, mas o caminho é oferecido. **Decisão registrada, não
      improvisada.**

      **Decisão: aceitável, não é achado.** É exatamente o desenho do
      ADR-0004 posto em prática: os dois primeiros momentos de autorização
      (catálogo filtrado, revalidação de schema) controlam o que é
      *oferecido*, e só o terceiro (autorização em cada `load`/`command`)
      controla o que é *acessível* — "esconder não é controlar" (comentário
      de `pipeline.py`). O portão de `/saida` pede um id de produto, que não é
      dado sensível (não é id de lote, não é saldo, não é custo); ao submeter,
      a única coisa que Marco recebe é "Sem acesso a este componente." — a
      mesma mensagem que `/controlados` e `/recebimento/novo` já mostram sem
      pedir nada primeiro. Mesmo padrão que `quarentena_liberar.pode_decidir`
      já usa quando o lote saiu da quarentena: mostrar a forma da decisão,
      recusar a decisão em si. Virar achado exigiria uma segunda checagem de
      autorização SÓ para decidir se o formulário aparece — autorização
      duplicada, no lugar exato que o ADR-0004 diz para não duplicar.
- [x] **AC-7** **Sabotagem**, registrada no fechamento e não commitada: desligar
      a verificação de `If-Match` deixa o AC-4 vermelho; desligar a autorização
      do comando deixa o AC-3 vermelho.

      **Feita e revertida nesta sessão**, `git diff` limpo depois — não é
      commit, é o que a sessão observou:
      - `_conferir_if_match`: `return` logo na entrada → AC-4 fica vermelho,
        mas por um caminho **inesperado**: em vez de aceitar a segunda
        submissão, a máquina de estados (`_transicionar`) recusa com
        `conflito` por outro motivo ("Esta ação não se aplica a um lote em
        liberado."), porque a primeira submissão já mudou o status. A
        asserção original checava só o código `conflito` e teria passado
        mesmo sabotada — **corrigida** para checar a mensagem específica do
        `If-Match`, que só a checagem de etag produz.
      - `autorizar_ou_falhar(...)` do comando comentada → AC-3 fica vermelho:
        403 esperado, 422 recebido (a requisição segue até a validação de
        schema, sem parar na autorização).
- [x] **AC-8** A corrida continua **sem escrever no banco de desenvolvimento** —
      contagens de `usuario`, `sessao`, `auditoria` e `movimento` do banco
      `estoque` idênticas antes e depois, com o `make up` no ar. Nenhum
      `waitForTimeout`, nenhuma chamada a modelo.

      Verificado com o `make up` real no ar: `usuario=7, sessao=13,
      auditoria=22, movimento=269` antes e depois da suíte inteira (26
      testes, `make db-local` de novo depois do `make up` — a armadilha do
      `CLAUDE.md` §3). `grep -rn waitForTimeout web/e2e/` sem resultado. O
      `webServer` do `playwright.config.ts` não muda: sem chave de provedor,
      como o ADR-0033 já exigia.

## Não faz

- **Exportação, paginação e `/usuarios`.** Ficam registrados como candidatos: o
  download real (`Content-Disposition`) e a rolagem infinita são browser-only,
  e `/usuarios` é a única tela sem teste de interface nenhum — mas nenhum dos
  três é navegação ou catálogo, que é o recorte do ADR-0033 §4.
- **Assistente com modelo real** — ADR-0013.
- **Firefox, WebKit, layout estreito** — continuam não verificados, por decisão.
- **Escopo por unidade (Ivo × Odair).** É dado, não navegação: o `CA-06` se
  fecha no `pytest`, não aqui.
