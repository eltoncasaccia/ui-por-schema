# ADR-0018 — Postgres em container, acessado só pela API

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Ciclo 1 |

## Contexto

A proposta anterior era repositórios in-memory no ciclo 1, com banco real depois.
O argumento era velocidade de teste e foco: o ciclo 1 existe para provar permissão
e composição, não persistência.

Dois fatos mudaram o cálculo:

1. **O projeto é portfólio.** Um repositório cuja camada de dados é uma lista em
   memória é descontado por quem revisa, independentemente da qualidade do resto.
2. **In-memory esconde um problema real.** [T-025](../tasks/T-025-pipeline-de-comando.md)
   exige que comando falho não deixe efeito parcial, e [T-011](../tasks/T-011-servidor.md)
   exige conflito por etag. Em lista na memória isso é trivial e **prova nada**.

## Decisão

> **Postgres 17 em container, subido pelo Docker Compose, acessado exclusivamente
> pelo processo da API.**

- Migrações versionadas com Alembic. Sem `create_all`.
- Seed determinístico com os dados da Bertoni, executável por `make seed`.
- Índices explícitos para as consultas com requisito de tempo — `RNF-01`, recall em
  menos de 60 s, é requisito de índice antes de ser requisito de código.

### O que fica proibido

> **O navegador nunca fala com o banco.** Sem cliente de banco no `web/`, sem chave
> de acesso ao banco no cliente, sem RLS como mecanismo de autorização.

A autorização deste sistema é por registro, no servidor, com a identidade real
(ADR-0004). Autorização em banco acessado pelo cliente é **outra arquitetura**;
misturar as duas produz um sistema em que ninguém sabe qual das duas está valendo.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| In-memory no ciclo 1 | Esconde transação e concorrência, e enfraquece o portfólio |
| SQLite | Some com o problema de concorrência real, que é parte do que se quer demonstrar |
| Supabase gerenciado | Dependência de conta de terceiro para alguém rodar o projeto. `docker compose up` é melhor cartão de visita |
| Supabase com RLS a partir do navegador | Conflita com ADR-0004 e criaria dois modelos de autorização no mesmo sistema |

## Consequências

**Positivas**
- Transação, concorrência e etag testados de verdade.
- `RNF-01` vira medida com plano de execução, não estimativa.
- Reprodutível: `docker compose up` e o sistema existe, com dados.

**Negativas**
- Testes ficam mais lentos que in-memory. Mitigação: transação revertida por
  teste, banco de teste separado, e as regras puras de `domain/` continuam
  testáveis sem I/O.
- Migração é trabalho contínuo que in-memory não teria.

**Riscos aceitos**
- Credencial de banco em `.env`. `.env.example` versionado, `.env` no
  `.gitignore`, e nenhum segredo real no repositório — verificado em CI.

## Conformidade

- `web/package.json` não contém dependência de banco. Teste no CI.
- `grep` de `postgres://` no bundle do cliente falha o build.
- Toda tabela de auditoria sem `UPDATE` nem `DELETE` concedidos ao papel da
  aplicação — `RN-D02` aplicado no banco, não só no código.

## Referências
- [A-001](../relatorios/A-001-auditoria-pre-migracao.md) · ADR-0004 · `RN-D02`
