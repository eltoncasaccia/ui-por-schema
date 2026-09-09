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
api/src/estoque/registry/componentes/recebimento_registrar.py
api/tests/registry/test_recebimento_registrar.py

api/src/estoque/commands/recebimento.py
api/src/estoque/commands/entradas/recebimento.py
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

- [ ] **AC-1** Não existe caminho, nem por requisição forjada, que crie lote com
      status diferente de `quarentena`. *(negativo — `RN-R01`)*
- [ ] **AC-2** Validade < 6 meses é recusada; com autorização do RT registrada, é
      aceita. *(`RN-L07`)*
- [ ] **AC-3** Termolábil sem temperatura de chegada é recusado. *(negativo —
      `RN-F01`)*
- [ ] **AC-4** Termolábil destinado a unidade seca é recusado. *(negativo —
      `RN-P02`)*
- [ ] **AC-5** Controlado destinado a unidade sem sala-cofre é recusado. *(negativo
      — `RN-P03`)*
- [ ] **AC-6** Divergência conclui o recebimento **e** cria pendência. *(`RN-R04`)*
- [ ] **AC-7** Rafael, Marco e Sandra **não** conseguem registrar recebimento, nem
      por requisição direta ao endpoint. *(negativo — matriz)*
- [ ] **AC-8** O fluxo completo é executável **sem digitação** quando há código de
      barras. Teste de navegação por teclado/leitor. *(`RNF-02`)*
- [ ] **AC-9** `tamanho: 'inteira'` e não é composto junto de outros blocos.
      *(ADR-0005)*

## Definição de pronto — adicional
- [ ] Contagem de catálogo no BOARD: **+1**.

## Armadilhas

Este é o formulário que testa o ADR-0005 na prática. Se a tentação de quebrá-lo em
blocos compostos aparecer, ela é exatamente o que o ADR proíbe.
