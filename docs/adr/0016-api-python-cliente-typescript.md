# ADR-0016 — Separar API e cliente em processos e linguagens distintos

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Fundacional |
| **Relacionado** | Substitui parte do [ADR-0006](./0006-contrato-unico-de-componente.md) · emenda [ADR-0007](./0007-camadas-e-arch-check.md) |

## Contexto

O ADR-0006 colocava `load` (servidor, toca repositório) e `render` (cliente, React)
na mesma declaração. Num bundle único de TypeScript, **o arquivo inteiro entra no
pacote do cliente** — incluindo a lógica de acesso a dados. Não vaza dado, porque
os endpoints continuam autorizados (ADR-0004), mas vaza implementação e abre a
porta para import acidental.

A defesa disponível era truque de bundler mais regra de `arch:check`: convenção
verificada, não impossibilidade.

Contexto adicional: o projeto é **portfólio público**. Um revisor vai perguntar
"seu código de acesso a dados vai para o navegador?", e "tem um lint que impede"
é resposta mais fraca que "está em outro processo".

## Decisão

> **A API é um serviço Python (FastAPI) e o cliente é uma aplicação TypeScript
> separada. A fronteira entre plano de dados e plano de apresentação é uma
> fronteira de processo, não uma convenção de import.**

```
┌────────────┐   HTTP/JSON    ┌──────────────┐   SQL   ┌──────────┐
│  web       │ ─────────────▶ │  api         │ ──────▶ │ postgres │
│  React/TS  │  ◀───────────  │  Python      │         │          │
│  só views  │   viewmodels   │  domínio,    │         └──────────┘
└────────────┘                │  registry,   │
                              │  autorização │
                              └──────────────┘
```

Orquestração por **Docker Compose**: `docker compose up` sobe os três. É a única
instrução de "como rodar".

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| TypeScript ponta a ponta, monorepo por runtime | Era a proposta anterior. Funciona, mas a separação depende de bundler e lint. Perde para uma fronteira de processo |
| TypeScript num pacote só, dois entry points | A garantia passa a depender de a transformação de build funcionar em todos os casos |
| Monorepo `client`/`server`/`shared` | `shared` conteria `load` e `render` juntos e iria inteiro para os dois lados — não resolve nada |

## Consequências

**Positivas**
- É **fisicamente impossível** o `load` chegar ao navegador.
- `select` passa a rodar no servidor por construção — resolve o [ADR-0020](./0020-select-no-servidor.md).
- OpenAPI sai de graça do FastAPI e gera os tipos do cliente.
- Separação legível para qualquer revisor: `api/` e `web/`.

**Negativas**
- **Perde-se a garantia de compilação entre `select` e `render`.** Em TypeScript
  ponta a ponta, o compilador provava que o viewmodel devolvido é o consumido.
  Agora isso vira *tipos gerados do OpenAPI + teste de bijeção em CI*. É mais
  fraco, e é o preço principal desta decisão.
- Duas toolchains, dois verificadores de arquitetura, dois runners de teste.
- Um passo de codegen no caminho de build.

**Riscos aceitos**
- Divergência entre `registry` (Python) e `views` (TypeScript). Mitigado pelo teste
  de bijeção obrigatório do [ADR-0017](./0017-registry-servidor-views-cliente.md) —
  sem ele, esta decisão reintroduz o apodrecimento que o ADR-0006 evitava.

## Conformidade

- `web/src/generated/**` é gerado; CI falha se estiver desatualizado em relação ao
  OpenAPI da API.
- Nenhuma dependência de banco no `package.json` do cliente.
- `import-linter` no lado Python, `arch:check` no lado TypeScript.

## Referências
- [A-001 auditoria](../relatorios/A-001-auditoria-pre-migracao.md) · ADR-0002, ADR-0004
