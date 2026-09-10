---
name: executar-tarefa
description: Executa uma tarefa T-0NN do board deste projeto, do começo ao commit. Use ao assumir qualquer tarefa de docs/tasks/, ao retomar uma tarefa parcial, ou quando o usuário disser "faça a T-018", "próxima tarefa", "continue a tarefa". Cobre o protocolo de leitura, propriedade exclusiva de arquivo, Definition of Done, e a atualização de BOARD e PROGRESSO no mesmo commit.
---

# Executar uma tarefa

O laço completo do [acordo de trabalho](../../../docs/tasks/README.md). Siga na
ordem; cada passo existe porque a falta dele já custou caro aqui.

---

## 1. Definition of Ready — antes de começar

Confira, na ordem:

- [ ] `docs/tasks/PROGRESSO.md` diz que as dependências desta tarefa estão `✅`
- [ ] os contratos que ela consome estão congelados (`docs/tasks/CONTRATOS.md`)
- [ ] a lista de propriedade exclusiva não intersecta nenhuma tarefa em andamento
- [ ] os critérios de aceite são verificáveis por teste, não por opinião

Se a tarefa está `🟡 parcial`, **descubra o que já existe antes de escrever**:
`PROGRESSO.md` tem uma coluna "o que falta" por tarefa. Confie nela como pista,
não como verdade — confirme no código.

## 2. Protocolo de leitura — e nada além disto

1. `docs/tasks/T-0NN-*.md`
2. `docs/tasks/CONTRATOS.md`
3. **só** os ADRs que a tarefa citar
4. **só** as regras `RN-*` citadas: `make rn RN-L05 RN-R02` — o script
   imprime a regra com a seção dela e a legenda de `[R]`/`[S]`/`[C]`.
   Abrir `docs/02-regras-de-negocio.md` inteiro lê 59 regras para usar duas.

Não leia o PRD inteiro nem os quatro documentos narrativos. Se a tarefa não puder
ser executada com essa leitura, **a tarefa está mal escrita** — corrija a tarefa.

Depois, leia o `CLAUDE.md` do subprojeto que você vai tocar (`api/` ou `web/`).

## 2b. Modelo — o padrão do projeto é Sonnet

`.claude/settings.json` fixa **Sonnet** neste repositório: tarefa de componente
(W3) é repetição de um padrão que a skill `componente-novo` já descreve, e
Sonnet a executa igual por uma fração do orçamento de sessão.

**Suba para Opus com `/model opus`** quando a tarefa decidir quem pode o quê:

| Sobe para Opus | Fica em Sonnet |
|---|---|
| tarefa de **escrita** (W4) — pipeline, comando, autorização | componente de leitura (W3) |
| segurança (T-033, T-040) e teste negativo de autorização | view React, viewmodel |
| as duas skills de auditoria | correção de bug, teste que faltou |

## 3. Ambiente

```bash
make db-local && make migrate     # e db-local DE NOVO: migrate derruba a porta
make env                          # o .env está completo?
```

Sem o Postgres publicado, nove testes de imutabilidade **pulam** — e teste que
pula é teste que não existe.

## 4. Implementar

**Propriedade exclusiva:** escreva **só** nos arquivos que a tarefa declara.
Precisou escrever em arquivo de outra tarefa? **Pare e sinalize.** Não é exceção
justificável; é sinal de que o corte de tarefas está errado.

**Nunca edite arquivo gerado:**
`api/src/estoque/application/registry/indice.py`, `web/src/views/indice.ts`,
`web/src/generated/*`. Rode `make gerar-indice` e `make types`.

**Imite o que já existe.** Achado o arquivo mais parecido com o que você vai
escrever, siga o estilo, a densidade de comentário e o idioma dele.

**Pergunte antes** ([ADR-0028](../../../docs/adr/0028-processo-de-decisao.md))
se for acrescentar dependência ou container, mudar contrato congelado, ou
escolher entre caminhos com custo/risco distintos. Uma linha, **com a
recomendação** — pergunta sem recomendação empurra o trabalho de volta.

## 5. Testar — o negativo é o que vale

Para cada critério de aceite, um teste que o exercita. Para cada mecanismo de
proteção, **dois**:

1. prova que funciona quando deveria funcionar;
2. **prova que falha quando deveria falhar** ← este.

*Testar que Helena consegue liberar quarentena prova pouco. Testar que Ivo
**não** consegue, nem por requisição forjada, é o que prova a arquitetura.*

Se a tarefa toca escrita, o teste de autorização negativa é **obrigatório** no
DoD: um papel que não pode, tentando, e sendo recusado no servidor.

Detalhes por linguagem: skills `testes-python` (em `api/`) e `testes-web` (em
`web/`).

## 6. Definition of Done

```bash
make check-api   # ou check-web — rode SÓ o lado que você tocou, a cada iteração
make check       # os dois + a bijeção — UMA vez, no fim, antes do commit
```

Rodar `make check` inteiro a cada iteração paga `tsc`, `eslint` e `vitest` num
laço de correção de Python, e a saída dos três não ajuda a consertar um pytest.

E mais, item a item:

- [ ] cada AC tem um teste ou verificação que **você executou**
- [ ] nenhum arquivo fora da propriedade exclusiva foi modificado
- [ ] se registrou componente: entrou no teste de orçamento de catálogo
      (`RNF-08`) e no de catálogo por persona (ADR-0003)
- [ ] se tocou escrita: existe teste de autorização **negativa**

## 7. Fechar — as três coisas no MESMO commit

1. marcar no arquivo da tarefa os `- [ ]` que foram **de fato verificados**
2. mudar a linha no `docs/tasks/BOARD.md` **e** no `docs/tasks/PROGRESSO.md`
3. se o escopo mudou, revisar o PRD

> **Critério de aceite não conferido fica em branco.** Marcar por otimismo é
> pior que deixar vazio: cria evidência falsa, e evidência falsa só é descoberta
> quando alguém confia nela. Foi assim que o CSRF ficou prometido em três
> documentos e implementado em nenhum
> ([A-002](../../../docs/relatorios/A-002-auditoria-de-execucao.md)).

**Mensagem de commit:** `T-0NN: <o que mudou>`. Explique **por quê**, cite os ACs
que passaram a valer, e registre o que você **não** fez e por quê. Um commit que
só lista arquivos alterados não ajuda ninguém em seis meses.

## 8. Quando parar e sinalizar

Não improvise. Pare se:

- precisa mudar contrato congelado
- precisa escrever em arquivo de outra tarefa
- um critério de aceite é ambíguo ou não verificável
- duas regras `RN-*` se contradizem
- uma decisão de negócio não está em documento nenhum

Os dois últimos viram **achado**, registrado em `docs/tasks/ACHADOS.md`. Achado que
muda regra vira pergunta ao cliente; achado que muda decisão técnica vira ADR.

**Achado que muda regra vai para a seção 0 do BOARD**, não só para o ACHADOS:
decisão do cliente enterrada numa tabela longa é decisão que ninguém vê, e
registrado-e-invisível é o mesmo que não registrado.

**Fechou um achado? Tire-o do ACHADOS** e mova o texto para
`docs/relatorios/achados-resolvidos.md`, deixando só o id citável. Não fazer isso
é o que transformou o arquivo no maior dos documentos de tarefa — 56% dele
descrevia problemas que não existiam mais, e todo fechamento passava por cima.

**Nenhum desses casos se resolve com uma suposição registrada em comentário de
código.** É assim que documentação e sistema divergem.
