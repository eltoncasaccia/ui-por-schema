# ADR-0020 — `select` roda no servidor; só o viewmodel cruza a rede

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Fundacional |
| **Corrige** | Achado [A-01](../relatorios/A-001-auditoria-pre-migracao.md) · emenda [Arquitetura v2 §4](../03-arquitetura-v2.md) |

## Contexto

A arquitetura v2 descrevia `select` como *"projeção pura, roda no render"*, e o
motor de render do cliente aplicaria a projeção. `CONTRATOS.md` marcava a função
como pura mas **não dizia onde roda** — e a auditoria A-001 mostrou que a leitura
natural era: no cliente.

A consequência é uma falha de confidencialidade:

```
load → D  ──────── rede ────────▶  select → V  → render
        ↑ D INTEIRO no navegador
```

Tudo que `select` descarta já chegou ao cliente e está no DevTools. Para `CA-05`
(custo invisível), se a projeção for o que remove o custo, o custo trafega.

## Decisão

> **`load` e `select` rodam no servidor, em sequência. Apenas o viewmodel `V`
> é serializado e enviado. `D` nunca sai do processo da API.**

```
API:      load → D → select → V ──── rede ────▶  CLIENTE: render(V)
```

`select` continua sendo **função pura** — a pureza é sobre determinismo e ausência
de I/O, não sobre onde executa.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| `select` no cliente, com `load` já projetando | Empurra a responsabilidade de projeção para o `load`, e `select` deixa de ter razão de existir |
| `select` no cliente, confiando na porta de dados | A porta já remove custo (T-007), mas isso cobre **um** campo restrito. `select` descarta muito mais, e depender de uma única camada é o oposto de defesa em profundidade |

## Consequências

**Positivas**
- O cliente recebe exatamente o que renderiza. Nada a mais.
- Menos tráfego, menos serialização.
- Com [ADR-0016](./0016-api-python-cliente-typescript.md), passa a ser garantido
  por construção: `select` está em Python, o cliente não tem como executá-lo.
- O viewmodel `V` vira o contrato público do componente, e é o que o OpenAPI
  descreve.

**Negativas**
- Reprojetar sem nova requisição deixa de ser possível: ordenar, filtrar ou
  agrupar no cliente exige que o viewmodel já traga o necessário.
- O viewmodel precisa ser desenhado com cuidado — projeção apertada demais obriga
  round trip para cada interação.

**Riscos aceitos**
- Interações puramente visuais (ordenar coluna) podem precisar de dados que o
  viewmodel não traz. Regra prática: **o viewmodel carrega o que a tela mostra e
  o que a tela deixa ordenar**, nada além.

## Conformidade

- Teste por componente: a resposta serializada de `/api/componentes/:id/dados`
  contém **exatamente** as chaves do viewmodel, e nenhuma do modelo de carga.
- Teste `CA-05`: para ator sem `custo.ler`, nenhuma resposta de nenhum componente
  contém a chave de custo — verificado sobre o **corpo HTTP**, não sobre o objeto
  de domínio.

## Referências
- [Arquitetura v2 §4](../03-arquitetura-v2.md) (corrigida aqui) · ADR-0016
