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

- [x] **AC-1** Consulta por período de 5 anos responde dentro do limite de tela
      (`RNF-04`), com agregação por intervalo quando o período é longo.
      *(`RNF-06`)*
      — `select` agrega em ≤ `LIMITE_PONTOS` (480) baldes de tempo acima desse
      volume; `agregado`/`pontos`/`baldes` no viewmodel. Provado com série
      sintética de 7.300 leituras (5 anos, 6/6 h): `agregado`, ≤ 480 baldes,
      excursão plantada sobrevive à agregação (`tem_excursao`). Série curta vem
      ponto a ponto. `test_temperatura_historico::test_ac1_*`. **`RNF-04` (2 s
      medido) fica para T-034** — aqui a garantia é estrutural (saída limitada).
- [x] **AC-2** Exportação disponível e com os mesmos dados da tela. *(`CA-07`)*
      — `csv` no viewmodel, montado por `select` das **mesmas** linhas
      (`pontos` ou `baldes`) que a tela desenha, então "mesmos dados" é
      verdadeiro por construção e testado. A view oferece como download
      client-side. **Não há endpoint de export no ciclo 1** ([A-23](./ACHADOS.md));
      esta é a forma que cabe nos arquivos da tarefa. `test_temperatura_historico::test_ac2_*`.
- [x] **AC-3** Toda excursão das fixtures aparece, com os lotes vinculados.
      *(`RN-F04`)*
      — a série `TEMPERATURAS` tem uma excursão de calor (duas leituras a
      9,8 °C); `temperatura_excursoes` a devolve com sentido, pico, duração e os
      lotes. `test_temperatura_excursoes::test_ac3_*`.
- [x] **AC-4** Lote presente na unidade no período da excursão aparece vinculado;
      lote que entrou depois **não** aparece. *(negativo — precisão do vínculo)*
      — corte: entrada na unidade com `criado_em <= fim da excursão`.
      `l-vac-quar` e `l-vac-quar-venc` (entraram antes) aparecem;
      `l-vac-ref-tardio` (fixture nova, `m-13`, entra hoje) **não**.
      `test_temperatura_excursoes::test_ac4_*`.
- [x] **AC-5** Como Odair, temperatura do CD Refrigerado é negada — não é unidade
      dele. *(negativo — `CA-06`)*
      — `unidade_id` fora do escopo → `nao_encontrado`, face pública idêntica a
      unidade inexistente (ADR-0014), nos dois componentes. Contraponto: Ivo
      alcança e vê a série. `test_temperatura_*::test_ac5_*`.
- [x] **AC-6** Período invertido (`de > ate`) é rejeitado. *(negativo)*
      — `model_validator` recusa na validação, antes do `load`. Em
      `temperatura_excursoes`, `de` sem `ate` (recorte pela metade) também é
      recusado. `test_temperatura_*::test_ac6_*`.

## Definição de pronto — adicional
- [x] Contagem de catálogo no BOARD: **+2** (18 → 20 registrados; teto 25).

## Armadilhas

AC-4 é o critério que dá valor regulatório ao componente. Vincular todo lote da
unidade, sem filtrar pela janela de presença, produz lista inflada e inútil na
inspeção. **Resolvido:** o vínculo exige `entrada.criado_em <= fim da excursão`,
e a fixture `l-vac-ref-tardio` prova o corte pelo lado negativo. Ciclo 1 não tem
transferência entre unidades, então "presente" é "entrou até então" — quando
houver saída de lote inteiro, o corte ganha um limite superior.
