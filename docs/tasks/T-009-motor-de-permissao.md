# T-009 — Motor de permissão e escopo de unidade

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | B — Servidor e permissão |
| **Tamanho** | M |
| **Depende de** | T-004 |
| **Bloqueia** | T-011, T-012 |
| **ADRs** | [0004](../adr/0004-autorizacao-em-tres-momentos.md), [0014](../adr/0014-erros-que-nao-vazam.md) |
| **Regras** | RN-A01..A07, RN-C01, RN-I01 |
| **Requisitos** | CS-02, CS-03 |

## Objetivo

O componente que **de fato** protege. Os outros dois momentos de autorização são
higiene; este é a garantia (ADR-0004).

## Arquivos de propriedade exclusiva

```
api/src/estoque/autorizacao/*.py   api/src/estoque/autorizacao/*.test.py
```

## Escopo

### Faz
- `podeExecutar(ator, requires): boolean`.
- `escopoDe(ator): UnidadeId[]` — interseção sempre aplicada.
- `autorizarOuFalhar(ator, requires, alvo?)` lançando `ErroDominio` com o **código
  correto conforme ADR-0014**:
  - escopo declarado negado → `nao_autorizado`
  - registro individual fora de escopo → `nao_encontrado`
- `mesmaPessoa(a, b)` para separação de funções (`RN-A04`, `RN-C01`, `RN-I01`).
- Ator inativo é sempre negado (`RN-A06`).

### Não faz
HTTP (T-011). Catálogo (T-012).

## Critérios de aceite

- [ ] **AC-1** Matriz completa testada: **para cada um dos 7 usuários × cada uma
      das 20 permissões**, o resultado bate com a matriz do documento 02. 140 casos,
      gerados por tabela.
- [ ] **AC-2** Helena é a **única** que passa em `lote.liberar`. *(`RN-R02`)*
- [ ] **AC-3** Ninguém, incluindo Marco, passa em uma permissão inexistente.
      *(negativo)*
- [ ] **AC-4** Ator com `ativo: false` é negado em tudo, mesmo com as permissões
      presentes. *(negativo — `RN-A06`)*
- [ ] **AC-5** Negativa de unidade devolve `nao_autorizado`; negativa de registro
      devolve `nao_encontrado`. *(ADR-0014, `CA-06`)*
- [ ] **AC-6** `mesmaPessoa` impede que autor e autorizador coincidam. *(negativo —
      `CA-04`)*
- [ ] **AC-7** Nenhuma mensagem de erro contém id, nome de registro ou contagem.

## Armadilhas

A tentação de um atalho `if (ator.papel === 'diretor') return true`. Diretor **não**
pode liberar quarentena (`RN-R02`) nem excluir movimento (`CA-08`). Papel não é
nível; é conjunto.
