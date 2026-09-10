# T-016 — TanStack Query, viewKey e URL

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-013, T-015 |
| **Bloqueia** | T-017 |
| **ADRs** | [0008](../adr/0008-tanstack-query.md), [0021](../adr/0021-viewkey-e-viewid.md) |
| **Requisitos** | RF-19 |

## Objetivo

Resolver os dois mecanismos que a v1 escreveu à mão — invalidação de pedido
superado e coalescing — e dar endereço à composição.

## Arquivos de propriedade exclusiva

```
web/src/app/rotas.tsx   web/src/App.tsx   web/src/estado/sessao.ts
web/src/testes/rotas.test.tsx   web/src/testes/query.test.tsx
api/tests/server/test_t016_ac.py
```

> **Corrigida na execução, por três motivos.**
>
> 1. `web/src/query/` e `web/src/state/` **nunca existiram** — as pastas foram
>    nomeadas `estado/` na T-001 (achado [A-25](./ACHADOS.md)), e os testes do
>    cliente moram em `web/src/testes/`.
> 2. **`App.tsx` entrou na lista.** É onde a rota se monta, e sem isso o AC-4
>    não tem como ser verdade. Nenhuma outra tarefa o declara.
> 3. **`api/tests/server/test_t016_ac.py` entrou na lista.** AC-5 e AC-6 são
>    regras que vivem no **servidor**; um teste no cliente provaria só que o
>    cliente pede — e o cliente é justamente quem não se pode obrigar a nada.
>    A lista original não cobria os próprios critérios da tarefa
>    ([A-36](./ACHADOS.md)).

## Escopo

### Faz
- `QueryClient` configurado; `queryKey` derivada de `[atorId, componenteId, params]`.
- Store observável mínimo para sessão do assistente: pergunta corrente, trace,
  composição ativa. **Só isso** (ADR-0008).
- Rota **`/v/:viewId`** — o endereço público é opaco e revogável; `view_key`
  nunca aparece em URL ([ADR-0021](../adr/0021-viewkey-e-viewid.md)).
- Ao abrir uma `viewKey`: **revalida o schema contra o catálogo do requisitante** e
  carrega sob a autenticação dele.

### Não faz
Compartilhamento entre usuários (ciclo 2, NO-6). Aqui só identidade e endereço.

## Critérios de aceite

> **Cada mecanismo foi sabotado de propósito para provar que o teste quebra:**
> `queryKey` com valor instável (coalescing e supersessão morrem juntos),
> `abrir_view` sem revalidar contra quem abre, e `viewIdDaUrl` devolvendo sempre
> `null`. As três reprovaram — 3, 2 e 6 testes respectivamente.

- [x] **AC-1** Toda `queryKey` contém o id do ator. Teste percorre as chaves geradas
      e falha se alguma não contiver. *(ADR-0008, risco de cache cruzado)*
      — já existia em `cache.test.ts`, varrendo o fonte inteiro. Reforçado por
      um teste de comportamento: o mesmo bloco para **outro ator** não
      reaproveita o cache. `query.test.tsx`.
- [x] **AC-2** Abrir a view A e imediatamente a B: a resposta tardia de A **não**
      sobrescreve B. *(invalidação de pedido superado)*
      — A fica pendente, B resolve, A responde depois com um valor que **não**
      pode aparecer na tela. `query.test.tsx`.
- [x] **AC-3** Quatro blocos da mesma entidade disparam **uma** requisição.
      *(coalescing)*
      — quatro blocos idênticos = 1 chamada, com os quatro desenhados. E o par
      negativo: `params` diferentes **não** são coalescidos — sem ele, uma chave
      constante coalesceria tudo e serviria o dado errado nos dois blocos.
- [x] **AC-4** Recarregar `/v/:viewId` reproduz a mesma tela. *(o bug do favorito
      da v1)*
      — desmontar e montar de novo (o F5) chega na mesma tela, porque o schema
      vem do servidor **pelo id** e não da memória do cliente, que o reload
      apaga. Com o contraponto: sem `viewId` na URL, não pede view nenhuma.
- [x] **AC-4b** `viewId` revogado devolve `nao_encontrado`; a `view_key` continua
      válida e o favorito sobrevive. *(ADR-0021)*
      — servidor: revogado e inexistente saem pela mesma porta (`views.py`).
      Cliente: a mesma mensagem para os dois, byte a byte — a tela não pode
      desfazer com duas frases o cuidado do ADR-0014. E a `viewKey` é
      independente do endereço: mesma composição com chaves em outra ordem gera
      a mesma chave, e o favorito continua encontrando a tela.
- [x] **AC-5** Uma `viewKey` criada por Marco, aberta por Odair, carrega sob a
      permissão de Odair — ou nega. **Nunca devolve dado de Marco.**
      *(negativo — ADR-0009, escalação de privilégio)*
      — duas propriedades, as duas testadas em `api/tests/server/test_t016_ac.py`:
      `GET /api/views/{id}` devolve **schema, nunca dado** (não há o que vazar),
      e o dado vem depois por `/api/componentes/{id}/dados`, sob a identidade de
      quem pediu — Odair recebe **403** no mesmo bloco em que Marco recebe 200.
- [x] **AC-6** Uma `viewKey` cujo schema referencia componente fora do catálogo do
      requisitante é rejeitada na abertura. *(negativo)*
      — `auditoria_trilha` (exige `auditoria.ler`) some para Odair. Sozinho, a
      abertura inteira é recusada; num schema misto, **o negado some e o
      permitido fica** — e o mesmo endereço traz os dois para Marco, o que prova
      que a filtragem é na abertura e não na gravação. A barreira também vale na
      entrada: Odair não consegue **salvar** uma view que ele não pode ver.
- [x] **AC-7** `arch:check` confirma que nenhum componente de apresentação importa
      TanStack Query.
      — regra 9 de `scripts/arch-check.ts`, com fixture de violação própria em
      `arch-check.test.ts`. Já existia e continua verde.

## Armadilhas

**AC-5 é o critério de segurança desta tarefa.** Endereço de view que carrega dado
com a permissão de quem criou é escalação de privilégio disfarçada de conveniência.

**Resolvido, e o desenho é o que torna simples:** o endereço não entrega dado
nenhum. `GET /api/views/{id}` devolve composição; o dado vem por outra rota, que
autoriza por registro com a identidade real (terceiro momento do ADR-0004). Não
há caminho em que a permissão de quem criou seja consultada.

## Decisão de implementação — rota sem biblioteca

`/v/:viewId` é **a única** rota com parâmetro do ciclo 1. Trazer um router seria
dependência nova para substituir um `match` em `location.pathname` — e
dependência se pergunta antes ([ADR-0028](../adr/0028-processo-de-decisao.md)).
`app/rotas.tsx` expõe quatro coisas (`viewIdDaUrl`, `caminhoDaView`, `irPara`,
`useRotaView`), pequenas o bastante para serem reimplementadas por cima de um
router sem tocar em mais nada. **A decisão se revisa na T-031**, que traz as
telas com rota e é onde haverá mais de um caso na mão.
