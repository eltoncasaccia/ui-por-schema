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

## Critérios de aceite

- [ ] **AC-1** O AC-6 da T-053 passa a rodar para **Marco, Helena e Cleide**, e a
      união cobre as **6 rotas sem parâmetro** — path, título e `aria-current`.
      A lista esperada continua **derivada do catálogo** de cada ator, nunca
      fixada no teste. Um teste registra que a união foi 6, e falha se uma rota
      nova entrar na tabela sem entrar no menu de ninguém.
- [ ] **AC-2** Helena libera um lote **pela interface**, em clique real: o lote
      sai da fila de quarentena, a tela reflete, e a trilha de auditoria registra
      a operação com a identidade dela. Contra `estoque_teste`, com o lote
      escolhido dinamicamente entre os que estiverem em quarentena.
- [ ] **AC-3** **(negativo)** Cleide, com a sessão dela, tentando o mesmo comando
      — não pelo menu, que ela não tem, mas forjando a requisição com o CSRF
      válido da própria sessão — é recusada pelo servidor, e o lote continua em
      quarentena. *A prova é a autorização no comando, não a ausência do botão.*
- [ ] **AC-4** **(negativo)** Segunda submissão com o **etag velho** devolve
      conflito e **nada é aplicado** — conferido relendo o lote depois.
- [ ] **AC-5** Uma composição compartilhada por Helena e aberta por Cleide em
      `/v/:viewId` **perde o bloco** que não está no catálogo dela, e a tela não
      quebra: o que sobra continua renderizando.
- [ ] **AC-6** Sair destrói a sessão de verdade: `/lotes` depois disso mostra a
      entrada, e uma requisição com o cookie antigo é recusada pelo servidor.
      *(negativo do lado do servidor, não só da tela)*
- [ ] **AC-7** **Sabotagem**, registrada no fechamento e não commitada: desligar
      a verificação de `If-Match` deixa o AC-4 vermelho; desligar a autorização
      do comando deixa o AC-3 vermelho.
- [ ] **AC-8** A corrida continua **sem escrever no banco de desenvolvimento** —
      contagens de `usuario`, `sessao`, `auditoria` e `movimento` do banco
      `estoque` idênticas antes e depois, com o `make up` no ar. Nenhum
      `waitForTimeout`, nenhuma chamada a modelo.

## Não faz

- **Exportação, paginação e `/usuarios`.** Ficam registrados como candidatos: o
  download real (`Content-Disposition`) e a rolagem infinita são browser-only,
  e `/usuarios` é a única tela sem teste de interface nenhum — mas nenhum dos
  três é navegação ou catálogo, que é o recorte do ADR-0033 §4.
- **Assistente com modelo real** — ADR-0013.
- **Firefox, WebKit, layout estreito** — continuam não verificados, por decisão.
- **Escopo por unidade (Ivo × Odair).** É dado, não navegação: o `CA-06` se
  fecha no `pytest`, não aqui.
