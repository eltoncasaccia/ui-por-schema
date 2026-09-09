---
name: auditar-execucao
description: Audita se a documentação diz a verdade sobre o código — board e PROGRESSO contra a realidade, promessas de ADR contra implementação, critérios de aceite marcados contra testes que existem. Use antes de fechar uma onda, antes de um relatório de fechamento, ao retomar o projeto depois de um intervalo, ou quando desconfiar de que documento e código andaram separados. Produz um relatório A-0NN em docs/relatorios/.
---

# Auditar a execução

Esta skill existe por causa de uma falha concreta. As 39 tarefas nasceram com
status `⬜` e nunca foram atualizadas: o board dizia que nada tinha sido feito
enquanto 19 tarefas estavam prontas. E foi nessa fresta que o **CSRF ficou
prometido em três documentos e implementado em nenhum** —
[A-002](../../../docs/relatorios/A-002-auditoria-de-execucao.md).

A pergunta desta auditoria é uma só: **onde o que está escrito deixou de
corresponder ao que está no código?**

---

## Regra de ouro

**Nunca acredite no documento. Vá ao código.** Se um documento diz que algo está
feito, encontre a linha que faz, e o teste que prova. Se não encontrar em dois
minutos, é achado — não é "deve estar em algum lugar".

Auditoria é trabalho de leitura, não de execução. **Não conserte nada durante a
auditoria**: consertar embaralha o que era estado e o que virou correção.
Registre, e conserte depois, em tarefa própria.

---

## Passo 1 — a linha de base é honesta?

```bash
make check
```

Se algum alvo falha, **isso já é o primeiro achado** e muda o peso de tudo o
mais: um `make check` vermelho significa que ninguém rodou o DoD por completo.

Confira também o que **pula**:

```bash
cd api && uv run pytest -q -rs        # -rs mostra os skips e a razão
```

Teste que pula é teste que não existe. Nove testes de banco pulam sem Postgres.

## Passo 2 — o board diz a verdade?

Para **cada** tarefa marcada `✅` em `docs/tasks/PROGRESSO.md`:

1. abra `docs/tasks/T-0NN-*.md` e leia os critérios de aceite marcados `[x]`
2. para cada um, **encontre o teste**. Nome do arquivo, nome da função
3. rode esse teste e veja passar
4. se não existe teste, pergunte: existe *alguma* verificação executada? Se a
   resposta for "deve funcionar", **o AC está marcado por otimismo** → achado

Faça o mesmo, ao contrário, para as `⬜`: existe código implementando uma tarefa
que o board diz não iniciada? Também é achado — status defasado nos dois sentidos
faz o mesmo estrago.

## Passo 3 — promessa de ADR tem código?

Percorra `docs/adr/*.md`. Cada ADR tem (ou deveria ter) uma seção de como é
verificado em código. Para cada um:

- a decisão está implementada? **onde?**
- existe teste que falharia se alguém a violasse?
- há ADR marcado "Aceito" cujo código nunca executou?

> Este é o padrão mais perigoso do projeto, e já apareceu duas vezes: **escrito,
> tipado, compilado e nunca executado.** A POC v1 publicou números de um parser
> simulado; o observador do LangFuse tinha três defeitos que só a primeira
> execução real revelou. Compilar não é evidência.

Marque como achado todo caminho de código que nunca rodou de verdade.

## Passo 4 — os invariantes estruturais

```bash
python3 scripts/gerar_indice.py --conferir   # índices em dia?
cd api && uv run lint-imports                # contratos de camada
cd web && npx tsx scripts/arch-check.ts      # regras do lado TS
cd web && npx vitest run src/testes/bijecao.test.ts
```

E na mão:

- **contagem de catálogo** no BOARD §5 bate com `len(todos())` do registry?
- todo componente registrado tem view, e vice-versa?
- `.env.example` e `.env` divergem? (`make env`) — variável ausente cai num
  padrão que funciona, e é por funcionar que passa despercebida
- `pyproject.toml` e `package.json` pinam versões compatíveis com o código que
  de fato usa a API delas?

## Passo 5 — rastreabilidade

`docs/RASTREABILIDADE.md` liga `RN` → `CA` → tarefa → teste. Amostre cinco
linhas e siga a corrente inteira. Uma corrente que se rompe é achado.

Confira também os critérios de aceite do cliente (`CA-01` a `CA-08`) e os
requisitos de segurança (`CS-01` a `CS-06`) no `PROGRESSO.md`: o estado ali
declarado se sustenta?

---

## O relatório

Escreva em `docs/relatorios/A-0NN-<assunto>.md`, seguindo o formato do
[A-002](../../../docs/relatorios/A-002-auditoria-de-execucao.md):

1. **Resumo em uma tabela:** antes / depois, com números
2. **Os achados, numerados `A-NN`**, cada um com:
   - o que está escrito, e onde
   - o que está no código, e onde
   - a consequência prática — *quem se machuca, e como*
   - severidade: **ALTA** (promessa de segurança não cumprida, número publicado
     sem base) · **média** (processo, cobertura) · **baixa** (documental)
   - a tarefa que fecha o achado
3. **Estado real apurado**, para substituir o `PROGRESSO.md`
4. **O que NÃO foi auditado**, e por quê ← seção obrigatória

Registre os achados também em `docs/tasks/ACHADOS.md`, e abra as tarefas que os
fecham. Classificação: muda regra → pergunta ao cliente; muda decisão técnica →
ADR; muda escopo → revisão do PRD.

**Se a auditoria não encontrou nada, desconfie dela mesma** e diga no relatório o
que você olhou. Auditoria sem achado costuma ser auditoria que leu o documento em
vez do código.
