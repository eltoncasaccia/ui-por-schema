# E2E Navigation Test Cases — Role: gerente

> Auto-gerado pela skill `e2e-nav-test`
> Framework: React 18 + TypeScript (Vite) · FastAPI (Python)
> Gerado: 2026-09-25
> Papel: gerente (persona-exemplo: Ivo Nakamura — CD Matriz e CD Refrigerado)

Testes de aceite de ponta a ponta, ordenados por dependência.

## Prerequisites

- **Subir o app**: `make up`
- **Base URL**: `http://localhost:5173`
- **Login**: botão de demonstração **"Ivo Nakamura"** (senha `demo`)
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

**Escopo de unidade é dado, não navegação** (`CA-06`): Ivo alcança
`cd-matriz` e `cd-refrigerado`; Odair só `filial-uberlandia`. As telas são as
mesmas — o que muda é o conteúdo dentro delas. T09 registra isso como
candidato, não como fluxo desta corrida.

---

## Dependency Tree

```
T01 Landing
 └─ T02 Login como Ivo (gerente)
     └─ T03 Workspace (/)
         ├─ T04 /lotes
         ├─ T05 /vencimento
         ├─ T06 /saida — separação com FEFO
         │   ├─ T07 Registrar saída do lote proposto (FEFO)
         │   └─ T08 (negativo) Trocar de lote sem justificativa
         ├─ T09 /recebimento/novo — leitor de código de barras
         │   └─ T10 Registrar recebimento completo
         ├─ T11 Descartar um movimento
         ├─ T12 Estornar um movimento
         └─ T13 Sair
     └─ T14 Acesso negado por URL — /quarentena/:loteId
     └─ T15 Acesso negado por URL — /controlados
     └─ T16 Acesso negado por URL — /usuarios
```

---

## Test Flows

### T01–T03

- [ ] Login como Ivo
- [ ] Abrir "Navegação" e verificar **exatamente** 4 itens: "Lotes",
      "Vencimento", "Saída", "Registrar recebimento"
- [ ] Verificar que "Liberar quarentena" e "Controlados" **não aparecem**

---

### T04: `/lotes` — T05: `/vencimento`

- [ ] Mesmos passos dos outros documentos, com a persona Ivo

---

### T06: `/saida` — separação com FEFO

**Dependencies**: T03
**Blocks**: T07, T08

- [ ] Clicar em "Saída" no menu
- [ ] Verificar o portão "Informe o id do produto para começar a separação."
- [ ] Preencher um id de produto com saldo disponível e clicar "Continuar"
- [ ] Verificar URL `/saida` com o formulário carregado: produto, lote
      proposto (destacado "FEFO"), alternativas com motivo de não serem a
      proposta

---

### T07: Registrar saída do lote proposto (FEFO)

**Dependencies**: T06

- [ ] Manter o lote proposto selecionado (sem trocar)
- [ ] Preencher quantidade e motivo
- [ ] Clicar "Registrar saída" (ou "Enviar para autorização", se o produto for
      controlado — não é o caso do lote proposto por padrão)
- [ ] Confirmar e verificar sucesso — saldo do lote refletido depois

---

### T08: *(negativo)* Trocar de lote sem justificativa

**Dependencies**: T06 (nova carga do formulário, mesmo produto)

- [ ] Selecionar uma alternativa diferente da proposta pelo FEFO
- [ ] Verificar que o campo de justificativa aparece, obrigatório
- [ ] Deixar a justificativa vazia ou curta (< 10 caracteres) e preencher o
      resto
- [ ] Verificar que o botão de envio continua desabilitado, com o texto
      "Separar lote diferente do proposto exige justificativa registrada"

---

### T09: `/recebimento/novo` — leitor de código de barras

**Dependencies**: T03
**Blocks**: T10

- [ ] Clicar em "Registrar recebimento" no menu
- [ ] Verificar URL `/recebimento/novo` e o campo "Código de barras do
      produto", com foco automático (fluxo de leitor, mão livre)
- [ ] Informar o EAN de um produto do seed
- [ ] Verificar que o produto é reconhecido e os campos de lote aparecem

---

### T10: Registrar recebimento completo

**Dependencies**: T09

- [ ] Preencher unidade de destino, nota fiscal, fornecedor
- [ ] Preencher lote, fabricação, validade e quantidade física
- [ ] Se o produto for termolábil, preencher temperatura de chegada
- [ ] Confirmar o recebimento
- [ ] Verificar o lote criado, visível em `/lotes`

---

### T11: Descartar um movimento — T12: Estornar um movimento

**Dependencies**: T03

- [ ] Mesmos passos do documento do RT (T13/T14), com a persona Ivo

---

### T13: Sair

**Dependencies**: T03

- [ ] Mesmos passos dos outros documentos

---

### Access Denial Tests

### T14: Acesso negado por URL — `/quarentena/:loteId`

**Dependencies**: T02

- [ ] Obter um `lote_id` em quarentena via API
- [ ] Navegar para `/quarentena/<lote_id>`; verificar "Sem acesso a este
      componente." (Ivo não tem `lote.liberar`)

### T15: Acesso negado por URL — `/controlados`

**Dependencies**: T02

- [ ] Navegar direto; verificar "Sem acesso a este componente."

### T16: Acesso negado por URL — `/usuarios`

**Dependencies**: T02

- [ ] Navegar para `/usuarios`; verificar recusa

---

## Não faz

Mesmo recorte dos demais documentos — sem assistente com modelo real, sem
exportação/paginação, sem Firefox/WebKit/layout estreito, sem o escopo de
unidade (Ivo × Odair) que é dado, não navegação.

---

## Observations

Execução não realizada nesta corrida, por decisão explícita.

### Summary

- Total: 16
- Executados: 0
