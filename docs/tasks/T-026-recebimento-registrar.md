# T-026 — Registrar recebimento

| | |
|---|---|
| **Onda** | W4 |
| **Trilha** | D |
| **Tamanho** | **G** |
| **Depende de** | T-025, T-022 |
| **Componentes** | `recebimento_registrar` |
| **ADRs** | [0005](../adr/0005-l2-leitura-l1-escrita.md) |
| **Regras** | RN-R01, RN-R03, RN-R04, RN-R05, RN-L01, RN-L07, RN-F01, RN-P02, RN-P03 |
| **Requisitos** | RF-04, RF-20 · `US-02` · `RNF-02` |

## Objetivo

O primeiro formulário de escrita. **Registrado como unidade inteira** (L1) — o
modelo escolhe abri-lo; nunca o monta peça por peça.

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/application/registry/componentes/recebimento_registrar.py
api/tests/registry/test_recebimento_registrar.py

api/src/estoque/application/commands/recebimento.py
api/src/estoque/application/commands/entradas/recebimento.py
api/tests/commands/test_recebimento_comandos.py
```

> **Corrigido pelo achado A-15.** Os arquivos em `commands/` não estavam na lista
> original, e sem eles a tarefa não fecha: o componente **declara** o comando, mas
> não pode **executá-lo** — `registry` não importa `commands.pipeline`, porque o
> contrato 2 do import-linter proíbe `registry → sqlalchemy`, inclusive por
> caminho indireto.
>
> `commands/entradas/<dominio>.py` guarda o schema de entrada, e é módulo-folha:
> só pydantic e `domain`. O `CommandDef` do registry e o comando executável
> apontam para **o mesmo schema** — duas declarações do mesmo formulário
> divergiriam (achado A-11). Há teste percorrendo o grafo em
> `tests/registry/test_quarentena_liberar.py` que reprova a folha que deixar de
> ser folha.
>
> **`commands/indice.py` é GERADO** por `make gerar-indice` e não entra em lista
> nenhuma: as cinco tarefas de escrita precisariam da mesma linha nele, que é
> exatamente o caso do acordo de trabalho §4. Rode o gerador; não edite à mão.
>
> `T-027` é o exemplo pronto: `commands/lote.py` + `commands/entradas/lote.py`.

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/recebimento_registrar.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 1 id tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

> **Endpoints corrigidos pelo achado A-16.** A tarefa citava rotas REST por
> recurso; [CONTRATOS §8](./CONTRATOS.md) — normativo e congelado — define
> `/api/comandos/{nome}` como a rota **única** de escrita, com CSRF, `Origin`,
> `Idempotency-Key` e `If-Match` aplicados num lugar só. A hierarquia do acordo
> de trabalho resolve: **`RN-*` > ADR > PRD > tarefa.**

- Formulário multi-etapa: nota → itens (leitor de código de barras) → conferência →
  confirmação.
- Command `recebimento_registrar` — `POST /api/comandos/recebimento_registrar`,
  `requires: 'recebimento.criar'`, **não idempotente** (exige `Idempotency-Key`).
- Lote nasce em **quarentena**, sempre (`RN-R01`).
- Validações de domínio: validade mínima de 6 meses (`RN-L07`), temperatura
  obrigatória se termolábil (`RN-F01`), alocação válida (`RN-P02`, `RN-P03`),
  número/fabricação/validade obrigatórios (`RN-L01`).
- Divergência nota × físico gera pendência e **não impede** a conclusão (`RN-R04`).
- Controlado exige a segunda identificação do RT (`RN-R05`).

### Não faz
Liberar quarentena (T-027).

## Critérios de aceite

> **Nenhum teste de comando passa por interface.** Cada um chama o pipeline
> direto, que é o que uma requisição forjada faz — a única forma de provar
> `RN-A03` e o AC-1, que fala de "requisição forjada" com todas as letras.

- [x] **AC-1** Não existe caminho, nem por requisição forjada, que crie lote com
      status diferente de `quarentena`. *(negativo — `RN-R01`)*
      — três camadas: (1) `extra="forbid"` nos dois schemas, então `status`
      forjado é **recusado** e não ignorado — no corpo **e** dentro do item;
      (2) o `INSERT` escreve `"quarentena"` literal; (3) receber num lote que já
      existe e **saiu** da quarentena é recusado com `conflito`, senão a
      mercadoria cairia em estoque liberado por outro caminho. Com o contraponto:
      receber de novo no mesmo lote **em quarentena** é legítimo e não duplica.
- [x] **AC-2** Validade < 6 meses é recusada; com autorização do RT registrada, é
      aceita. *(`RN-L07`)*
      — e a trilha guarda **quais itens** dependeram da autorização, além do
      texto dela. "Houve autorização" sem dizer de quê não é auditável.
- [x] **AC-3** Termolábil sem temperatura de chegada é recusado. *(negativo —
      `RN-F01`)*
      — com os dois contrapontos: com temperatura passa, e produto comum não
      precisa dela (exigir de todos treinaria o conferente a digitar qualquer
      número).
- [x] **AC-4** Termolábil destinado a unidade seca é recusado. *(negativo —
      `RN-P02`)*
- [x] **AC-5** Controlado destinado a unidade sem sala-cofre é recusado. *(negativo
      — `RN-P03`)*
      — as unidades do teste têm propriedades **opostas** de propósito
      (`cd-matriz` seca **com** cofre, `cd-refrigerado` fria **sem** cofre), para
      cada regra ter um destino que aceita e um que recusa.
- [x] **AC-6** Divergência conclui o recebimento **e** cria pendência. *(`RN-R04`)*
      — o recebimento fica `conferido` com `divergencia = true`. Não impede.
- [x] **AC-7** Rafael, Marco e Sandra **não** conseguem registrar recebimento, nem
      por requisição direta ao endpoint. *(negativo — matriz)*
      — um teste por persona, não um `for`: com dois recusados e um esquecido, o
      laço ainda ficaria verde. **Nem o Diretor** — papel não é nível, é
      conjunto. Com o contraponto de Cleide e Ivo passando.
- [x] **AC-8** O fluxo completo é executável **sem digitação** quando há código de
      barras. Teste de navegação por teclado/leitor. *(`RNF-02`)*
      — destravado pela [T-048](./T-048-porta-produto-por-ean.md). O `ean` é
      **param do componente**: o leitor dispara, o cliente repede os dados com
      `ean=<lido>`, o `load` resolve por `RepoProduto.por_ean`. Sem rota nova.
      Os quatro testes que fazem a mão livre existir: foco no scan ao abrir,
      Enter acrescenta o item sem clique, Enter **não** envia o formulário, e o
      foco **volta** para o scan — este último é o que separa "funciona na
      demonstração" de "funciona na esteira".
- [x] **AC-9** `tamanho: 'inteira'` e não é composto junto de outros blocos.
      *(ADR-0005)*
      — e o `CommandDef` não carrega função nenhuma (ADR-0002), e aponta para o
      **mesmo** schema do comando executável.

## Definição de pronto — adicional
- [x] Contagem de catálogo no BOARD: **+1** (20 → 21 registrados; teto 25).

## Armadilhas

Este é o formulário que testa o ADR-0005 na prática. Se a tentação de quebrá-lo em
blocos compostos aparecer, ela é exatamente o que o ADR proíbe.

**Respeitado:** `tamanho="inteira"`, um `ComponentDef` só, e as quatro etapas
(nota → itens → conferência → confirmação) vivem dentro de uma view React, que é
onde estado entre etapas e foco pertencem.

## A camada que não é falsificável sozinha — registro

O AC-1 tem três camadas, e **só duas são testáveis isoladamente**. Sabotar o
`INSERT` (trocar o `"quarentena"` literal por `getattr(item, "status", ...)`)
**não reprova nada**, porque o `extra="forbid"` impede o campo de chegar. Isso é
defesa em profundidade funcionando — e é também o motivo de a camada 2 não ter
teste próprio.

O que dá para afirmar é o que a sustenta: **não existe campo de status em schema
nenhum**, e os dois recusam campo extra. Esse teste existe, e cai no dia em que
alguém acrescentar um `status` — antes de o `INSERT` ter chance de usá-lo.

## Fora de escopo, e por quê

- **`lote.recebimento_id`** ("lotes gerados"). Segue sem schema, descopado desde
  a T-047 ([A-32](./ACHADOS.md)). Os lotes são criados e a trilha registra quais
  foram, em `valor_novo.lotes` — o que falta é a coluna que ligaria os dois para
  consulta.
- **O formulário avisar antes sobre `RN-P02`/`RN-P03`.** Exigiria `RepoUnidade`,
  que não existe na porta, e seria segunda tarefa de contrato numa entrega só.
  O comando recusa com mensagem que nomeia a regra, e por ADR-0004 o cliente
  nunca foi a garantia. Anotado como limite conhecido.
