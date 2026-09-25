# E2E Navigation Test Cases — Role: conferente

> Auto-gerado pela skill `e2e-nav-test`
> Framework: React 18 + TypeScript (Vite) · FastAPI (Python)
> Gerado: 2026-09-25
> Papel: conferente (persona-exemplo: Cleide Ramos)

Testes de aceite de ponta a ponta, ordenados por dependência.

## Prerequisites

- **Subir o app**: `make up`
- **Base URL**: `http://localhost:5173`
- **Login**: botão de demonstração **"Cleide Ramos"** (senha `demo`)
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

**Cleide tem o mesmo menu que o gerente** (`/lotes`, `/vencimento`, `/saida`,
`/recebimento/novo`), mas **não** tem descarte/estorno de movimento nem
`custo.ler` — a diferença aparece dentro das telas, não no menu.

---

## Dependency Tree

```
T01 Landing
 └─ T02 Login como Cleide (conferente)
     └─ T03 Workspace (/)
         ├─ T04 /lotes — sem coluna de custo
         ├─ T05 /vencimento
         ├─ T06 /saida — separação com FEFO
         │   └─ T07 Registrar saída
         ├─ T08 /recebimento/novo
         │   └─ T09 Registrar recebimento
         └─ T10 Sair
     └─ T11 Menu não tem "Liberar quarentena" (negativo, matriz)
     └─ T12 Acesso negado por URL — /quarentena/:loteId, forjando o comando
     └─ T13 Acesso negado por URL — /controlados
     └─ T14 Acesso negado por URL — /usuarios
```

T11 é o par positivo/negativo mais direto do projeto: Helena vê "Liberar
quarentena", Cleide não — mesmo catálogo por ator, personas diferentes.

---

## Test Flows

### T01–T03

- [ ] Login como Cleide
- [ ] Abrir "Navegação" e verificar 4 itens: "Lotes", "Vencimento", "Saída",
      "Registrar recebimento" — igual ao gerente

---

### T04: `/lotes` — sem coluna de custo

**Dependencies**: T03

- [ ] Clicar em "Lotes"
- [ ] Verificar a tabela carregada
- [ ] Verificar que **nenhuma coluna de custo** aparece (Cleide não tem
      `custo.ler` — `CA-05`)

### T05: `/vencimento`

**Dependencies**: T03

- [ ] Mesmos passos dos outros documentos

---

### T06: `/saida` — T07: Registrar saída

**Dependencies**: T03

- [ ] Mesmos passos do documento do gerente (T06/T07), com a persona Cleide

### T08: `/recebimento/novo` — T09: Registrar recebimento

**Dependencies**: T03

- [ ] Mesmos passos do documento do gerente (T09/T10), com a persona Cleide

---

### T10: Sair

**Dependencies**: T03

- [ ] Mesmos passos dos outros documentos

---

### Access Denial Tests

### T11: *(negativo, matriz)* Menu não tem "Liberar quarentena"

**Dependencies**: T03

- [ ] Abrir "Navegação"
- [ ] Verificar "Lotes" visível (controle: o menu carregou, o catálogo chegou)
- [ ] Verificar "Liberar quarentena" **ausente** — não desabilitado, ausente

### T12: Acesso negado por URL — `/quarentena/:loteId`, forjando o comando

**Dependencies**: T02

- [ ] Obter (por outra sessão, ex. Helena) o `lote_id` de um item na fila de
      quarentena
- [ ] Como Cleide, navegar para `/quarentena/<lote_id>`
- [ ] Verificar "Sem acesso a este componente."; nenhum botão de liberar, nem
      desabilitado; o número do lote não aparece na tela
- [ ] *(mais forte, candidato)* Forjar `POST /api/comandos/lote_liberar_quarentena`
      com o CSRF válido da própria sessão de Cleide — verificar `403
      nao_autorizado`, e que o lote continua na fila de quem pode vê-la

### T13: Acesso negado por URL — `/controlados`

**Dependencies**: T02

- [ ] Navegar direto; verificar "Sem acesso a este componente."

### T14: Acesso negado por URL — `/usuarios`

**Dependencies**: T02

- [ ] Navegar para `/usuarios`; verificar recusa

---

## Não faz

Mesmo recorte dos demais documentos.

---

## Observations

Execução não realizada nesta corrida, por decisão explícita.

### Summary

- Total: 14
- Executados: 0
