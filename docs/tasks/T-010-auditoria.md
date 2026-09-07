# T-010 — Trilha de auditoria append-only

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | B |
| **Tamanho** | M |
| **Depende de** | T-004 |
| **Bloqueia** | T-011 |
| **Paralelizável com** | T-009, T-012, T-014 |
| **Regras** | RN-D01, RN-D02, RN-D05 |
| **Requisitos** | RF-15, RF-16, CS-05 |

## Objetivo

Registro imutável de tudo. Inclui o que quase todo sistema esquece: **a consulta
também é auditada** (`RN-D05`).

## Arquivos de propriedade exclusiva

```
api/src/estoque/auditoria/*.py   api/src/estoque/auditoria/*.test.py
```

## Escopo

### Faz
- `registrar(evento)` — append-only. Sem update, sem delete, **sem exceção**.
- Evento de escrita: quem, o quê, quando, valor anterior, valor novo, origem
  (`tela` | `assistente`).
- Evento de leitura: ator, entidade consultada, filtros, `viewKey` quando houver.
- Evento de composição do assistente: pergunta, schema resultante, componentes
  compostos, aceitos e rejeitados.

### Não faz
Componente de consulta da trilha (T-024). Aqui só a escrita.

## Critérios de aceite

- [ ] **AC-1** A API **não expõe** método de update nem de delete. Não é validação
      em runtime: o tipo não tem a função. *(`RN-D02`)*
- [ ] **AC-2** Uma tentativa de mutar um evento já registrado não compila e, se
      forçada, não altera o armazenado. *(negativo)*
- [ ] **AC-3** Toda consulta a repositório gera evento de leitura. Teste: executar
      uma consulta e afirmar que o evento existe. *(`RN-D05`, `CS-05`)*
- [ ] **AC-4** Toda resposta do assistente gera evento com schema e componentes
      rejeitados. *(`CS-05`)*
- [ ] **AC-5** `criadoEm` vem **sempre** do servidor, nunca do cliente. Timestamp
      enviado pelo cliente é ignorado. *(negativo — `RN-M04`)*
- [ ] **AC-6** O evento de auditoria **não contém** campos restritos: custo não
      entra na trilha lida por quem não tem `custo.ler`.

## Armadilhas

AC-6 é o vazamento clássico: o sistema protege o campo na tela e o expõe no log de
auditoria, que Sandra pode ler.
