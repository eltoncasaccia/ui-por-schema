# ADR-0028 — Pergunta curta antes; ADR depois

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-08 |
| **Escopo** | Processo |

## Contexto

O [acordo de trabalho](../tasks/README.md) diz quando **parar** — contrato
congelado, arquivo de outra tarefa, regra ambígua. Não dizia nada sobre decisões
que aparecem no meio da execução e não caem em nenhuma dessas categorias.

Na prática, elas vinham sendo tomadas e documentadas depois. Isso produz um ADR
que **registra um fato consumado** em vez de sustentar uma escolha — e a seção
"alternativas consideradas" vira retórica, porque a alternativa já foi
descartada na hora de escrever o código.

O caso concreto: subir uma instância local do LangFuse. Quatro containers a mais
no projeto, decidido e implementado sem perguntar, e revertido em seguida porque
não era o que se queria. O trabalho foi perdido e o repositório ficou com um
arquivo a menos de história útil.

## Decisão

> **Decisão que não está nos documentos: pergunta curta antes de implementar.
> Uma linha, com a recomendação. Depois de decidida, vira ADR com status
> Aceito, e os documentos afetados são revisados no mesmo commit.**

### O que exige pergunta

Acrescentar dependência ou container · mudar contrato congelado · escolher entre
caminhos com custo ou risco distintos · qualquer coisa que altere como o projeto
é executado ou publicado.

### O que não exige

Corrigir bug · escrever teste · seguir decisão já registrada em ADR · nomear
variável · refatorar dentro do escopo de uma tarefa.

### O que a pergunta contém

O que se decide, as opções reais, e **qual eu recomendo e por quê**. Uma
pergunta sem recomendação empurra o trabalho de volta em vez de adiantá-lo.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **ADR "Proposto" antes de implementar** | Mais rigoroso e mais lento: escrever o ADR inteiro antes de saber se a coisa funciona produz documento sobre hipótese. Bom para decisão irreversível; caro para todas |
| Decidir e documentar depois | O que vinha sendo feito. Produz ADR que justifica em vez de decidir, e desperdiça trabalho quando a decisão não era a desejada |
| Perguntar tudo | Transforma execução em ping-pong e devolve ao humano o trabalho que ele delegou |

## Consequências

**Positivas**
- A alternativa é descartada **antes** do código, que é quando descartar é barato.
- O ADR passa a registrar uma escolha real, com o dono da decisão certo.
- Menos retrabalho do tipo "implementei e revertemos".

**Negativas**
- Mais idas e voltas. Uma pergunta mal calibrada — sobre algo óbvio — custa uma
  rodada e irrita.
- A fronteira entre "exige pergunta" e "não exige" é julgamento, não regra. Vai
  errar para os dois lados.

**Riscos aceitos**
- Errar para o lado de perguntar demais é preferível a errar para o lado de
  implementar quatro containers que ninguém pediu.

## Conformidade

Não é verificável por teste — é acordo entre quem executa e quem decide. O que
dá para observar: todo ADR daqui em diante nasce de uma pergunta registrada na
conversa, e o commit que o acrescenta também revisa os documentos afetados.

## Referências
- [Acordo de trabalho §9](../tasks/README.md) — "quando parar"
