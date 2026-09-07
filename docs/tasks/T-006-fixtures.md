# T-006 — Fixtures da Bertoni

| | |
|---|---|
| **Onda** | W1 — Núcleo |
| **Trilha** | A — Domínio e dados |
| **Tamanho** | M |
| **Depende de** | T-036 |
| **Bloqueia** | T-017, W3 |
| **Paralelizável com** | T-008, T-009, T-010, T-012, T-014 |
| **Regras** | RN-P02, RN-P03, RN-L08, RN-A01 |

## Objetivo

Um conjunto de dados que **contém os casos difíceis**. Fixture que só tem o caminho
feliz esconde exatamente o que o ciclo 1 precisa provar.

## Arquivos de propriedade exclusiva

```
api/src/estoque/data/seed/**   api/tests/data/test_seed.py
```

## Escopo

### Faz

**Unidades (3):** `cd-matriz` (seco), `cd-refrigerado` (refrigerado, câmara fria),
`filial-uberlandia` (seco). Só a Matriz tem sala-cofre.

**Usuários (7):** Marco, Helena, Ivo, Odair, Cleide, Rafael, Sandra — com as
permissões e escopos da matriz do documento 02.

**Produtos (~40):** cobrindo as quatro classes, curvas A/B/C, ativos e inativos,
com e sem custo.

**Lotes (~200):** distribuídos pelas três unidades, cobrindo **obrigatoriamente**:

| Caso | Por quê |
|---|---|
| Mesmo número de lote em duas unidades | `RN-L08` — registros distintos |
| Validade em 15, 45, 89, 91 e 200 dias | Fronteiras de `RN-L04` e `RN-L05` |
| Lote vencido com saldo | `RN-L06` |
| Lote em cada um dos 6 status | máquina de estados |
| Termolábil, só em refrigerado | `RN-P02` |
| Controlado, só na Matriz | `RN-P03` |
| Lote com saldo zero | `esgotado` |

**Movimentos (~2000):** entradas, saídas com cliente e nota (para o recall),
estornos, descartes, e movimentos de controlado em `aguardando_autorizacao`.

**Temperatura:** série de 5 anos na unidade refrigerada, com **pelo menos duas
excursões** fora de 2–8 °C.

### Não faz
Repositórios (T-007). Schema e migrações (T-036). Aqui só os dados.

> O seed roda por `make seed`, é **idempotente** e usa transação — nada de
> `INSERT` solto ([ADR-0018](../adr/0018-postgres-em-container.md)).

## Critérios de aceite

- [ ] **AC-1** Um teste verifica que **todos** os casos difíceis da tabela existem
      nos dados. Fixture que perde um caso quebra o teste.
- [ ] **AC-2** Nenhum lote termolábil fora de unidade refrigerada. *(`RN-P02`)*
- [ ] **AC-3** Nenhum lote controlado fora da Matriz. *(`RN-P03`)*
- [ ] **AC-4** O saldo derivado de todo lote é ≥ 0. *(`RN-M01`)*
- [ ] **AC-5** Existe pelo menos um lote com saídas para ≥ 3 clientes distintos —
      é o caso de teste do recall `CA-01`.
- [ ] **AC-6** Volume suficiente para medir `RNF-01`: o lote de recall tem ≥ 50
      movimentos de saída.
- [ ] **AC-7** Os dados são determinísticos — mesma seed, mesmo resultado. Sem
      `Math.random` sem seed, sem `new Date()`.

## Armadilhas

Fixture com data relativa a `hoje` quebra o teste em datas diferentes. Use uma data
de referência fixa e derive tudo dela.
