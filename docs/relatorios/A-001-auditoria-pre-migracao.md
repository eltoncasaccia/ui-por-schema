# A-001 — Auditoria pré-migração

| | |
|---|---|
| **Data** | 2026-09-07 |
| **Motivo** | Antes de migrar para API Python + cliente TypeScript + Postgres em Docker |
| **Alvo** | 63 documentos: PRD, 15 ADRs, CONTRATOS, 34 tarefas, rastreabilidade |
| **Resultado** | **11 achados** — 3 de segurança, 4 de consistência, 4 mecânicos |

Auditoria feita **antes** da migração de propósito: migrar carregando contradição
significa reescrever duas vezes, e algumas destas só apareceram porque a troca de
arquitetura obrigou a olhar de novo.

---

## Achados de segurança

### A-01 · `select` roda no cliente — dado filtrado atravessa a rede

**Severidade: alta.** Contradição documentada.

| Onde | O que diz |
|---|---|
| [Arquitetura v2 §4](../03-arquitetura-v2.md) | `select` — *"projeção pura, roda no render"* |
| [T-015](../tasks/T-015-motor-de-render.md) | o motor *"chama `load`, aplica `select`, renderiza"* — no cliente |
| [CONTRATOS §5](../tasks/CONTRATOS.md) | `select: (dados: D) => V // PURA` — **não diz onde roda** |

Se `load` devolve `D` e a projeção para `V` acontece no navegador, então **`D`
inteiro atravessa a rede**. Tudo que o `select` descarta já chegou ao cliente e
está no DevTools.

Impacto direto em `CA-05`: se o `select` for o que remove custo, o custo trafega.

> **Resolução:** `select` roda **no servidor**, imediatamente após o `load`. Só `V`
> cruza a rede. Vira ADR-0020, e a arquitetura v2 §4 fica marcada como corrigida.

Com API em Python isso deixa de ser escolha: `load` e `select` estão no processo
Python, e só o viewmodel serializado chega ao cliente. **A migração resolve o
achado como efeito colateral.**

---

### A-02 · Sessão em cookie sem proteção CSRF

**Severidade: alta.** Lacuna, não contradição — a autenticação foi acrescentada
depois dos documentos.

Cookie `httpOnly` protege contra roubo por XSS. **Não protege contra CSRF.** Todo
comando de escrita (`POST /movimentos/saida`, `POST /lotes/:id/liberacao`) fica
disparável por site de terceiro enquanto a pessoa estiver logada.

Numa entrevista, é a primeira pergunta depois de "como você guarda a sessão?".

> **Resolução:** `SameSite=Lax` como base (já previsto) **mais** token CSRF de
> dupla submissão nos comandos de escrita, e `Origin`/`Referer` verificados no
> servidor. Entra no ADR-0019 e na tarefa de autenticação.

---

### A-03 · `viewKey` é hash de conteúdo, mas o ADR promete revogação

**Severidade: média-alta.** Contradição interna do [ADR-0009](../adr/0009-identidade-de-view.md).

| Linha | O que afirma |
|---|---|
| Título | *"com **id gerado no servidor**"* |
| Decisão | *"A chave é `viewKey`, derivada por **hash** do schema canonicalizado"* |
| Consequências | *"**Revogação existe**: um id pode ser invalidado"* |

As três não podem ser verdadeiras ao mesmo tempo. **Hash de conteúdo não é
revogável** — invalidar a chave e recompor a mesma view regenera exatamente a
mesma chave. E se o hash é o endereço público, ele é derivado do conteúdo, não
gerado pelo servidor.

> **Resolução — dois identificadores, com papéis distintos:**
>
> | | O que é | Para quê |
> |---|---|---|
> | `viewKey` | hash do schema canonicalizado, **interno** | deduplicação: favorito, histórico, "é a mesma tela" |
> | `viewId` | opaco, aleatório, gerado no servidor, **público** | a URL `/v/:viewId`, revogação, auditoria |
>
> Um `viewId` aponta para um registro que carrega seu `viewKey`. Revogar o
> `viewId` não afeta o `viewKey` — que é o comportamento correto: a view continua
> sendo a mesma view; o *endereço* é que foi revogado.

Bônus de segurança: `viewId` aleatório não é enumerável nem adivinhável a partir
do conteúdo, o que um hash em URL seria.

---

## Achados de consistência

### A-04 · `Lote.status` armazena estado derivado — a doença que o T-002 proíbe

**Severidade: alta.** É o achado mais interessante da auditoria.

[T-002 AC-1](../tasks/T-002-dominio-tipos-erros.md) proíbe campo `saldo` no `Lote`,
com o argumento certo: *"um campo de saldo é um campo editável, e um campo editável
é a divergência de 3,8% de volta"* (`RN-M06`).

Mas o mesmo `Lote` tem `status: StatusLote`, e dois dos seis valores são
**igualmente derivados**:

| Status | Derivado de | Documento 02 |
|---|---|---|
| `vencido` | data de validade vs. hoje | §4.1 — *"Sistema, automático"* |
| `esgotado` | soma dos movimentos = 0 | §4.1 — *"Sistema, automático"* |

Armazená-los cria exatamente o problema que `RN-M06` evita: um lote vencido ontem
com `status: 'liberado'` no banco porque nenhum processo rodou.

**E nenhuma das 34 tarefas implementa essas transições.** Não há job, não há
agendamento, não há tarefa. `RN-L05` (bloqueio automático em 30 dias) tem o mesmo
buraco.

Havia inclusive uma discordância entre tarefas: [T-020 AC-3](../tasks/T-020-vencimento-indicador.md)
trata a validade como **derivada em tempo de leitura** (`classificarValidade`),
enquanto o tipo a trata como armazenada.

> **Resolução — separar o que é decisão humana do que é consequência:**
>
> ```
> StatusLoteRegistrado   quarentena · liberado · bloqueado · descartado
>                        ↑ muda por ação de alguém, com autor e motivo
>
> StatusLoteEfetivo      + vencido · esgotado
>                        ↑ função pura de (registrado, validade, saldo, hoje)
> ```
>
> Nada de job, nada de agendamento. Consistente com `RN-M06`, e o
> `classificarValidade` do T-008 passa a ser a fonte única.

---

### A-05 · `requires` é obrigatório e estático, e dois componentes não cabem

**Severidade: média.** Contradição entre [CONTRATOS §5](../tasks/CONTRATOS.md) e duas tarefas.

CONTRATOS afirma: *"`requires` é obrigatório — o tipo não compila sem ele"*. Mas:

| Componente | O que a tarefa diz | Conflito |
|---|---|---|
| `confirm_action` | *"sem `requires` próprio — herda o do comando confirmado"* | é opcional |
| `estoque_indicador` | *"varia por métrica"* | é dinâmico, depende do param |

> **Resolução:**
> - `confirm_action` sai do catálogo do modelo, como o `sem_acesso` já saiu.
>   Confirmação é decisão do motor de render diante de `CommandDef.confirm`, não
>   composição que o modelo escolhe. **Catálogo cai de 23 para 22** e a folga
>   sobe para 3.
> - `estoque_indicador` ganha `requires` por **valor de enum**: a métrica
>   `valor_em_estoque` exige `custo.ler`, as demais exigem `lote.ler`. O contrato
>   passa a aceitar `requires` como mapa `param → permissão`, além de estático.

---

### A-06 · Seis permissões declaradas sem uso, e uma contradiz uma tarefa

**Severidade: média.**

| Permissão | Situação |
|---|---|
| `produto.criar` `produto.editar` `produto.inativar` | Nenhum componente. Não há CRUD de produto no ciclo 1 |
| `usuario.ler` `usuario.gerenciar` | Nenhum componente — **passam a ser usadas** com a autenticação |
| `controlado.movimentar` | **Contradiz [T-028](../tasks/T-028-saida-fefo.md)**, que usa `movimento.criar` para saída de controlado |

A matriz do documento 02 tem a linha *"Controlado — movimentar"* com Conferente
`C*`, o que exige permissão própria — mas a tarefa não a usa.

> **Resolução:** `controlado.movimentar` passa a ser exigida em `movimento_saida`
> quando o produto é controlado (`requires` por param, mesmo mecanismo do A-05).
> As três de produto saem do enum — permissão sem uso é superfície morta que
> confunde quem lê. Voltam quando houver CRUD de produto.

---

### A-07 · CONTRATOS define 3 de 7 entidades

**Severidade: média.** [T-002](../tasks/T-002-dominio-tipos-erros.md) exige sete
tipos; [CONTRATOS §3](../tasks/CONTRATOS.md) define três.

Faltam: `Recebimento`, `RegistroTemperatura`, `Unidade`, `Usuario`.

Um contrato "congelado" incompleto é pior que nenhum: quem pega T-022 ou T-023 em
sessão paralela inventa o tipo, e duas sessões inventam diferente. **É exatamente
a colisão que o congelamento existe para evitar.**

> **Resolução:** completar os quatro antes de qualquer paralelização.

---

## Achados mecânicos — consequência da migração

### A-08 · Quatro critérios de aceite dependem do compilador TypeScript

| Tarefa | Critério |
|---|---|
| T-002 AC-4 | *"`ReadonlySet`; tentativa de mutação **não compila**"* |
| T-003 AC-1 | *"`defineComponent` sem `requires` **não compila**"* |
| T-003 AC-4 | tipo de `select` inferido do retorno de `load` |
| T-010 AC-2 | *"mutar evento registrado **não compila**"* |

Os quatro vão para o lado Python. Precisam de equivalente: `mypy --strict`,
`@dataclass(frozen=True)`, `Protocol`, `Final`. **Garantia comparável, sintaxe
diferente** — e o critério tem de ser reescrito, não traduzido literalmente.

### A-09 · `arch:check` se divide em dois verificadores

Das 9 regras: **1, 2, 3** ficam no cliente TypeScript; **4, 5, 6, 7** vão para
`import-linter` em Python; **9** continua nos dois. A regra **8** (`registry/componentes/*`
exporta exatamente um `defineComponent`) **morre com o ADR-0006** e é substituída
pelo teste de bijeção `registry` ↔ `views`.

### A-10 · Caminhos e ferramentas desatualizados

30 tarefas citam `src/`; 4 citam `npm run`; 2 citam `zod`; 1 cita
`React.ComponentType` dentro do contrato do servidor.

### A-11 · Autenticação não tem tarefa, e `usuario.gerenciar` não tem tela

Escopo novo, aceito nesta rodada, ainda sem lugar no BOARD.

---

## Verificado e correto

Registrado para que a auditoria não pareça só lista de defeitos:

| Item | Resultado |
|---|---|
| Contagem de catálogo | 23 nas tarefas = 23 na rastreabilidade ✓ (vira 22 com A-05) |
| Links internos | 301 verificados, **zero quebrados** ✓ |
| `custo.ler` | tratado em 9 pontos — porta, catálogo, componente, trilha, testes. **Defesa em profundidade coerente**, não duplicação acidental ✓ |
| Cobertura de ADR | todo ADR tem tarefa que o verifica ✓ |
| Critérios de aceite | CA-01 a CA-08 todos rastreados até teste ✓ |
| Escopo | nenhuma tarefa toca contagem, ajuste ou transferência ✓ |

---

## Efeito da migração sobre os 15 ADRs

| | |
|---|---|
| **Substituído** | ADR-0006 — "uma declaração produz tudo" |
| **Emendados** | ADR-0007 (dois verificadores) · ADR-0009 (A-03) |
| **Intactos** | 12, incluindo os cinco fundacionais |

Que 12 de 15 sobrevivam à troca de linguagem do servidor é evidência de que as
decisões estavam no nível certo — separadas da tecnologia.
