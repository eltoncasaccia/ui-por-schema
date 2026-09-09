# ADR-0030 — Organizar diretórios por dependência permitida, não por tipo de arquivo

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-08 |
| **Escopo** | Fundacional |
| **Emenda** | [ADR-0007](./0007-camadas-e-arch-check.md) — a tabela de camadas de lá é a da v1 e não descreve mais o `api/` |

## Contexto

O [ADR-0007](./0007-camadas-e-arch-check.md) decidiu que **camadas são
verificadas por script**. Ele responde *como* a disciplina se sustenta, e não
*quais* camadas existem nem *por que* estas.

A tabela que ele traz — `application/`, `state/`, `render/`, `viewmodels/`,
`components/` — é a do monólito TypeScript da v1. Depois do
[ADR-0016](./0016-api-python-cliente-typescript.md), que partiu o sistema em API
Python e cliente TypeScript, **nenhuma dessas cinco existe no `api/`**. A mesma
tabela desatualizada está em [`03-arquitetura-v2.md` §9](../03-arquitetura-v2.md).

O layout real foi construído em T-001 e cresceu com as tarefas seguintes. Ele é
consistente e tem uma lógica única — mas essa lógica nunca foi escrita. A
pergunta *"por que `src/estoque`, e o que cada diretório significa?"* não tinha
resposta em documento nenhum do repositório.

Fatos que restringem a escolha:

- O `import-linter` precisa de **um** pacote raiz para percorrer o grafo
  (`root_package = estoque`).
- A tese do projeto — [ADR-0002](./0002-plano-render-plano-escrita.md) — só é
  verificável se plano de render e plano de escrita forem **módulos distintos**.
  Um contrato `forbidden` não se escreve dentro de um pacote só.
- `RN-A01` e `RN-A02` são aplicados na porta de dados, e o teste disso depende de
  a porta ser um lugar, não um hábito.

## Decisão

> **Cada diretório é definido pelo que ele tem permissão de importar, não pelo
> tipo de coisa que mora nele. O pacote é `estoque`, sob `src/`, e todo import é
> absoluto a partir dele.**

### `src/` — layout de pacote instalado

O pacote não fica na raiz do projeto. `import estoque` só funciona porque o
pacote está **instalado**, nunca porque o diretório de trabalho por acaso contém
uma pasta com esse nome.

Consequência que é o motivo: `tests/` é **irmão** de `src/`, não filho. O teste
importa pelo mesmo caminho que a produção usa, e o teste que passa na máquina de
quem escreveu e quebra no container deixa de existir como categoria.

`estoque` é o nome do pacote distribuível, e é único. Uma pasta chamada `api/` ou
`app/` colidiria com nome genérico de dependência e não serviria de raiz para o
verificador.

### O eixo: dependência

**Não existe `models/`, `services/`, `utils/` nem `helpers/`.** `Lote` (um tipo) e
`propor_fefo` (uma regra) moram juntos em `domain/` apesar de serem coisas
diferentes, porque têm a mesma permissão — que é nenhuma.

```
domain/                    não importa NADA do projeto
   ↑
data/                      porta única; aplica escopo e campo restrito
   ↑
registry/                  o vocabulário do modelo; proibido server e sqlalchemy
   ↑
assistant/   |  commands/  os dois planos do ADR-0002, separados para serem
   ↑              ↑        verificáveis
server/                    a borda; o único que conhece os dois planos
```

| Diretório | Por que existe como diretório próprio |
|---|---|
| `domain/` | Regra que depende de banco é regra que ninguém testa. Não importar nada é o que deixa `RN-L02` ser exercitada sem subir Postgres |
| `data/` | Interseção de escopo (`RN-A01`) e remoção de campo restrito (`RN-A02`) **não são responsabilidade do chamador**. Um lugar só, testado num lugar só |
| `registry/` | Componente descreve **o quê**, não **como buscar**. Não importar `sqlalchemy` é o que permite testá-lo com repositório falso |
| `schema/` | Validação da saída do modelo. Separada de `assistant/` porque schema recebido é payload não-confiável **venha do modelo ou do cliente** — é o mesmo trabalho nos dois casos |
| `assistant/` | O plano de render: adaptador, prompt, trace |
| `commands/` | O plano de escrita: pipeline e comandos |
| `server/` | A borda HTTP, e o único módulo que conhece os dois planos |
| `auth/`, `autorizacao/`, `auditoria/` | Transversais, e **fora de `server/` de propósito**: `autorizacao/motor.py` é chamado pela borda **e** pelo pipeline de comandos. Dentro de `server/`, o `commands/` teria que importar a borda para autorizar, e a seta apontaria para o lado errado |

### `assistant/` e `commands/` são o ADR-0002 em forma de diretório

Na v1 isso era um pacote só, `application/`, com queries e commands juntos.
Partir em dois não é organização: é a condição para o contrato existir.

```ini
[importlinter:contract:3]
name = assistente nunca alcanca comandos de escrita
source_modules = estoque.assistant
forbidden_modules = estoque.commands
allow_indirect_imports = False
```

Com um pacote só, **esse contrato não teria como ser escrito**, e *"a saída do
modelo autoriza renderizar, nunca autoriza escrever"* voltaria a ser uma frase.

### Subpastas, pelo mesmo eixo

| Caminho | Razão |
|---|---|
| `registry/componentes/<id>.py` | Um arquivo por id do catálogo — o que faz duas tarefas de componente não colidirem |
| `commands/entradas/<dominio>.py` | Pacote-**folha**: só pydantic e `domain`. O `registry` precisa apontar o `CommandDef` para o schema de entrada e **não pode** alcançar `commands/pipeline.py`, que importa SQLAlchemy. É a única forma de haver uma definição do formulário em vez de duas divergindo (achado A-15) |
| `data/seed/` | Dados de demonstração perto da porta que os grava, longe do domínio |
| `domain/regras/` | Uma regra por arquivo, pelo nome da regra — `fefo.py`, `validade.py`, `estados.py` |

### Arquivos gerados

`registry/indice.py`, `commands/indice.py` e `web/src/views/indice.ts` são
**gerados** por `make gerar-indice`, e a razão é a mesma para os três: seriam os
únicos arquivos que **toda** tarefa de componente ou de comando precisaria
editar. Ver o acordo de trabalho §4.

### O lado `web/`

Mesmo eixo, com os nomes que o projeto adotou depois de T-001:

| Diretório | Papel |
|---|---|
| `views/` | uma por componente registrado. Recebe `vm` e desenha. Não busca dado, não decide regra, não conhece permissão |
| `ui/` | peças reutilizáveis, sem conhecimento de domínio |
| `render/` | schema validado → React |
| `shell/` | a moldura: painéis, login, navegação |
| `estado/`, `query/` | sessão e cache |
| `generated/` | gerado por `make types`; não se edita |
| `testes/` | a suíte |

T-001 e o ADR-0007 chamavam três destes de `components/`, `app/` e `state/`. Os
nomes mudaram na implementação e ninguém corrigiu — os corretos são os da tabela
acima.

Numa árvore de trabalho pode aparecer um `web/src/app/` **vazio**, sobra do
esqueleto de T-001. Ele não está versionado — git não guarda diretório vazio —,
então some sozinho num clone novo e não vale correção.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Organizar por tipo (`models/`, `services/`, `repositories/`) | Não expressa restrição nenhuma. `services/` pode importar qualquer coisa, então nenhum contrato de camada se escreve sobre ele — e a disciplina volta a depender de revisão |
| Organizar por feature (`lote/`, `movimento/`, `recebimento/`) | A barreira do ADR-0002 atravessa **todas** as features: cada uma teria leitura e escrita no mesmo pacote, e o contrato 3 se tornaria inexpressável. Foi o que decidiu |
| Pacote na raiz, sem `src/` | Faz `import estoque` funcionar por acidente de diretório de trabalho. O teste passa localmente e quebra no container |
| Manter `application/` como na v1 | Ver acima: é exatamente o que impede verificar a tese |

## Consequências

**Positivas**
- A pergunta "onde isto vai?" tem resposta mecânica: *o que este código precisa
  importar?*
- Quatro contratos do `import-linter` se escrevem porque as fronteiras existem
  como módulos.
- Sessão nova entende o desenho pelo `.importlinter`, não por leitura de código.

**Negativas**
- Diretórios pequenos. `auditoria/` tem um arquivo, `auth/` tem dois. Agrupar por
  tamanho seria mais arrumado e apagaria a fronteira.
- Um schema de entrada compartilhado exige um pacote-folha, com a regra "só
  pydantic" mantida à mão — e verificada por teste, não pelo `import-linter`.
- Ler um fluxo de ponta a ponta atravessa cinco diretórios. É o preço de o
  acoplamento ser explícito.

**Riscos aceitos**
- O eixo é invisível para quem não lê o `.importlinter`. Mitigado por este ADR,
  pela tabela do `CLAUDE.md` §5 e pelos testes de grafo — não por convenção.
- Duas das fronteiras do `web/` **não são verificadas**: `scripts/arch-check.ts`
  é invocado pelo Makefile e não existe (achado A-13). Do lado TypeScript, isto
  aqui é convenção até T-005 fechar.

## Conformidade

- `api/.importlinter`, contratos 1 a 4 — `make arch` falha o build.
- `api/tests/arquitetura/test_verificador_falha_quando_violado.py` introduz as
  violações de propósito e afirma que o verificador quebra, inclusive por caminho
  indireto de dois saltos.
- `api/tests/commands/test_ac1_barreira.py` percorre o grafo com `grimp` e
  afirma que `assistant` não alcança `commands` — em código, para a garantia não
  morrer junto com uma linha removida do arquivo de configuração.
- `api/tests/registry/test_quarentena_liberar.py` afirma que
  `commands/entradas/**` não alcança `pipeline`, `data` nem `sqlalchemy`.
- Todos passam `cache_dir=None` ao `grimp`: o cache já serviu um grafo velho
  (achado A-17), e teste de segurança não depende de invalidação de cache.

## Referências
- [ADR-0002](./0002-plano-render-plano-escrita.md) · [ADR-0007](./0007-camadas-e-arch-check.md)
  · [ADR-0016](./0016-api-python-cliente-typescript.md) · [ADR-0017](./0017-registry-servidor-views-cliente.md)
- [`CLAUDE.md` §5](../../CLAUDE.md) — a tabela operacional, com o que cada módulo não pode importar
- Achados A-13, A-15 e A-17, no [BOARD](../tasks/BOARD.md)
