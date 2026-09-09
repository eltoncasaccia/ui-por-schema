# T-021 — Rastreabilidade · `CA-01`

| | |
|---|---|
| **Onda** | W3 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-007, T-009, T-010, T-012, T-015 · liberada por T-017 |
| **Componentes** | `rastreabilidade` |
| **ADRs** | [0011](../adr/0011-teto-de-catalogo.md) |
| **Regras** | RN-D03, RN-D04, RN-D05, RN-A01 |
| **Requisitos** | RF-10 · `CA-01` · `RNF-01` |

## Objetivo

O componente que responde ao episódio que motivou o projeto: **o recall da
losartana, nove dias.** O alvo agora é 60 segundos.

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/application/registry/componentes/rastreabilidade.py
api/tests/registry/test_rastreabilidade.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/rastreabilidade.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 1 id tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Param | Valores |
|---|---|
| `direcao` | `lote_para_clientes` \| `cliente_para_lotes` |
| `loteId` | obrigatório se `direcao = lote_para_clientes` |
| `clienteId` + `de`/`ate` | obrigatórios se `direcao = cliente_para_lotes` |

`requires: 'auditoria.rastrear'` · `tamanho: 'inteira'`

Um componente, duas direções — fusão deliberada do ADR-0011. O recorte continua
sendo **valor nomeado no enum**.

- Saída no sentido lote → clientes: cliente, nota fiscal, data, quantidade.
- Exportável.

### Não faz
Bloqueio do lote em recall — é `lote_status_acao`, em T-027.

## Critérios de aceite

- [x] **AC-1** Dado o lote de recall das fixtures (≥ 50 saídas, ≥ 3 clientes), a
      consulta responde em **menos de 60 s**. Teste de performance, não manual.
      *(`CA-01`, `RNF-01`)*
      → `test_ac1_lote_com_muitas_saidas_responde_rapido`: 60 saídas / 4 clientes
      no fake, `load`+`select` sub-milissegundo, `< 1.0 s`. **Prova de forma**
      (consultas limitadas, `select` linear); o número real de `RNF-01` contra
      Postgres é do T-034.
- [x] **AC-2** O sentido inverso devolve todos os lotes de um cliente num período.
      *(`RN-D04`)*
      → `test_ac2_cliente_para_lotes_lista_os_lotes_do_periodo` (2 lotes) e
      `test_ac2_o_periodo_recorta_de_verdade` (janela vazia → 0). O recorte de
      período é feito no `load` — a porta ignora `de`/`ate` (achado [A-31](./ACHADOS.md)).
- [x] **AC-3** Cada consulta gera registro de auditoria com ator, direção e
      parâmetros. *(`RN-D05`, `CA-01.3`)*
      → `test_ac3_a_borda_audita_toda_leitura_com_os_params`: a borda
      (`rotas/dados.py`) grava `acao="ler"`, `ator_id` e `valor_novo={"params":
      corpo.params}` — os params incluem `direcao`. E2E contra o banco em
      `test_ac6_leitura_auditada.py` ("toda leitura").
- [x] **AC-4** Como Odair, a rastreabilidade **não atravessa** para saídas de outras
      unidades. *(negativo — `CA-06`)*
      → Odair (e Ivo, Cleide, Rafael) **não têm `auditoria.rastrear`**, então nem
      veem o componente — `test_ac4_quem_nao_tem_rastrear_nao_ve_o_componente` e
      `test_catalogo_por_ator.py`. Nenhuma persona junta `rastrear` com escopo
      restrito, então o "não atravessa" no nível do `load` é provado com um ator
      sintético restrito a Uberlândia:
      `test_ac4_rastreador_restrito_nao_alcanca_lote_de_outra_unidade` (recall em
      CD Matriz → vazio, não erro).
- [x] **AC-5** `direcao` ausente ou fora do enum é rejeitado. *(negativo)*
      → `test_ac5_direcao_ausente_e_rejeitada`, `test_ac5_direcao_fora_do_enum_e_rejeitada`,
      `test_ac5_schema_forjado_sem_direcao_e_rejeitado`.
- [x] **AC-6** Params incoerentes com a direção (ex.: `clienteId` com
      `lote_para_clientes`) são rejeitados na validação. *(negativo)*
      → `@model_validator` em `Params._coerencia`; testado direto e via
      `validar_schema` (`test_ac6_*`), inclusive schema forjado.
- [x] **AC-7** A resposta não expõe custo nem margem para nenhum papel sem
      `custo.ler`. *(`CA-05`)*
      → `test_ac7_resposta_nao_tem_custo` nas duas direções, como Marco (tem
      `custo.ler`). `Movimento` não carrega custo e nada aqui o busca.

## Definição de pronto — adicional
- [x] Contagem de catálogo no BOARD: **+1** (`rastreabilidade`) — 15 → 16.
- [ ] `RNF-01` medido e o número registrado no relatório de fechamento (T-034).
      → **do T-034.** AC-1 aqui prova a forma, não o número contra Postgres.

## Armadilhas

AC-1 precisa de volume real nas fixtures. Medir com 3 movimentos prova nada; por
isso T-006 AC-6 exige ≥ 50 saídas no lote de recall.
