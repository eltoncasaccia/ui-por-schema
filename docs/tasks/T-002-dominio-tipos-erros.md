# T-002 — Tipos de domínio, erros e identidade

| | |
|---|---|
| **Onda** | W0 — Contratos · **serial** |
| **Trilha** | A — Domínio |
| **Tamanho** | M |
| **Depende de** | T-001 |
| **Bloqueia** | T-003, T-005, T-006, T-008 |
| **ADRs** | [0014](../adr/0014-erros-que-nao-vazam.md), [0022](../adr/0022-status-registrado-e-efetivo.md) |
| **Regras** | RN-M02, RN-M04, RN-M06, RN-A01, RN-A07, RN-P01 |

## Objetivo

Escrever em código as seções 1, 2 e 3 de [CONTRATOS.md](./CONTRATOS.md). É o
vocabulário do qual todo o resto depende.

## Arquivos de propriedade exclusiva

```
api/src/estoque/domain/identidade.py   api/src/estoque/domain/erros.py   api/src/estoque/domain/tipos.py
api/src/estoque/domain/index.py        api/src/estoque/domain/*.test.py
```

## Escopo

### Faz
- `PapelId`, `UnidadeId`, `Permissao` (20 valores), `Ator`.
- `CodigoErro`, `ErroDominio` com `detalheInterno` **não serializável**.
- **As sete entidades** de [CONTRATOS §3](./CONTRATOS.md): `Produto`, `Lote`,
  `Movimento`, `Recebimento`, `RegistroTemperatura`, `Unidade`, `Usuario` — todas
  `@dataclass(frozen=True, slots=True)`.
- **`StatusLoteRegistrado` e `StatusLoteEfetivo` separados** ([ADR-0022](../adr/0022-status-registrado-e-efetivo.md)).
- Enums fechados: `ClasseProduto`, `TipoUnidade`, `StatusLote`, `TipoMovimento`,
  `StatusMovimento`, `MotivoMovimento`.

### Não faz
- Regras de negócio (T-008). Aqui só tipos.
- Persistência, validação de entrada, React.

## Critérios de aceite

> **Verificado por** `tests/domain/` — auditado em [A-002](../relatorios/A-002-auditoria-de-execucao.md).

- [ ] **AC-1** `Lote` **não possui** campo `saldo` **nem** os valores `vencido`/
      `esgotado` no seu status. Teste inspeciona os campos do dataclass.
      *(`RN-M06` + [ADR-0022](../adr/0022-status-registrado-e-efetivo.md) — o achado A-04)*
- [ ] **AC-2** `Movimento` não tem setter nem campo mutável; toda propriedade é
      `readonly`. *(`RN-M02`)*
- [ ] **AC-3** `ErroDominio.detalheInterno` não aparece em `JSON.stringify(erro)`.
      *(negativo — ADR-0014)*
- [ ] **AC-4** `Ator.permissoes` é `frozenset` e o dataclass é `frozen` — mutação
      levanta em runtime **e** `mypy --strict` a recusa. *(negativo)*
- [ ] **AC-4b** `Usuario` **não tem** campo de senha nem de hash. *(negativo —
      credencial não pertence ao domínio)*
- [ ] **AC-5** Todo enum é `Literal[...]`, não `enum.Enum` — para que valor fora
      do conjunto seja erro de tipo **e** de validação Pydantic.
- [ ] **AC-6** Valores monetários são `int` em centavos, com sufixo `_centavos`.
      *(negativo — nenhum `float` para dinheiro)*
- [ ] **AC-7** `ErroDominio.detalhe_interno` não aparece em nenhuma serialização.
      *(negativo — [ADR-0014](../adr/0014-erros-que-nao-vazam.md))*

## Armadilhas

A tentação de "só um campo de saldo para facilitar" volta em toda tarefa de
leitura. Ela é a divergência de 3,8% do documento 01, reintroduzida.
