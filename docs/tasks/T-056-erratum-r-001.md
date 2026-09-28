# T-056 — O erratum do R-001, e o destino do A-08b

| | |
|---|---|
| **Trilha** | E · ambiente e qualidade |
| **Tamanho** | P |
| **Depende de** | nada — a evidência já está no repositório |
| **ADRs** | [0013](../adr/0013-suite-de-avaliacao.md), [0025](../adr/0025-agnosticismo-de-provedor.md) |
| **RN** | nenhuma |
| **Origem** | achado [A-47](./ACHADOS.md), aberto em 2026-09-25 ao limpar os worktrees |
| **Escrita em** | 2026-09-25 |

## Por que existe

O [R-001 §8](../relatorios/R-001-medicao-modelo-real.md) afirma duas coisas que a
evidência contradiz:

> *"AC-1 não cumprido. As perguntas não foram escritas nem commitadas antes da
> primeira execução."* · *"`api/src/estoque/spike/` nunca foi construído."*

As duas existiam, fora da `main`. O commit `e753200` (branch `tarefa/T-017`,
**2026-09-08 12:15:48 -03**) congela 30 perguntas, com mensagem citando o AC-1
nominalmente; os dados brutos têm **120 execuções** cujo campo `perguntas_de`
aponta para aquele arquivo; e o `spike/` estava na pasta de trabalho. Tudo isso
foi recuperado para o repositório em 2026-09-25 ([A-47](./ACHADOS.md)).

**O relatório não está errado nos números.** A rodada recuperada é *outra*: usou
`sonnet-4.6`, com 30 perguntas e 120 execuções; a publicada usou `sonnet-5` e
`haiku-4.5`, com 17 casos e 68 execuções. Uma rodada anterior foi abandonada sem
publicação, e o texto do §8 descreve a publicada como se fosse a única.

O que muda é o que se pode **afirmar sobre o AC-1** — e, por consequência, sobre
o [A-08b](./ACHADOS.md), que hoje está registrado como *"não recuperável"*.

## O que já foi conferido

- **Os arquivos estão na `main`**, commitados em `7fcb9de`:
  `docs/relatorios/R-001-perguntas.json` (30 perguntas) e
  `docs/relatorios/R-001-dados-brutos.json` (120 execuções, 188 KB). O `spike/`
  foi para `.archive/T-017-spike-medicao.tar.gz` — é código anterior à
  reorganização hexagonal e não compila contra o domínio de hoje.
- **A integridade bate:** os 30 `id` das perguntas são exatamente os 30
  `pergunta_id` distintos das execuções. 100% de schema válido, 96,7% de
  composição correta.
- **A data é verificável em um comando**, e não depende de acreditar em ninguém:
  `git show -s --format='%ci %ci' e753200` — data de autor e de committer
  iguais, sem sinal de reescrita.
- **A prova de data mora só na branch.** `tarefa/T-017` é hoje o único lugar que
  carrega o carimbo; os arquivos, sozinhos, não provam *quando* foram escritos.

## Decisão que a tarefa precisa tomar

**O A-08b fecha?** A pergunta é uma só, e o critério é este: *o AC-1 existia para
impedir que as perguntas fossem ajustadas ao resultado*. A rodada recuperada tem
essa proteção; a rodada publicada, não. Duas leituras defensáveis:

| Leitura | Consequência |
|---|---|
| **Fecha** — a disciplina do AC-1 foi cumprida numa medição real, e a evidência existe | o A-08b sai do ACHADOS; o §8 registra que a proteção existiu, na rodada de 30 |
| **Não fecha** — a medição *publicada* continua sem a proteção, e é ela que sustenta o "seguir" do §7 | o A-08b fica, com o texto corrigido: não é "não recuperável", é "não vale para a rodada publicada" |

**A recomendação é a segunda**, por um motivo: o número que o PRD §9 cita e a
recomendação de seguir vêm dos 17 casos, não das 30 perguntas. Fechar o achado
transferiria para a rodada publicada uma garantia que ela não tem.

## Arquivos de propriedade exclusiva

```
docs/relatorios/R-001-medicao-modelo-real.md
docs/tasks/T-056-erratum-r-001.md
```

## Toca, com registro

```
docs/tasks/ACHADOS.md            A-47 fecha; A-08b conforme a decisão acima
docs/tasks/PROGRESSO.md          a linha da T-017 para de dizer "não recuperável"
docs/tasks/BOARD.md              status
docs/relatorios/achados-resolvidos.md   destino do A-47 (e do A-08b, se fechar)
```

## Critérios de aceite

- [x] **AC-1** O R-001 ganha um **erratum datado** no fim do §8, que corrige as
      duas frases sem reescrever o texto original. Relatório é registro: apagar
      o que ele dizia esconderia que houve divergência.
- [x] **AC-2** O erratum descreve a rodada recuperada com os números conferidos —
      30 perguntas, 120 execuções, `sonnet-4.6` + `haiku-4.5`, dois modos, 100%
      de schema válido, 96,7% de composição correta — e diz explicitamente que
      **não é** a rodada dos números do §4.
- [x] **AC-3** A decisão sobre o A-08b está registrada com o critério que a
      sustenta, não só com o veredito.
- [x] **AC-4** A prova de data deixa de depender da branch: o erratum traz o
      hash `e753200`, a data, e o comando que qualquer pessoa roda para
      conferir. **Verificado rodando o comando** e comparando com o texto.
- [x] **AC-5** Depois do AC-4, `tarefa/T-017` pode ser apagada sem perder
      evidência — e a tarefa diz isso em uma linha, porque hoje o
      [A-47](./ACHADOS.md) manda o contrário.
- [x] **AC-6** A linha da T-017 no PROGRESSO deixa de dizer "AC-1 não
      recuperável" e passa a dizer o que ficou decidido, com o ponteiro.
- [x] **AC-7** O A-47 sai do ACHADOS para `achados-resolvidos.md`, deixando só
      o id citável — a regra da casa para achado fechado.

## Não faz

- **Republicar a medição.** Rodar o modelo de novo custa token
  ([ADR-0013](../adr/0013-suite-de-avaliacao.md)) e não é o assunto: o assunto é
  o que o relatório afirma sobre o que já foi medido.
- **Ressuscitar o `spike/`** para `api/src/`. Fica no `.archive/`.
- **Mexer nos 17 casos da T-032.** A disciplina de pré-commitação para casos
  novos continua sendo assunto dela.
