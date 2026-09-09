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
api/src/estoque/application/registry/componentes/controlado_autorizar.py
api/tests/registry/test_controlado_autorizar.py

api/src/estoque/application/commands/autorizacao.py
api/src/estoque/application/commands/entradas/autorizacao.py
api/tests/commands/test_autorizacao_comandos.py
```

> **Corrigido pelo achado A-15.** Os arquivos em `commands/` não estavam na lista
> original, e sem eles a tarefa não fecha: o componente **declara** o comando, mas
> não pode **executá-lo** — `registry` não importa `commands.pipeline`, porque o
> contrato 2 do import-linter proíbe `registry → sqlalchemy`, inclusive por
> caminho indireto.
>
> `commands/entradas/<dominio>.py` guarda o schema de entrada, e é módulo-folha:
> só pydantic e `domain`. O `CommandDef` do registry e o comando executável
> apontam para **o mesmo schema** — duas declarações do mesmo formulário
> divergiriam (achado A-11). Há teste percorrendo o grafo em
> `tests/registry/test_quarentena_liberar.py` que reprova a folha que deixar de
> ser folha.
>
> **`commands/indice.py` é GERADO** por `make gerar-indice` e não entra em lista
> nenhuma: as cinco tarefas de escrita precisariam da mesma linha nele, que é
> exatamente o caso do acordo de trabalho §4. Rode o gerador; não edite à mão.
>
> `T-027` é o exemplo pronto: `commands/lote.py` + `commands/entradas/lote.py`.

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

> **Endpoints corrigidos pelo achado A-16.** A tarefa citava rotas REST por
> recurso; [CONTRATOS §8](./CONTRATOS.md) — normativo e congelado — define
> `/api/comandos/{nome}` como a rota **única** de escrita, com CSRF, `Origin`,
> `Idempotency-Key` e `If-Match` aplicados num lugar só. A hierarquia do acordo
> de trabalho resolve: **`RN-*` > ADR > PRD > tarefa.**

- Command `controlado_autorizar` — `POST /api/comandos/controlado_autorizar`,
  `requires: 'controlado.autorizar'`, **não idempotente**.
- Autorizar ou recusar, com motivo.
- Efetivação atômica: movimento passa a `efetivado` e o saldo muda **no mesmo
  instante**.
- ~~Ajuste de controlado exige motivo e documento anexo (`RN-C02`)~~ — o fluxo de
  ajuste está fora do ciclo 1 (ADR-0010). Ver "Não faz".
- Livro de registro eletrônico **imutável** (`RN-C05`), pelo `GRANT` por coluna e
  pelo gatilho da migração 0004. **Exportável fica para depois** — achado A-23.

### Não faz
Divergência de controlado escalando para RT e Diretor (`RN-C04`) — depende de
contagem, fora do ciclo 1 (ADR-0010). **E, pelo mesmo motivo, `RN-C02`**: ajuste
de saldo também foi cortado pelo ADR-0010, e o AC-6 pedia uma recusa num fluxo
que não existe (achado A-22).

### Decidido na execução

**A migração 0004 existe porque duas regras estavam em tensão.** `RN-M02` diz que
movimento é imutável, e a migração 0001 aplicou isso com `REVOKE UPDATE, DELETE ON
movimento` — o que torna `RN-C01` impossível: conferido no banco, a aplicação
recebia `permission denied` ao tentar efetivar o pendente. A resolução não foi
devolver o UPDATE, e sim:

1. `GRANT UPDATE (status, autorizador_id)` — **por coluna**. Mexer em quantidade,
   lote, autor ou data continua sendo recusado pelo mesmo `permission denied`.
2. Um **gatilho** que só deixa passar `aguardando_autorizacao → efetivado|recusado`,
   com todas as outras colunas conferidas inalteradas e `autorizador_id` presente.
   Sem ele, o GRANT por coluna permitiria virar um `efetivado` em `recusado` — e
   apagar o efeito de um movimento é reescrever história com outro nome.

O que `RN-M02` protege continua protegido: ninguém muda o que aconteceu.

**Sem `movimento_id`, o componente mostra a fila.** A descoberta pelo
`movimento_lista` é T-024 e não existe; um formulário que só funciona com um id
que ninguém consegue obter seria entrega pela metade. Não é componente novo — o
catálogo continua com +1.

## Critérios de aceite

- [x] **AC-1** Movimento de controlado pendente **não altera o saldo**. Teste
      compara o saldo antes e depois da submissão. *(`CA-04`, `AC-06.1`)*
- [x] **AC-2** Após autorização, o movimento grava `autorId` **e** `autorizadorId`,
      distintos. *(`RN-C01`)*
- [x] **AC-3** A mesma pessoa submetendo e autorizando é recusada — no servidor,
      mesmo com requisição forjada. *(negativo — `RN-A04`, o critério central)*
- [x] **AC-4** Apenas Helena tem `controlado.autorizar`. Nem Marco consegue.
      *(negativo — matriz)*
- [x] **AC-5** Movimento recusado não altera saldo e fica registrado como
      `recusado`, com motivo. *(`RN-M02` — nada é apagado)*
- [ ] **AC-6** ~~Ajuste de controlado sem documento anexo é recusado~~ *(`RN-C02`)*
      — **fora do ciclo 1, e o critério estava errado.** `RN-C02` fala de
      **ajuste de saldo**, e o [ADR-0010](../adr/0010-corte-de-escopo-ciclo-1.md)
      cortou contagem, inventário, **ajuste** e transferência. Não existe fluxo de
      ajuste para recusar. A própria seção "Não faz" desta tarefa já excluía
      `RN-C04` pelo mesmo motivo e esqueceu este. Achado A-22 — fica em branco.
- [~] **AC-7** O livro de controlados exporta e não permite alteração
      *(`RN-C05`)* — **metade verificada.**
      *Não permite alteração:* provado, e em duas camadas — `GRANT` por coluna e
      gatilho (`test_a_autorizacao_nao_abriu_a_porta_para_editar_o_movimento`,
      `test_ac5_o_gatilho_do_banco_recusa_desfazer_um_efetivado`).
      *Exporta:* **não entregue.** Exportação não tem componente, comando nem
      endpoint em lugar nenhum do ciclo 1, e criar um aqui seria +1 no catálogo
      sem tarefa que o preveja. Achado A-23.
- [x] **AC-8** Nenhum caminho a partir do assistente conclui a autorização — só o
      submit humano. *(negativo — ADR-0002)*

## Definição de pronto — adicional
- [x] Contagem de catálogo no BOARD: **+1**. Registrados hoje: **11**. O
      acumulado de 23 depende das tarefas que faltam — não fecha aqui.
- [x] Teste de teto `RNF-08` verde (11 de 25).

## Armadilhas

AC-3 tem que ser testado com **requisição direta**, não pela interface. A interface
esconderá o botão; o servidor é quem precisa recusar.
