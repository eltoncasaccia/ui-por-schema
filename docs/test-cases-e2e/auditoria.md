# E2E Navigation Test Cases — Role: auditoria

> Auto-gerado pela skill `e2e-nav-test`
> Framework: React 18 + TypeScript (Vite) · FastAPI (Python)
> Gerado: 2026-09-25
> Papel: auditoria (persona-exemplo: Sandra Alves)

Testes de aceite de ponta a ponta, ordenados por dependência.

## Prerequisites

- **Subir o app**: `make up`
- **Base URL**: `http://localhost:5173`
- **Login**: botão de demonstração **"Sandra Alves"** (senha `demo`)
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

**Sandra lê mais do que qualquer papel sem escrita**: movimento, recebimento,
temperatura, trilha de auditoria e custo — mas nenhuma das 4 rotas de escrita
está no menu dela (mesma cobertura de nav que o diretor).

---

## Dependency Tree

```
T01 Landing
 └─ T02 Login como Sandra (auditoria)
     └─ T03 Workspace (/)
         ├─ T04 /lotes — COM coluna de custo
         ├─ T05 /vencimento
         ├─ T06 Trilha de auditoria — filtros
         ├─ T07 Rastreabilidade (auditoria.rastrear)
         ├─ T08 Movimentos, recebimentos e temperatura (leitura ampla)
         └─ T09 Sair
     └─ T10 Acesso negado por URL — /quarentena/:loteId
     └─ T11 Acesso negado por URL — /saida
     └─ T12 Acesso negado por URL — /controlados
     └─ T13 Acesso negado por URL — /recebimento/novo
     └─ T14 Acesso negado por URL — /usuarios
```

---

## Test Flows

### T01–T03

- [ ] Login como Sandra
- [ ] Abrir "Navegação" e verificar **exatamente** 2 itens: "Lotes",
      "Vencimento" — igual ao diretor, apesar do catálogo de leitura ser bem
      mais largo

---

### T04: `/lotes` — COM coluna de custo

**Dependencies**: T03

- [ ] Verificar a tabela com a coluna de custo visível (Sandra tem
      `custo.ler`)

### T05: `/vencimento`

**Dependencies**: T03

- [ ] Mesmos passos dos outros documentos

---

### T06: Trilha de auditoria — filtros

**Dependencies**: T03

- [ ] Abrir `auditoria_trilha`
- [ ] Filtrar por entidade (`lote`, `movimento`, `comando`, `recebimento`,
      `usuario`) e por período (7/30/90/365/tudo)
- [ ] Verificar que a contagem muda com o filtro
- [ ] Verificar que **nenhum** campo de custo aparece em `valor_anterior` /
      `valor_novo`, mesmo Sandra tendo `custo.ler` — o filtro é regra da
      leitura, para todo mundo (`_sem_custo`)

### T07: Rastreabilidade (`auditoria.rastrear`)

**Dependencies**: T03

- [ ] Abrir o componente de rastreabilidade para um lote ou produto
- [ ] Verificar a cadeia de eventos ligados

### T08: Movimentos, recebimentos e temperatura (leitura ampla)

**Dependencies**: T03

- [ ] Compor `movimento_lista`, `recebimento_lista` e
      `temperatura_historico`/`temperatura_excursoes` (pelo assistente ou por
      um lote/unidade específico)
- [ ] Verificar que os três carregam — nenhum outro papel de leitura alcança
      os três ao mesmo tempo sem também ter escrita

### T09: Sair

**Dependencies**: T03

- [ ] Mesmos passos dos outros documentos

---

### Access Denial Tests

### T10–T14: Acesso negado por URL

**Dependencies**: T02

- [ ] `/quarentena/<lote_id>` → "Sem acesso a este componente."
- [ ] `/saida` → portão aparece; ao submeter produto, "Sem acesso a este
      componente."
- [ ] `/controlados` → "Sem acesso a este componente."
- [ ] `/recebimento/novo` → "Sem acesso a este componente."
- [ ] `/usuarios` → recusa (Sandra tem `usuario.ler`, não `usuario.gerenciar`)

---

## Não faz

Mesmo recorte dos demais documentos.

---

## Observations

Execução não realizada nesta corrida, por decisão explícita.

### Summary

- Total: 14
- Executados: 0
