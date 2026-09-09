# T-023 — Cadeia fria · `CA-07`

| | |
|---|---|
| **Onda** | W3 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-007, T-009, T-012, T-015 · liberada por T-017 |
| **Componentes** | `temperatura_historico` `temperatura_excursoes` |
| **Regras** | RN-F02, RN-F03, RN-F04 |
| **Requisitos** | RF-11, RF-12 · `CA-07` · `RNF-06` |

## Objetivo

O componente que responde ao auto de infração da ANVISA: histórico consultável e
exportável, com cinco anos de retenção.

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/application/registry/componentes/temperatura_historico.py
api/src/estoque/application/registry/componentes/temperatura_excursoes.py
api/tests/registry/test_temperatura_historico.py
api/tests/registry/test_temperatura_excursoes.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/temperatura_historico.tsx
web/src/views/temperatura_excursoes.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 2 ids tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz

| Componente | Params | `requires` | Tamanho |
|---|---|---|---|
| `temperatura_historico` | `unidadeId` `de` `ate` | `temperatura.ler` | `alta` |
| `temperatura_excursoes` | `unidadeId` `de?` `ate?` | `temperatura.ler` | `inteira` |

- Histórico: série temporal com faixa 2–8 °C marcada, exportável.
- Excursões: ocorrências fora da faixa **com os lotes presentes na unidade no
  período** (`RN-F04`) — é o vínculo que a inspeção pede.

### Não faz
Decidir destino de lote em excursão — é do RT, via `lote_status_acao` (T-027).

## Critérios de aceite

- [ ] **AC-1** Consulta por período de 5 anos responde dentro do limite de tela
      (`RNF-04`), com agregação por intervalo quando o período é longo.
      *(`RNF-06`)*
- [ ] **AC-2** Exportação disponível e com os mesmos dados da tela. *(`CA-07`)*
- [ ] **AC-3** Toda excursão das fixtures aparece, com os lotes vinculados.
      *(`RN-F04`)*
- [ ] **AC-4** Lote presente na unidade no período da excursão aparece vinculado;
      lote que entrou depois **não** aparece. *(negativo — precisão do vínculo)*
- [ ] **AC-5** Como Odair, temperatura do CD Refrigerado é negada — não é unidade
      dele. *(negativo — `CA-06`)*
- [ ] **AC-6** Período invertido (`de > ate`) é rejeitado. *(negativo)*

## Definição de pronto — adicional
- [ ] Contagem de catálogo no BOARD: **+2**.

## Armadilhas

AC-4 é o critério que dá valor regulatório ao componente. Vincular todo lote da
unidade, sem filtrar pela janela de presença, produz lista inflada e inútil na
inspeção.
