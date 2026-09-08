# T-042 — Contract test: o fake e o repositório real obedecem à mesma porta

| | |
|---|---|
| **Trilha** | A · dados |
| **Tamanho** | M |
| **Depende de** | T-007 (repositórios), T-036 (schema) |
| **Origem** | achado da auditoria de testes, 2026-09-08 |

## Por que existe

`api/tests/registry/fakes.py` **reimplementa** a interseção de escopo que
`data/porta.py` promete (`RN-A01`). Hoje, os testes de componente provam que o
*componente* não contorna a porta — e não provam nada sobre o adaptador real.

> Se o repositório SQLAlchemy parar de intersectar escopo, **todos os testes de
> registry continuam verdes.** Um gerente passaria a ver as unidades dos outros,
> e a suíte não diria uma palavra.

`tests/data/` só tem os testes de imutabilidade. Não existe teste de escopo no
adaptador real.

## Arquivos de propriedade exclusiva

```
api/tests/data/test_contrato_da_porta.py
api/tests/data/porta_contrato.py        (a bateria compartilhada)
```

## Só leitura

`api/src/estoque/data/**`, `api/tests/registry/fakes.py`

## Escopo

### Faz

Uma **bateria única** de asserções sobre a porta, executada duas vezes: contra o
fake e contra o repositório real ligado ao Postgres. Parametrize por
implementação — a mesma função de teste, dois `pytest.param`.

O que a bateria tem de cobrir, no mínimo:

| Invariante | Regra |
|---|---|
| interseção de escopo vem **antes** do critério | `RN-A01` |
| `unidade_id` de fora do escopo devolve **vazio**, nunca erro | ADR-0014 |
| `por_id` de registro fora do escopo devolve `None` | ADR-0014 |
| `saldos` só considera movimento `efetivado` | `RN-M06` |
| `saldos` de lote fora do escopo **não aparece no dicionário** | `RN-A01` |
| custo chega **ausente** para quem não tem `custo.ler` | `RN-A02` |
| ordenação estável por `(validade, id)` | paginação por cursor depende disso |

### Não faz

Imutabilidade — já é `tests/data/test_imutabilidade_no_banco.py`.
Não reescreve os fakes; corrige-os se a bateria os reprovar.

## Critérios de aceite

- [ ] **AC-1** A mesma bateria roda contra fake e repositório real, e os dois
      passam.
- [ ] **AC-2** Removendo a interseção de escopo do repositório **real**, a
      bateria **falha**. *(negativo — é o teste que prova que este teste serve)*
- [ ] **AC-3** Removendo a interseção do **fake**, a bateria falha também.
      *(negativo — um fake permissivo é pior que fake nenhum)*
- [ ] **AC-4** Um método novo na porta sem cobertura na bateria é detectado —
      por reflexão sobre o `Protocol`, ou por lista explícita que falha ao
      divergir.
- [ ] **AC-5** No CI, a bateria contra o repositório real **não pula**. Teste
      que pula é teste que não existe.

## Armadilhas

**Bateria escrita a partir do fake.** Se você derivar as asserções lendo
`fakes.py`, vai codificar o comportamento dele — inclusive os erros. Derive de
`data/porta.py` e das `RN-*` citadas; o fake é candidato a estar errado.

**Fixture divergente.** Os dois lados precisam do *mesmo* conjunto de dados, ou
a comparação não vale. O seed determinístico da T-006 é o ponto de partida certo.
