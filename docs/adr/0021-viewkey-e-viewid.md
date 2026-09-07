# ADR-0021 — `viewKey` interna para identidade, `viewId` público para endereço

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Ciclo 1 |
| **Emenda** | [ADR-0009](./0009-identidade-de-view.md) · corrige achado [A-03](../relatorios/A-001-auditoria-pre-migracao.md) |

## Contexto

O ADR-0009 afirmava três coisas que não podem ser verdadeiras juntas:

| Onde | Afirmação |
|---|---|
| Título | *"com **id gerado no servidor**"* |
| Decisão | *"A chave é `viewKey`, derivada por **hash** do schema canonicalizado"* |
| Consequências | *"**Revogação existe**: um id pode ser invalidado"* |

**Hash de conteúdo não é revogável.** Invalidar a chave e recompor a mesma view
regenera exatamente a mesma chave. E se o hash é o endereço público, ele é
derivado do conteúdo — não gerado pelo servidor.

A confusão vem de misturar duas necessidades diferentes que o ADR-0009 tratou como
uma: *"esta tela é a mesma tela de antes?"* e *"qual o endereço desta tela?"*.

## Decisão

> **Dois identificadores, com papéis distintos.**

| | O que é | Onde vive | Para quê |
|---|---|---|---|
| **`viewKey`** | hash do schema canonicalizado | **interno**, nunca em URL | deduplicação: favorito, histórico, "é a mesma tela" |
| **`viewId`** | opaco, aleatório, gerado no servidor | **público**, na URL `/v/:viewId` | endereço, revogação, auditoria |

Um registro de view guarda `{ viewId, viewKey, schema, criadoPor, criadoEm, revogadoEm }`.

Revogar um `viewId` **não afeta** o `viewKey` — que é o comportamento correto: a
view continua sendo a mesma view; o *endereço* é que foi revogado. Recompor gera
`viewId` novo com o mesmo `viewKey`, e o favorito continua funcionando.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Só o hash, sem revogação | Abandona uma propriedade que o ADR-0009 vendeu, e endereço não revogável é problema no ciclo 2, quando houver compartilhamento |
| Só id aleatório, sem hash | Volta o bug do favorito da v1: a mesma tela recomposta não se reconhece |
| Hash com sal por usuário | Deixa de deduplicar entre usuários e continua não sendo revogável |

## Consequências

**Positivas**
- O bug do favorito da v1 continua resolvido, e revogação passa a ser verdade.
- `viewId` aleatório **não é enumerável nem adivinhável a partir do conteúdo** —
  um hash em URL seria, para quem conhecesse o esquema de canonicalização.
- Auditoria ganha um alvo estável: `viewId` identifica um acesso específico.

**Negativas**
- Dois conceitos onde havia um. Custo de explicação permanente, inclusive neste ADR.
- Uma tabela a mais, com limpeza de registros antigos a considerar.

**Riscos aceitos**
- `viewId` continua **apontando para** uma view, e não concedendo acesso. Quem
  abre carrega sob a própria permissão, com o schema revalidado contra o próprio
  catálogo. Isso vale igual para os dois identificadores e continua sendo a regra
  que não pode quebrar (ADR-0009).

## Conformidade

- Teste: o mesmo schema com chaves em ordem diferente produz a mesma `viewKey`.
- Teste: recompor a mesma view produz `viewId` **diferente** e `viewKey` **igual**.
- Teste: `viewId` revogado devolve `nao_encontrado`; o `viewKey` continua válido.
- Teste: nenhuma URL do sistema contém `viewKey`. *(negativo)*
- Teste: `viewId` tem ao menos 128 bits de entropia.

## Referências
- [ADR-0009](./0009-identidade-de-view.md) · [A-001 achado A-03](../relatorios/A-001-auditoria-pre-migracao.md)
