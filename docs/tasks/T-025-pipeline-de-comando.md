# T-025 — Pipeline de comando e `confirm_action`

| | |
|---|---|
| **Onda** | W4 — Escrita |
| **Trilha** | B |
| **Tamanho** | **G** |
| **Depende de** | T-011, T-015 |
| **Bloqueia** | **toda a W4** |
| **Componentes** | *(nenhum — ver nota)* |
| **ADRs** | [0002](../adr/0002-plano-render-plano-escrita.md), [0004](../adr/0004-autorizacao-em-tres-momentos.md) |
| **Regras** | RN-D01, RN-M04, RN-A03 |
| **Requisitos** | RF-15 |

## Objetivo

O caminho único de escrita. **Nenhum comando é alcançável a partir da saída do
modelo** — é aqui que o ADR-0002 vira código.

## Arquivos de propriedade exclusiva

```
api/src/estoque/commands/pipeline.py   api/src/estoque/commands/tipos.py
api/tests/commands/*.py
```

> **A lista acima foi corrigida na execução** (achado A-12). A original declarava
> `registry/componentes/confirm_action.py`, um arquivo que o próprio escopo desta
> tarefa manda **não** criar (achado A-05), e `commands/*.test.py`, caminho que
> não existe neste repositório — teste Python vive em `api/tests/`.

### Arquivos de outra tarefa, tocados por necessidade — achado A-12

| Arquivo | Dono | Por quê |
|---|---|---|
| `api/migrations/versions/0003_idempotencia.py` | T-036 | `Idempotency-Key` (AC-3) exige registro durável. Não havia tabela |
| `api/src/estoque/data/modelos.py` | T-036 | a tabela precisa da definição Core correspondente |
| `api/src/estoque/server/app.py` | T-011 | sem a rota `/api/comandos/{nome}` os AC-2 a AC-7 não são alcançáveis de fora |

Nenhuma sessão estava em andamento nessas tarefas. A decisão foi tomada com o
cliente antes de escrever — ver A-12 na seção 6 do BOARD.

## Escopo

### Faz
- Pipeline: validar entrada → autorizar no servidor → aplicar regra de domínio →
  persistir → auditar → devolver etag.
- Idempotência por `Idempotency-Key`; concorrência por `If-Match`.
- **Confirmação como decisão do motor de render**, disparada por
  `CommandDef.confirm` — **não** é componente de catálogo.

> **Achado A-05:** `confirm_action` era o único componente sem `requires` próprio,
> o que contradizia a obrigatoriedade declarada em CONTRATOS §5. Saiu do catálogo,
> como `sem_acesso` já havia saído: confirmar não é composição que o modelo
> escolhe. **Catálogo cai de 23 para 22.**
- **Barreira arquitetural:** nenhum caminho de código liga o pipeline do assistente
  a um `CommandDef`.

### Não faz
Comandos específicos — T-026 a T-030.

## Critérios de aceite

- [x] **AC-1** Existe teste que percorre o grafo de imports e afirma que
      `application/assistant/**` **não alcança** `application/commands/**`.
      *(negativo — ADR-0002, o critério central desta tarefa)*
- [x] **AC-2** Todo comando exige ator autenticado e revalida `requires` no
      servidor, mesmo que a interface já tenha escondido a ação. *(negativo —
      `RN-A03`)*
- [x] **AC-3** Repetir a mesma `Idempotency-Key` produz **um** efeito e a mesma
      resposta.
- [x] **AC-4** Escrita concorrente com etag antigo devolve `conflito` sem aplicar
      nada. *(negativo)*
- [x] **AC-5** Todo comando bem-sucedido grava auditoria com valor anterior e novo.
      *(`RN-D01`)*
- [x] **AC-6** `criadoEm` é sempre do servidor; timestamp do cliente é ignorado.
      *(negativo — `RN-M04`)*
- [x] **AC-7** Comando que falha na regra de domínio não deixa efeito parcial —
      auditoria registra a tentativa recusada.

## Definição de pronto — adicional
- [x] Contagem de catálogo no BOARD: **+0** — confirmação não é componente.

## Armadilhas

**AC-1 é o teste que sustenta a tese inteira do projeto.** Se algum dia ele
quebrar, a separação entre plano de render e plano de escrita deixou de existir —
e nenhum outro teste vai perceber.
