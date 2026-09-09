# ADR-0031 — Ports & Adapters, com a regra de dependência verificada pelo CI

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-09 |
| **Escopo** | Fundacional |
| **Substitui** | [ADR-0030](./0030-layout-de-diretorios.md) — que descrevia o mesmo desenho sem nomeá-lo |

## Contexto

O [ADR-0030](./0030-layout-de-diretorios.md) descreveu corretamente o mecanismo —
*"diretório é definido pelo que tem permissão de importar"* — e cometeu um erro de
consequência prática: **inventou vocabulário em vez de usar o nome que a indústria
usa.** Quem lesse aquele ADR não conseguiria dizer que padrão o projeto segue.

O padrão sempre esteve no código, e literalmente:

| Arquivo | Nome no padrão |
|---|---|
| `data/**porta**.py` — 6 `Protocol` | *port* |
| `data/repositorios.py` — SQLAlchemy | *driven adapter* |
| `assistant/**adapter**.py` — `AdaptadorModelo(Protocol)` | *port* do LLM |
| `assistant/fabrica.py` — OpenRouter, Ollama, Anthropic | *driven adapter* |
| `assistant/observador.py` — `Observador(Protocol)` | *port* de telemetria |
| `server/app.py` — FastAPI | *driving adapter* |

Faltava o nome, e faltava a arrumação que o torna legível: `registry/`,
`commands/` e `schema/` estavam soltos na raiz do pacote, parecendo três coisas de
naturezas diferentes. São a mesma: **caso de uso**.

## Decisão

> **O `api/` é Ports & Adapters (hexagonal), com a regra de dependência do Clean
> Architecture: as setas apontam para dentro. Os casos de uso ficam sob
> `application/`, e a regra é verificada pelo `import-linter` no CI.**

```
domain/                    núcleo. Não importa NADA do projeto
   ↑
application/               casos de uso
   registry/                 leitura  — catálogo, load, select
   commands/                 escrita  — pipeline e comandos
   schema/                   validação da entrada não-confiável
   ↑
portas                     data/porta.py · assistant/adapter.py
   ↑                       assistant/observador.py
adapters                   server/ (primário)
                           data/repositorios.py · assistant/fabrica.py (secundários)
```

`auth/`, `autorizacao/` e `auditoria/` ficam fora de `server/` de propósito:
`autorizacao/motor.py` é chamado pela borda **e** pelo pipeline de comandos. Se
morasse dentro de `server/`, `commands` teria que importar a borda para autorizar,
e a seta apontaria para o lado errado.

### O que este projeto faz e a maioria não

O padrão é comum. **Verificá-lo não é.**

```ini
[importlinter:contract:3]
name = assistente nunca alcanca comandos de escrita
source_modules = estoque.assistant
forbidden_modules = estoque.application.commands
allow_indirect_imports = False
```

E — o que fecha o argumento — **o verificador tem testes que provam que ele
quebra**: `tests/arquitetura/test_verificador_falha_quando_violado.py` introduz
cada violação de propósito, inclusive por caminho indireto de dois saltos, e
afirma que `lint-imports` sai com código diferente de zero.

> Uma regra que nunca falhou não é evidência de nada.

### Por que `src/estoque`

`src/` é layout de pacote instalado: `import estoque` só funciona porque o pacote
está **instalado**, nunca porque o diretório de trabalho por acaso tem uma pasta
com esse nome. A consequência é o motivo — `tests/` é **irmão** de `src/`, e o
teste importa pelo mesmo caminho que a produção. O teste que passa na máquina de
quem escreveu e quebra no container deixa de existir como categoria.

`estoque` é o pacote distribuível, único, e serve de raiz ao verificador
(`root_package = estoque`). `api/` ou `app/` colidiriam com nome genérico.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **MVC** | Não tem onde pôr a regra de negócio: ela escorre para o controller ou para o model, e a divergência de 3,8% do cliente veio exatamente de regra espalhada |
| **Clean Architecture com os nomes do livro** (`entities/`, `usecases/`, `interface_adapters/`, `frameworks/`) | Mesma ideia, mais cerimônia. Quatro anéis para um sistema com três lugares onde a dependência importa. E `usecases/` esconderia a separação leitura/escrita, que é a tese |
| **Vertical slice / por feature** (`lote/`, `movimento/`) | A barreira do ADR-0002 atravessa **todas** as features: cada uma teria leitura e escrita no mesmo pacote, e o contrato 3 seria inexpressável. Foi o que decidiu |
| **Renomear tudo para o vocabulário canônico** (`adapters/db`, `adapters/http`, `ports/`) | Tocaria 11 componentes, 4 comandos, ~18 arquivos de teste, o `.importlinter`, o gerador de índice, as listas de propriedade exclusiva de todas as tarefas e o CONTRATOS, que é congelado. O ganho é de leitura; o nome do padrão resolve o mesmo por um documento |
| Manter `registry/`, `commands/`, `schema/` na raiz | Três casos de uso parecendo três naturezas. Era a queixa que originou este ADR |

## Consequências

**Positivas**
- O desenho tem nome, e o nome é o que se usa numa conversa técnica.
- `application/` torna a camada de casos de uso visível sem ler documento.
- A pergunta "onde isto vai?" continua tendo resposta mecânica: *o que este
  código precisa importar?*

**Negativas**
- Caminhos de import mais longos (`estoque.application.registry.componentes.x`).
- `tests/` **não** espelha a mudança: continua `tests/registry/`,
  `tests/commands/`, `tests/schema/`. Mover custaria a lista de propriedade
  exclusiva de todas as tarefas, por ganho de simetria. Fica anotado.
- `auth/` continua meio adapter, meio aplicação — a única fronteira do projeto
  que não é limpa.

**Riscos aceitos**
- Do lado TypeScript isto é **convenção, não CI**: `web/scripts/arch-check.ts` é
  invocado pelo Makefile e não existe (achado A-13, endereçado à T-005). O
  hexágono é verificado no `api/` e prometido no `web/`.

## Conformidade

- `api/.importlinter`, contratos 1 a 4 — `make arch` falha o build.
- `api/tests/arquitetura/test_verificador_falha_quando_violado.py` — o
  verificador quebrado de propósito, direto e em dois saltos.
- `api/tests/commands/test_ac1_barreira.py` — o grafo percorrido em código, com
  `grimp` e `cache_dir=None`, para a garantia não morrer junto com uma linha
  removida do arquivo de configuração.
- `api/tests/registry/test_quarentena_liberar.py` — `application/commands/entradas/**`
  não alcança `pipeline`, `data` nem `sqlalchemy`.

## Referências
- [ADR-0002](./0002-plano-render-plano-escrita.md) — a barreira que decide o layout
- [ADR-0007](./0007-camadas-e-arch-check.md) · [ADR-0016](./0016-api-python-cliente-typescript.md)
- [`api/CLAUDE.md`](../../api/CLAUDE.md) — o hexágono desenhado, com pasta → papel
- Alistair Cockburn, *Hexagonal Architecture* (2005) · Robert C. Martin, *Clean
  Architecture* (2017) — a regra de dependência
