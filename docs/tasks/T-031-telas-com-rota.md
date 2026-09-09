# T-031 — Superfície tradicional: telas com rota

| | |
|---|---|
| **Onda** | W5 — Garantias |
| **Trilha** | D |
| **Tamanho** | **G** |
| **Depende de** | T-026, T-027, T-028 |
| **Bloqueia** | T-034 |
| **ADRs** | [0005](../adr/0005-l2-leitura-l1-escrita.md) |
| **Requisitos** | `RNF-04` · PRD §5.3 |

## Objetivo

Provar o ganho colateral do ADR-0005: **o mesmo componente registrado serve à rota
tradicional e ao assistente.** Uma declaração, duas superfícies.

E aplicar a regra §11.5 da arquitetura: **o assistente não é o app.** A operação de
alta frequência não tem modelo no caminho.

## Arquivos de propriedade exclusiva

```
web/src/app/telas/*.tsx   web/src/app/layout/*.tsx   web/src/app/telas/*.test.tsx
```

## Só leitura

`api/src/estoque/application/registry/componentes/**`

## Escopo

### Faz
- Rotas para a operação de alta frequência, sem passar pelo modelo:

| Rota | Componente registrado |
|---|---|
| `/recebimento/novo` | `recebimento_registrar` |
| `/quarentena` | `quarentena_fila` |
| `/quarentena/:loteId` | `quarentena_liberar` |
| `/saida` | `movimento_saida` |
| `/lotes` | `lote_lista` |
| `/lotes/:id` | `lote_detalhe` |
| `/vencimento` | `fila_vencimento` |

- Navegação lateral filtrada por permissão do ator.
- O assistente é **uma** superfície, acessível de qualquer tela, nunca a única.

### Não faz
Componentes novos. **Zero registro nesta tarefa** — se precisar de um componente
novo, o corte está errado.

## Critérios de aceite

- [ ] **AC-1** Cada rota renderiza o **mesmo** componente registrado usado pelo
      assistente. Teste afirma a identidade da referência. *(ADR-0005 — o critério
      central)*
- [ ] **AC-2** Nenhuma rota de operação chama o modelo. Teste com o adapter real
      espionado: **zero chamadas**. *(negativo — §11.5)*
- [ ] **AC-3** p95 de cada rota de operação ≤ 2 s. *(`RNF-04`)*
- [ ] **AC-4** Navegação lateral de Cleide não contém entrada para liberar
      quarentena. *(negativo — matriz)*
- [ ] **AC-5** Acessar `/quarentena/:id` diretamente como Cleide é recusado **no
      servidor**, não só escondido. *(negativo — `RN-A03`)*
- [ ] **AC-6** URL, botão voltar e recarregar funcionam em todas as rotas.
- [ ] **AC-7** Contagem de catálogo inalterada: **23**.

## Armadilhas

AC-1 é a prova de que o ADR-0005 se pagou. Se a tela com rota precisar de um
componente diferente do que o assistente usa, o desenho tem duplicação — e é
melhor descobrir agora do que no ciclo 2.
