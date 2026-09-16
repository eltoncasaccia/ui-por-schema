# ADR-0029 — Relatório é um componente parametrizado, não uma consulta gerada

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-08 |
| **Escopo** | Catálogo e assistente |
| **Consequência de escopo** | **+1 componente** — o catálogo vai a 24, e a folga do [ADR-0011](./0011-teto-de-catalogo.md) cai de 2 para 1 |

## Contexto

Os componentes do catálogo respondem perguntas **fixas com recorte fechado**:
`fila_vencimento` responde "o que vence", `lote_lista` responde "quais lotes".
Cada pergunta nova que não caiba num deles exige um componente novo — escrito,
testado e registrado por um desenvolvedor.

Isso funciona para operação, e falha para **relatório**. Um relatório é a mesma
pergunta com eixos trocados: *movimentação por unidade*, *por produto*, *por
motivo*, *no trimestre*, *só descartes*. A combinatória é grande, o esforço por
combinação é o mesmo de um componente inteiro, e o teto de 25 acaba antes de a
necessidade acabar.

O sintoma prático: toda vez que alguém quiser um corte novo, a resposta do
sistema é `blocos: []` — e a resposta da equipe é "abrimos uma tarefa".

## Decisão

> **Um componente de relatório, com dimensões, métrica e recorte como enums
> fechados vindos do modelo de dados. Quem escolhe os eixos é o usuário; o
> modelo apenas preenche parâmetros que já existiam.**

O primeiro é `relatorio_movimentacao`:

| Param | Valores | Observação |
|---|---|---|
| `agrupar_por` | `unidade` `produto` `motivo` `mes` `classe` | eixo do relatório |
| `metrica` | `quantidade` `movimentos` `valor` | `valor` **exige `custo.ler`** |
| `tipo` | `entrada` `saida` `descarte` `estorno` `todos` | |
| `periodo` | `30` `90` `180` `365` | janela nomeada, nunca data solta |
| `unidade_id` | opcional | interseção de escopo continua na porta |

Cinco eixos × três métricas × cinco tipos × quatro janelas = **300 relatórios**
com **um** componente e ~164 tokens de catálogo.

A métrica `valor` usa `RequiresPorValor` — o mecanismo que já existe e já é
testado em `estoque_indicador` (achado A-05): para quem não tem `custo.ler`, o
valor **some do enum**, e o modelo não consegue nem propor. Não é campo
condicional escondido no `select`; é vocabulário que não existe.

Relatório salvo é uma **`viewId`** ([ADR-0021](./0021-viewkey-e-viewid.md)):
favoritável, compartilhável, e carregado sob a permissão de **quem abre** —
nunca de quem enviou.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Um componente por relatório** | é o que fazemos hoje. Cada corte novo custa uma tarefa, e o teto de 25 chega antes de a necessidade acabar |
| **Text-to-SQL** | o modelo passaria a escolher **os dados**, e não o que mostrar — contraria a regra 1 do [ADR-0001](./0001-ui-por-schema.md). Um `WHERE unidade_id` esquecido é vazamento de escopo, e a falha é silenciosa: devolve mais linhas, e mais linhas parecem uma resposta boa |
| **Pivot genérico com dimensões livres** | dimensão livre é texto livre com outro nome. Reabre o risco R-5 — o filtro que falta alarga a resposta sem ninguém perceber |
| **Construtor de relatório fora do catálogo** | perde a composição pelo assistente e a `viewId`. E o formulário teria de reimplementar a filtragem de permissão que o catálogo já faz |

A diferença entre o pivot genérico recusado e o aceito é **uma só**: aqui as
dimensões vêm de um `Literal` derivado do modelo de dados, e são filtradas por
permissão como qualquer outro enum. Um eixo que o usuário não pode ver não
existe no vocabulário dele.

## Consequências

**Ganhos**
- 300 combinações por um componente. O catálogo deixa de crescer por pergunta.
- O usuário monta o próprio corte, sem abrir tarefa.
- Reaproveita `RequiresPorValor`, `viewId` e a exportação que já existem.
  *(Emenda, 2026-09-16: a exportação não existia fora da temperatura. Ela passou
  a existir com o [ADR-0035](./0035-exportacao-no-servidor.md).)*

**Custos aceitos**
- **A folga do catálogo cai de 2 para 1.** Um segundo relatório
  (`relatorio_perdas`, por exemplo) estoura o teto e vira discussão de escopo,
  como o ADR-0011 manda.
- `load` mais caro: agregação por dimensão variável é uma consulta mais pesada
  que uma listagem. Precisa de índice, e precisa de teto de linhas.
- Mais superfície de teste: cada eixo é um caminho de `select`, e todos
  precisam ser exercitados.

**Riscos**
- **O eixo que falta continua invisível.** Se um operador pensa em "por
  fornecedor" e esse valor não está no enum, ele recebe um relatório
  parecido e errado. O risco R-5 não desaparece — muda de lugar. A auditoria de
  enums da [T-032](../tasks/T-032-suite-de-avaliacao.md) passa a valer também
  para os eixos.
- Um componente com 300 saídas é difícil de descrever em ~164 tokens sem que a
  `description` fique vaga. Descrição vaga produz composição errada, e a falha é
  silenciosa.

## Como é verificado em código

- `relatorio_movimentacao` registrado, com `Params` de enums fechados
- teste negativo: `Params.model_validate({"agrupar_por": "fornecedor"})` levanta
  `ValidationError`
- teste negativo: `metrica: "valor"` **ausente do enum** no catálogo de Cleide,
  Helena, Ivo e Odair — e presente no de Marco, Rafael e Sandra
- teste: `select` puro, e o viewmodel **sem custo** quando a métrica não é `valor`
- cenário 10 de [CENARIOS.md](../CENARIOS.md), executado à mão
- contagem de catálogo no BOARD §5 atualizada para 24

## Referências
[ADR-0001](./0001-ui-por-schema.md) · [ADR-0003](./0003-catalogo-por-ator.md) ·
[ADR-0011](./0011-teto-de-catalogo.md) · [ADR-0020](./0020-select-no-servidor.md) ·
[ADR-0021](./0021-viewkey-e-viewid.md) · [T-044](../tasks/T-044-relatorio-movimentacao.md)
