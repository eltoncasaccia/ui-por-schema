# A-002 — Auditoria de execução

| | |
|---|---|
| **Data** | 2026-09-08 |
| **Motivo** | O BOARD dizia que nada tinha sido feito enquanto boa parte estava pronta |
| **Método** | Código e testes conferidos contra as 39 tarefas e seus critérios de aceite |
| **Resultado** | **19 tarefas concluídas · 5 parciais · 15 não iniciadas · 8 achados** |
| **Depois** | A-02, A-03 e A-05 fechados em 2026-09-08 ([T-040](../tasks/T-040-csrf-e-rate-limit.md), [T-039](../tasks/T-039-codegen-e-bijecao.md)) — 21 concluídas |

---

## O problema que motivou esta auditoria

As 39 tarefas foram geradas com status `⬜` e **nunca atualizadas**. A execução
seguiu a conversa, não o board — e o board virou ficção: dizia que nada tinha
sido feito enquanto dezenove tarefas estavam prontas, e os critérios de aceite
nunca foram conferidos um a um.

A consequência não é cosmética. Sem status verdadeiro:

- não dá para saber o que falta sem reler a conversa inteira;
- promessa de documento e realidade de código divergem em silêncio — foi assim
  que o CSRF ficou prometido em três lugares e implementado em nenhum;
- a pergunta *"isso está pronto?"* só tem resposta por inspeção manual.

A correção está no [PROGRESSO](../tasks/PROGRESSO.md) e na regra nova do
[acordo de trabalho](../tasks/README.md).

---

## Achados

### A-01 · O board não refletia a execução
**Severidade: alta (processo).** 19 tarefas concluídas marcadas como disponíveis.
Corrigido nesta auditoria; a regra que evita a recorrência está no acordo §12.

### A-02 · CSRF prometido em três lugares, implementado em nenhum ✅ FECHADO
**Severidade: alta (segurança).** Corrigido em [T-040](../tasks/T-040-csrf-e-rate-limit.md).

| Onde | O que promete |
|---|---|
| [ADR-0019](../adr/0019-autenticacao-e-cadastro.md) | *"token de dupla submissão em toda escrita, mais verificação de `Origin`"* |
| [T-037](../tasks/T-037-autenticacao.md) AC-2 | *"escrita sem token CSRF é recusada"* |
| T-037 AC-3 | *"escrita com `Origin` de outro domínio é recusada"* |

O que existe: o cookie `csrf` é criado no login, o cliente envia o header
`X-CSRF-Token` em toda escrita — e **o servidor nunca o lê**. A metade visível
foi construída; a metade que protege, não.

`SameSite=Lax` continua valendo e cobre a maior parte dos casos. O que falta é a
segunda camada, que o ADR declara e o sistema não tem.

→ **T-040**, aberta.

### A-03 · Rate limit no login não existe ✅ FECHADO
**Severidade: alta (segurança).** Corrigido em [T-040](../tasks/T-040-csrf-e-rate-limit.md). `auth/` está vazio. T-037 AC-8 e `CS-06`
exigem limite por conta e por IP; nada limita tentativas de senha hoje.

→ **T-040**, junto com A-02.

### A-04 · `arch:check` existe só metade
**Severidade: média.** [T-005](../tasks/T-005-arch-check.md) especifica 12 regras
em dois verificadores. O `import-linter` cobre **4 das 6** do lado Python; o
`arch-check` do lado TypeScript **não existe** — as 6 regras do cliente não são
verificadas por nada.

Faltam do lado Python: `domain`/`registry` não importam `sqlalchemy`, e fixtures
só importadas por `data`.

### A-05 · Bijeção registry ↔ views não é verificada ✅ FECHADO
**Severidade: alta.** Corrigido em [T-039](../tasks/T-039-codegen-e-bijecao.md). [ADR-0017](../adr/0017-registry-servidor-views-cliente.md)
diz, com todas as letras: *"é este teste que faz o ADR-0017 valer o que o
ADR-0006 valia. Sem ele, esta decisão é uma regressão."*

[T-039](../tasks/T-039-codegen-e-bijecao.md) não foi executada: não há
`web/src/generated/`, não há codegen do OpenAPI, e não há teste de bijeção. Hoje
os três componentes têm registro e view por coincidência de disciplina, não por
verificação.

É o achado mais grave depois dos de segurança, porque compromete a decisão que
substituiu o ADR-0006.

### A-06 · Escopo cresceu sem o PRD acompanhar
**Severidade: média.** Três coisas entraram e o PRD ainda as lista como fora:

| Entregue | Estado no PRD |
|---|---|
| Compartilhamento de view | **NO-6 — não-objetivo** |
| `vencimento_grafico` | não existe no catálogo de 23 |
| Cadastro de usuário | não é requisito de nenhum RF |

O compartilhamento é o caso claro: ADR-0009 o adiava para o ciclo 2, foi pedido
e construído, e o PRD nunca foi revisto.

### A-07 · Não há CI
**Severidade: média.** [T-001](../tasks/T-001-bootstrap.md) AC-3 e
[T-035](../tasks/T-035-docker-compose.md) AC-5 exigem CI rodando lint, typecheck,
test e arch nos dois lados. `.github/workflows/` não existe. Tudo passa porque é
rodado à mão — o que funciona enquanto for uma pessoa só.

### A-08 · Spike T-017 sem relatório
**Severidade: baixa.** A medição foi feita e está no
[PRD §9](../prd/PRD-001-ciclo-1.md), mas o relatório `R-001` que a T-017 exige não
existe, e a tarefa previa uma etapa que não aconteceu: **as perguntas escritas e
versionadas antes da primeira execução**, em commit separado.

Sem isso, não há como provar que os casos não foram ajustados ao resultado. A
suíte atual tem 17 casos e acerta 100% nos dois modos — número bom demais para
não levantar a pergunta.

---

## Estado real, por onda

| Onda | Concluídas | Parciais | Não iniciadas |
|---|---|---|---|
| **W0** Contratos | T-035, T-001, T-002, T-003, T-004 | T-005 | T-039 |
| **W1** Núcleo | T-036, T-006, T-007, T-008, T-009, T-010, T-012, T-013, T-014, T-015 | T-011, T-016, T-037 | — |
| **W2** Risco | — | T-017 | — |
| **W3** Leitura | T-020 | — | T-018, T-019, T-021, T-022, T-023, T-024 |
| **W4** Escrita | — | — | T-025 … T-030 |
| **W5** Garantias | — | T-032, T-033 | T-031, T-034, T-038 |

**Catálogo: 3 de 23 componentes.** `fila_vencimento`, `estoque_indicador` e
`vencimento_grafico` — este último não previsto no PRD (ver A-06).

### O que está pronto e é substancial

Domínio com regras puras e testes de fronteira · banco com imutabilidade por
`REVOKE` · catálogo filtrado por ator com filtragem de valor de enum ·
validação adversarial de schema · três provedores de modelo trocáveis por
configuração · três modos de saída com queda automática · suíte de avaliação
com casos negativos · sistema de design com paleta validada · compartilhamento
com destinatários filtrados por permissão.

### O que falta e muda a tese

**Escrita.** Nenhum componente tem `commands`. O
[ADR-0002](../adr/0002-plano-render-plano-escrita.md) — *"a saída do modelo
autoriza renderizar, nunca autoriza escrever"* — **não está demonstrado**,
porque não há escrita para o modelo deixar de autorizar. É a metade que falta da
tese, e um revisor vai notar.

---

## O que muda daqui em diante

1. **Status é atualizado no mesmo commit da entrega**, nunca depois
   ([acordo §12](../tasks/README.md)).
2. **Critério de aceite não conferido não é marcado.** Marcar por otimismo é
   pior que deixar em branco: cria evidência falsa.
3. **`make progresso`** conta os ACs marcados por tarefa e compara com o BOARD.
4. Toda entrega que muda escopo revisa o PRD no mesmo commit.
