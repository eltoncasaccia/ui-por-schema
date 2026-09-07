# T-030 — Dupla identificação de controlado · `CA-04`

| | |
|---|---|
| **Onda** | W4 |
| **Trilha** | B |
| **Tamanho** | **G** |
| **Depende de** | T-028, T-024 |
| **Bloqueia** | T-033 |
| **Componentes** | `controlado_autorizar` |
| **ADRs** | [0002](../adr/0002-plano-render-plano-escrita.md), [0011](../adr/0011-teto-de-catalogo.md) |
| **Regras** | RN-C01, RN-C02, RN-C04, RN-C05, RN-A04, RN-I01 |
| **Requisitos** | RF-09 · `US-06` · `CA-04` |

## Objetivo

O único fluxo de duas pessoas do ciclo 1, e o **teste mais afiado do ADR-0002**:
nenhuma saída de modelo conclui a operação; duas identidades humanas são exigidas.

## O fluxo

```
Cleide submete saída de controlado          (T-028)
  → movimento em `aguardando_autorizacao`
  → saldo NÃO muda
  → Helena encontra em movimento_lista(status: aguardando_autorizacao)   (T-024)
  → Helena autoriza em controlado_autorizar                              (esta tarefa)
  → servidor efetiva, com as DUAS identidades gravadas
```

Nenhum componente novo para a fila: `status` já é enum de `movimento_lista`. Foi
assim que o catálogo coube em 23 (ADR-0011).

## Arquivos de propriedade exclusiva

**Lado servidor** — params, `requires`, `description`, `load`, `select`, viewmodel:

```
api/src/estoque/registry/componentes/controlado_autorizar.py
api/tests/registry/test_controlado_autorizar.py
```

**Lado cliente** — apenas o React que recebe o viewmodel:

```
web/src/views/controlado_autorizar.tsx
```

> Esta tarefa atravessa os dois lados por causa do
> [ADR-0017](../adr/0017-registry-servidor-views-cliente.md). O teste de bijeção
> exige que os 1 id tenham registro **e** view — entregar só um lado
> quebra o CI.

## Escopo

### Faz
- Command `POST /movimentos/:id/autorizacao`, `requires: 'controlado.autorizar'`.
- Autorizar ou recusar, com motivo.
- Efetivação atômica: movimento passa a `efetivado` e o saldo muda **no mesmo
  instante**.
- Ajuste de controlado exige motivo **e documento anexo** (`RN-C02`).
- Livro de registro eletrônico exportável e imutável (`RN-C05`).

### Não faz
Divergência de controlado escalando para RT e Diretor (`RN-C04`) — depende de
contagem, fora do ciclo 1 (ADR-0010).

## Critérios de aceite

- [ ] **AC-1** Movimento de controlado pendente **não altera o saldo**. Teste
      compara o saldo antes e depois da submissão. *(`CA-04`, `AC-06.1`)*
- [ ] **AC-2** Após autorização, o movimento grava `autorId` **e** `autorizadorId`,
      distintos. *(`RN-C01`)*
- [ ] **AC-3** A mesma pessoa submetendo e autorizando é recusada — no servidor,
      mesmo com requisição forjada. *(negativo — `RN-A04`, o critério central)*
- [ ] **AC-4** Apenas Helena tem `controlado.autorizar`. Nem Marco consegue.
      *(negativo — matriz)*
- [ ] **AC-5** Movimento recusado não altera saldo e fica registrado como
      `recusado`, com motivo. *(`RN-M02` — nada é apagado)*
- [ ] **AC-6** Ajuste de controlado sem documento anexo é recusado. *(negativo —
      `RN-C02`)*
- [ ] **AC-7** O livro de controlados exporta e não permite alteração. *(negativo —
      `RN-C05`)*
- [ ] **AC-8** Nenhum caminho a partir do assistente conclui a autorização — só o
      submit humano. *(negativo — ADR-0002)*

## Definição de pronto — adicional
- [ ] Contagem de catálogo no BOARD: **+1** — **acumulado fecha em 23**.
- [ ] Teste de teto `RNF-08` verde com 23.

## Armadilhas

AC-3 tem que ser testado com **requisição direta**, não pela interface. A interface
esconderá o botão; o servidor é quem precisa recusar.
