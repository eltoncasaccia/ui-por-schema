# T-029 — Estorno e descarte

| | |
|---|---|
| **Onda** | W4 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-025, T-024 |
| **Componentes** | `movimento_estorno` `movimento_descarte` |
| **Regras** | RN-M02, RN-M03, RN-M05, RN-L06, §4.1 |
| **Requisitos** | RF-02, RF-03 · `US-07` · `CA-08` |

## Objetivo

Corrigir sem apagar história. É a implementação direta de `CA-08` — **excluir
movimento é recusado para todos, incluindo Diretor.**

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/application/registry/componentes/movimento_estorno.py
api/src/estoque/application/registry/componentes/movimento_descarte.py
api/tests/registry/test_movimento_estorno.py
api/tests/registry/test_movimento_descarte.py

api/src/estoque/application/commands/estorno.py
api/src/estoque/application/commands/entradas/estorno.py
api/tests/commands/test_estorno_comandos.py

api/src/estoque/application/commands/descarte.py
api/src/estoque/application/commands/entradas/descarte.py
api/tests/commands/test_descarte_comandos.py
```

> **Corrigido na execução, pela mesma razão do A-15.** A lista trazia os arquivos
> de `commands/` do **estorno** e não os do **descarte** — e são dois comandos,
> não um. Enfiar os dois em `estorno.py` faria um módulo chamado "estorno"
> executar descarte; a correção é a lista, não o código. Nenhum dos três arquivos
> novos pertence a outra tarefa.

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
web/src/views/movimento_estorno.tsx
web/src/views/movimento_descarte.tsx
web/src/testes/movimento_estorno_descarte.test.tsx
```

> O arquivo de teste do cliente também faltava na lista, e o AC-6 e o AC-7 têm
> metade do lado de cá: a tela avisa antes de o servidor recusar. Mesmo
> tratamento que a T-026 deu ao `recebimento_registrar.test.tsx`.

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 2 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

> **Endpoints corrigidos pelo achado A-16.** A tarefa citava rotas REST por
> recurso; [CONTRATOS §8](./CONTRATOS.md) — normativo e congelado — define
> `/api/comandos/{nome}` como a rota **única** de escrita, com CSRF, `Origin`,
> `Idempotency-Key` e `If-Match` aplicados num lugar só. A hierarquia do acordo
> de trabalho resolve: **`RN-*` > ADR > PRD > tarefa.**


| Componente | Command | `requires` |
|---|---|---|
| `movimento_estorno` | `POST /api/comandos/movimento_estorno` | `movimento.estornar` |
| `movimento_descarte` | `POST /api/comandos/movimento_descarte` | `movimento.descartar` |

- Estorno referencia o original, exige motivo de lista fechada, e **não modifica**
  o original (`RN-M03`).
- Descarte é a única saída possível para lote vencido ou bloqueado (`RN-L06`), e
  leva o lote a `descartado` (§4.1). Exige Gerente **e** RT.
- Ambos declaram `CommandDef.confirm = True` — são irreversíveis. **Não existe
  componente `confirm_action`**: confirmar é decisão do motor de render diante do
  `confirm`, não composição que o modelo escolhe (achado A-05).

### Não faz
Exclusão. Não existe, em lugar nenhum, para ninguém.

## Critérios de aceite

- [x] **AC-1** Não existe rota, comando ou caminho de código que exclua ou edite
      movimento. Teste percorre as rotas registradas e afirma a ausência.
      *(negativo — `CA-08`, `RN-M02`)*
- [x] **AC-2** Marco (Diretor) tentando excluir movimento é recusado igual a
      qualquer outro papel. *(negativo — `CA-08`)*
- [x] **AC-3** Estorno cria movimento novo e o original permanece **byte a byte
      inalterado**. *(`RN-M03`)*
- [x] **AC-4** Saldo após estorno é a soma dos dois movimentos, sem edição de
      campo. *(`RN-M06`, `AC-07.3` do PRD)*
- [x] **AC-5** Estorno sem motivo de lista fechada é recusado. *(negativo)*
- [x] **AC-6** Descarte de lote **liberado e válido** é recusado — descarte não é
      atalho de saída. *(negativo — `RN-L06`)*
- [x] **AC-7** Descarte exige as duas identificações (Gerente e RT). *(negativo)*
- [x] **AC-8** Ambos passam por `confirm_action` antes de aplicar.

> **Onde cada um foi verificado.** AC-1 a AC-5 e AC-8 em
> `api/tests/commands/test_estorno_comandos.py` (25 testes, contra Postgres);
> AC-6 e AC-7 em `api/tests/commands/test_descarte_comandos.py` (18);
> a metade de tela dos dois em `web/src/testes/movimento_estorno_descarte.test.tsx`
> (15); leitura, catálogo por ator e escopo em `api/tests/registry/`
> (24 + 25). **AC-8 é a bandeira `confirm`, dos dois lados da declaração** —
> não existe componente `confirm_action` (achado A-05), e confirmar é decisão do
> motor de render.
>
> **Seis proteções foram sabotadas de propósito**, e o teste reprovou nas seis:
> o par de papéis do descarte, a lista de estados descartáveis, a de tipos
> estornáveis, o `ja_estornado`, e uma rota `DELETE /api/movimentos/{id}`
> acrescentada à borda — que reprovou o AC-1 **e** o AC-2.

## Definição de pronto — adicional
- [x] Contagem de catálogo no BOARD: **+2** (21 → **23**, teto 25).

## O que ficou fora, e por quê

- **Estorno de entrada não existe** — achado [A-38](./ACHADOS.md). O sinal de
  `estorno` é fixo e positivo na view `saldo_lote` (migração 0001, congelada):
  estornar uma entrada somaria de novo o que se queria desfazer. O comando
  recusa, com o par negativo testado dos dois lados.
- **Descarte de lote sem saldo é recusado.** `quantidade > 0` é `CHECK` da
  migração 0001, e um lote sem saldo já não ocupa prateleira. Um lote vencido e
  zerado, portanto, continua com o status registrado que tinha.
- **As listas de motivos seguem derivadas do enum** (A-19, aberto), como a T-028
  fez para a saída. O que `RN-M05` exige — lista fechada por tipo, texto livre
  como complemento — está implementado e testado; **quais** valores é resposta do
  cliente.

## Armadilhas

AC-1 precisa ser um teste sobre as **rotas registradas**, não sobre a interface.
Ausência de botão não é ausência de endpoint.
