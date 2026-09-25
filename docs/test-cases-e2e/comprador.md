# E2E Navigation Test Cases — Role: comprador

> Auto-gerado pela skill `e2e-nav-test`
> Framework: React 18 + TypeScript (Vite) · FastAPI (Python)
> Gerado: 2026-09-25
> Papel: comprador (persona-exemplo: Rafael Lima)

Testes de aceite de ponta a ponta, ordenados por dependência.

## Prerequisites

- **Subir o app**: `make up`
- **Base URL**: `http://localhost:5173`
- **Login**: botão de demonstração **"Rafael Lima"** (senha `demo`)
- **Screenshots on failure**: `screenshots/` ao lado deste documento
- **Browser mode**: headless

## Detected Stack

Igual aos demais documentos deste conjunto — ver `diretor.md`.

## Role Matrix

| Rota / recurso | diretor | rt | gerente | conferente | comprador | auditoria |
|---|---|---|---|---|---|---|
| `/lotes` (lote_lista) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/vencimento` (fila_vencimento) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/quarentena` (fila + liberar) | – | ✓ | – | – | – | – |
| `/controlados` (controlado_autorizar) | – | ✓ | – | – | – | – |
| `/saida` (movimento_saida) | – | – | ✓ | ✓ | – | – |
| `/recebimento/novo` (recebimento_registrar) | – | – | ✓ | ✓ | – | – |
| `/usuarios` (fora do catálogo) | ✓ | – | – | – | – | – |
| Ver custo (`custo.ler`) | ✓ | – | – | – | ✓ | ✓ |
| Trilha de auditoria (`auditoria.ler`) | ✓ | ✓ | – | – | – | ✓ |
| Movimentos, recebimentos, temperatura (leitura) | ✓ | ✓ | ✓ | ✓ | – | ✓ |
| Descarte / estorno de movimento | ✓ | ✓ | ✓ | – | – | – |
| Bloquear/desbloquear lote (`lote.status`) | – | ✓ | – | – | – | – |

**O comprador é o papel mais estreito do sistema**: só `produto.ler`,
`lote.ler` e `custo.ler`. Sem `movimento.ler` nem `recebimento.ler` — não vê
nem histórico de movimento, nem recebimento, o que nenhum outro papel de
leitura perde.

---

## Dependency Tree

```
T01 Landing
 └─ T02 Login como Rafael (comprador)
     └─ T03 Workspace (/)
         ├─ T04 /lotes — COM coluna de custo
         ├─ T05 /vencimento
         ├─ T06 Ver custo num indicador
         └─ T07 Sair
     └─ T08 Menu tem só 2 dos 6 itens (negativo, matriz)
     └─ T09 Acesso negado por URL — /quarentena/:loteId
     └─ T10 Acesso negado por URL — /saida
     └─ T11 Acesso negado por URL — /controlados
     └─ T12 Acesso negado por URL — /recebimento/novo
```

---

## Test Flows

### T01–T03

- [ ] Login como Rafael
- [ ] Abrir "Navegação" e verificar **exatamente** 2 itens: "Lotes",
      "Vencimento"

---

### T04: `/lotes` — COM coluna de custo

**Dependencies**: T03

- [ ] Clicar em "Lotes"
- [ ] Verificar a tabela carregada
- [ ] Verificar que a coluna/campo de custo **aparece** — Rafael tem
      `custo.ler`, diferente de gerente e conferente

### T05: `/vencimento`

**Dependencies**: T03

- [ ] Mesmos passos dos outros documentos

### T06: Ver custo num indicador

**Dependencies**: T03

- [ ] Compor um `estoque_indicador` com `metrica=valor_em_estoque`
- [ ] Verificar o valor em reais visível

### T07: Sair

**Dependencies**: T03

- [ ] Mesmos passos dos outros documentos

---

### Access Denial Tests

### T08: *(negativo, matriz)* Menu tem só 2 dos 6 itens

**Dependencies**: T03

- [ ] Verificar "Liberar quarentena", "Controlados", "Saída" e "Registrar
      recebimento" **ausentes** do menu

### T09–T12: Acesso negado por URL

**Dependencies**: T02

- [ ] `/quarentena/<lote_id>` → "Sem acesso a este componente."
- [ ] `/saida` → portão aparece; ao submeter produto, "Sem acesso a este
      componente."
- [ ] `/controlados` → "Sem acesso a este componente."
- [ ] `/recebimento/novo` → "Sem acesso a este componente."

---

## Não faz

Mesmo recorte dos demais documentos.

---

## Observations

Execução não realizada nesta corrida, por decisão explícita.

### Summary

- Total: 12
- Executados: 0
