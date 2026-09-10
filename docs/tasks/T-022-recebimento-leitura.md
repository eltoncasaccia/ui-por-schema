# T-022 — Recebimento, leitura

| | |
|---|---|
| **Onda** | W3 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-007, T-009, T-012, T-015 · liberada por T-017 |
| **Bloqueia** | T-026 |
| **Componentes** | `recebimento_lista` `recebimento_detalhe` |
| **Regras** | RN-R01, RN-R03, RN-R04, RN-R05, RN-F01, RN-A01 |

## Objetivo

Ver o que entrou e em que estado está. Base de leitura para o formulário de
registro (T-026).

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/application/registry/componentes/recebimento_lista.py
api/src/estoque/application/registry/componentes/recebimento_detalhe.py
api/tests/registry/test_recebimento_lista.py
api/tests/registry/test_recebimento_detalhe.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/recebimento_lista.tsx
web/src/views/recebimento_detalhe.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 2 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Componente | Params | `requires` | Tamanho |
|---|---|---|---|
| `recebimento_lista` | `unidadeId?` `status?` `de?` `ate?` | `recebimento.ler` | `inteira` |
| `recebimento_detalhe` | `recebimentoId` | `recebimento.ler` | `inteira` |

- Detalhe mostra: conferência registrada (integridade, validade, nota,
  temperatura se termolábil), lotes gerados, **pendências** de divergência
  (`RN-R04`), e as identificações no caso de controlado (`RN-R05`).

### Não faz
Registrar recebimento (T-026). Liberar quarentena (T-027).

## Critérios de aceite

- [ ] **AC-1** Todo recebimento listado gerou lote em **quarentena**; não existe
      recebimento com lote nascido liberado nas fixtures nem no caminho.
      *(`RN-R01`)*
      — **em branco.** Não há vínculo `recebimento → lote` (`lote.recebimento_id`
      nunca teve schema, descopado pela T-047 / [A-32](./ACHADOS.md)). Sem o
      vínculo não há o que asseverar sobre o status do lote gerado. Volta com a
      tarefa de contrato que criar `lote.recebimento_id`.
- [x] **AC-2** Recebimento com divergência exibe a pendência vinculada, e a
      pendência não impede a conclusão. *(`RN-R04`)*
      — `divergencia` na linha e `tem_pendencia_divergencia` no detalhe;
      `r-diverg-mtz` segue `conferido`, não um estado de erro.
      `test_recebimento_lista::test_ac2_*`, `test_recebimento_detalhe::test_ac2_*`.
- [x] **AC-3** Recebimento de controlado exibe as **duas** identificações.
      *(`RN-R05`)*
      — `recebimento_detalhe` expõe `conferente` e `responsavel_tecnico`;
      `r-controlado-mtz` traz os dois, `r-normal-mtz` tem `responsavel_tecnico`
      `None` (negativo). `test_recebimento_detalhe::test_ac3_*`.
- [x] **AC-4** Recebimento de termolábil exibe a temperatura de chegada. *(`RN-F01`)*
      — `r-termo-ref` → `temperatura_chegada_c == 5.4`; `r-normal-mtz` → `None`.
      `test_recebimento_detalhe::test_ac4_*`.
- [x] **AC-5** Como Odair, apenas recebimentos de Uberlândia. *(negativo — `CA-06`)*
      — lista de Odair == `{r-uber}`; pedindo `unidade_id="cd-matriz"` vem vazio;
      `por_id("r-normal-mtz")` como Odair === id inexistente (`nao_encontrado`,
      face pública idêntica, ADR-0014). `test_recebimento_lista::test_ac5_*`,
      `test_recebimento_detalhe::test_ac5_*`.
- [x] **AC-6** `status` é enum fechado. *(negativo — risco R-5)*
      — `Params.model_validate({"status": "parcial"})` levanta `ValidationError`;
      idem `periodo` inválido. O recorte de período é `periodo` (enum
      `7/30/90/365/tudo`), **não** `de`/`ate` soltos como a tarefa dizia — data
      livre alarga a resposta em silêncio (risco R-5); mesmo tratamento de
      `movimento_lista`. `test_recebimento_lista::test_ac6_*`.
- [x] **AC-7** Nenhum custo exposto. *(`CA-05`)*
      — `model_dump_json()` das duas VMs não contém `custo` nem `centavos`, nem
      para Marco (tem `custo.ler`). `Recebimento` não carrega custo e nada aqui o
      busca. `test_recebimento_*::test_ac7_*`.

## Definição de pronto — adicional
- [x] Contagem de catálogo no BOARD: **+2** (16 → 18 registrados; teto 25).
