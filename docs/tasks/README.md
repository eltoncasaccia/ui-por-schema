# Acordo de Trabalho — como este projeto é executado

Este documento existe para uma finalidade específica: **permitir que várias
sessões trabalhem ao mesmo tempo, no mesmo repositório, sem conflito e sem
retrabalho.**

Vale para sessões de IA e para pessoas — as regras são as mesmas.

---

## 1. Os três mecanismos que tornam o paralelismo seguro

Paralelismo não vem de dividir tarefas. Vem de eliminar as três causas de colisão.

| Causa de colisão | Mecanismo |
|---|---|
| Duas tarefas decidem a mesma interface de formas diferentes | **[Contratos congelados](./CONTRATOS.md)** — decididos antes, alteráveis só por tarefa própria |
| Duas tarefas editam o mesmo arquivo | **Propriedade exclusiva de arquivo** — cada tarefa declara os arquivos que só ela escreve |
| Uma tarefa espera por algo que ninguém sabia que ela esperava | **Grafo de dependências explícito** no [BOARD](./BOARD.md) |

Se os três estiverem respeitados, duas sessões podem trabalhar na mesma onda sem
nunca se falarem.

---

## 2. Protocolo de leitura — o que uma sessão nova lê

Uma sessão que assume uma tarefa lê, **nesta ordem, e nada além disto**:

1. O arquivo da própria tarefa — `T-0NN-*.md`
2. [`CONTRATOS.md`](./CONTRATOS.md)
3. Os ADRs que a tarefa cita — **só esses**
4. As regras `RN-*` que a tarefa cita, no [documento 02](../02-regras-de-negocio.md)

**Não é necessário ler o PRD inteiro, nem os quatro documentos narrativos.** Se uma
tarefa não puder ser executada com essa leitura, a tarefa está mal escrita — e
corrigir a tarefa é a ação certa, não ler mais.

Cada arquivo de tarefa é auto-contido de propósito. Isso é o que permite começar
uma sessão fria no meio do projeto.

---

## 3. Ciclo de vida de uma tarefa

```
Disponível → Em andamento → Em revisão → Concluída
                    ↓
                Bloqueada
```

**Assumir uma tarefa:** editar o [BOARD](./BOARD.md), marcar `🔵 em andamento` com
identificação e data. É um commit de uma linha, direto na branch principal. Isso é
o lock — não há outro.

**Concluir:** marcar `✅` no BOARD, no mesmo commit do merge.

**Bloquear:** marcar `🔴 bloqueada por <motivo>` e **parar**. Não contornar, não
adivinhar contrato, não editar arquivo de outra tarefa.

---

## 4. Regra da propriedade exclusiva

Toda tarefa declara duas listas:

- **Arquivos de propriedade exclusiva** — só esta tarefa escreve neles, na sua onda.
- **Arquivos que só pode ler** — consumidos, nunca modificados.

> **Uma tarefa que precisa escrever num arquivo que não é seu está bloqueada.**
> Não é uma exceção justificável; é o sinal de que o corte de tarefas está errado.

### Arquivos compartilhados e como não brigar por eles

Alguns arquivos são inevitavelmente tocados por muita gente. Regras específicas:

| Arquivo | Regra |
|---|---|
| `registry/indice.ts` | **Gerado**, nunca editado à mão. Um script varre `registry/componentes/*` |
| `package.json` | Dependência nova é linha isolada; conflito se resolve mantendo as duas |
| `BOARD.md` | Só a linha da própria tarefa. Conflito aqui é sempre trivial |
| `CONTRATOS.md` | **Ninguém**, exceto tarefa de contrato explícita |

O `registry/indice.ts` gerado é o detalhe que evita o pior conflito do projeto: 23
componentes registrados à mão num arquivo só seriam 23 conflitos garantidos.

---

## 5. Git

Uma tarefa, uma branch, uma worktree:

```bash
git worktree add ../trabalho/T-018 -b tarefa/T-018-componentes-de-lote
```

Worktree separada por tarefa é o que permite várias sessões simultâneas sem
disputar o diretório de trabalho.

**Commits:** `T-018: <o que mudou>` — o id no início, sempre. É o que liga o
histórico à tarefa e ao critério de aceite meses depois.

**Merge:** só com o Definition of Done inteiro verde. Sem exceção "eu arrumo
depois" — a próxima tarefa já vai estar construindo em cima.

---

## 6. Definition of Ready

Uma tarefa só entra em `disponível` quando:

- [ ] Todas as dependências estão `✅`
- [ ] Os contratos que ela consome estão congelados
- [ ] Os critérios de aceite são verificáveis por teste, não por opinião
- [ ] A lista de arquivos de propriedade exclusiva não intersecta nenhuma outra
      tarefa em andamento

---

## 7. Definition of Done

Vale para **toda** tarefa. Uma tarefa que não cumpre isto não é mergeada.

- [ ] Critérios de aceite da tarefa passam como teste automatizado
- [ ] `npm run arch:check` verde
- [ ] `npm run typecheck` verde — sem `any`, sem `@ts-expect-error` não justificado
- [ ] `npm test` verde
- [ ] Nenhum arquivo fora da lista de propriedade exclusiva foi modificado
- [ ] Se a tarefa registra componente: entrou no teste de orçamento de catálogo
      (`RNF-08`) e no teste de catálogo por persona (ADR-0003)
- [ ] Se a tarefa toca escrita: existe teste de autorização **negativa** — um papel
      que não pode, tentando, e sendo recusado no servidor
- [ ] BOARD atualizado para `✅`

> **O item da autorização negativa é o mais importante da lista.** Testar que
> Helena consegue liberar quarentena prova pouco. Testar que Ivo **não** consegue,
> nem por requisição forjada, é o que prova a arquitetura.

---

## 8. Testar negativamente é a regra da casa

Herdado da v1, onde as três regras do `arch:check` foram validadas introduzindo as
violações de propósito.

> **Uma regra que nunca falhou não é evidência de nada.**

Na prática, para todo mecanismo de proteção:

1. Escreva o teste que prova que funciona quando deveria funcionar.
2. Escreva o teste que prova que **falha** quando deveria falhar.
3. O segundo é o que vale.

---

## 9. Quando perguntar

Antes de implementar, **uma linha** — com a recomendação
([ADR-0028](../adr/0028-processo-de-decisao.md)).

| Exige pergunta | Não exige |
|---|---|
| acrescentar dependência ou container | corrigir bug |
| mudar contrato congelado | escrever teste |
| escolher entre caminhos com custo ou risco distintos | seguir ADR já registrado |
| alterar como o projeto é executado ou publicado | refatorar dentro da tarefa |

Uma pergunta **sem recomendação** empurra o trabalho de volta em vez de
adiantá-lo. Diga o que você faria e por quê; a decisão continua sendo de quem
decide.

Depois de decidida: implementa, escreve o ADR como **Aceito**, e revisa os
documentos afetados **no mesmo commit**.

> Isto nasceu de um erro concreto: quatro containers de observabilidade foram
> acrescentados sem perguntar e revertidos em seguida. O trabalho perdido foi o
> menor custo — o maior foi o ADR ter virado justificativa de fato consumado em
> vez de registro de escolha.

## 10. Quando parar

Uma sessão para e sinaliza — não improvisa — quando:

- Precisa mudar um contrato congelado
- Precisa escrever num arquivo de outra tarefa
- Descobre que um critério de aceite é ambíguo ou não verificável
- Descobre conflito entre duas regras `RN-*`
- Uma decisão de negócio não está em lugar nenhum dos documentos

Os dois últimos casos produzem **um achado**, registrado no BOARD. Achado que
muda regra vira pergunta ao cliente; achado que muda decisão técnica vira ADR.

**Nenhum desses casos se resolve com uma suposição registrada em comentário de
código.** É assim que documentação e sistema divergem.

---

## 11. Estimativas

| Tamanho | Significado |
|---|---|
| **P** | Uma sessão curta. Escopo evidente, poucos arquivos |
| **M** | Uma sessão. O tamanho alvo — a maioria das tarefas deveria ser M |
| **G** | Mais de uma sessão. Candidata a ser quebrada; só permitida quando o corte criaria acoplamento pior |

Tarefa `G` que não é caminho crítico deve ser quebrada antes de começar.
