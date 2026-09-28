# Prompts para o Gemini

Para colar direto. Cada bloco é auto-contido — não precisa de contexto da
conversa que o gerou.

> **O que o Gemini NÃO deve gerar: a interface.** Peça "tela de sistema de
> estoque" e o Veo devolve um painel inventado com texto ilegível. Para demo de
> software isso é pior que nada, e quem é da área percebe em dois segundos. A
> tela de verdade está gravada em `midia/vertical/`. O Gemini serve para o que
> **não** é tela: o depósito, a câmara fria, a pessoa.

---

## 1. B-roll (Veo) — o que entra por baixo da locução

Usar nos clipes 1, 4 e 7 da [montagem](montagem.md), em cortes de 1 a 2
segundos, nunca por cima do momento em que a tela se monta.

```
Gere 4 clipes de vídeo de 8 segundos, formato vertical 9:16, estilo documental
realista, luz natural, câmera em movimento lento e sutil, sem texto na tela,
sem interface de computador, sem gráficos:

1. Interior de um centro de distribuição farmacêutico brasileiro de porte médio.
   Corredores de prateleiras com caixas de medicamento. Um operador passa ao
   fundo, desfocado. Câmera desliza lateralmente. Luz fria de galpão.

2. Câmara fria de medicamentos, 2 a 8 graus. Vapor leve ao abrir a porta.
   Uma farmacêutica de jaleco branco confere uma caixa térmica. Detalhe das
   mãos e da etiqueta. Câmera lenta aproximando.

3. Sala de escritório simples dentro do galpão. Uma mulher de 40 anos, jaleco,
   olha um monitor fora de quadro. Expressão de quem encontrou o que procurava.
   Plano médio, profundidade de campo curta.

4. Mãos segurando um celular em pé, num corredor de estoque. A tela do celular
   NÃO deve aparecer legível — mantenha fora de foco ou em ângulo.
   Foco nas mãos e no ambiente ao fundo.
```

---

## 2. Variações de texto — ganchos e roteiros

Quando quiser outras versões do roteiro sem me chamar.

```
Você é redator de vídeo curto para redes sociais, em português do Brasil.
Tom: seco, direto, frase curta, sem jargão de marketing, sem emoji, sem
exclamação, sem "revolucionário" ou "game changer".

Produto: um sistema de controle de estoque para distribuidora farmacêutica
onde a tela não é programada antes — o usuário pergunta em português
("o que está vencendo nos próximos 90 dias?") e o sistema monta a tela na hora,
em cerca de 4 segundos: número, gráfico, lista e ação. Diferenciais:

- a mesma pergunta devolve telas diferentes conforme o cargo de quem pergunta.
  Muda o item de menu, muda o dado que a pessoa alcança, e muda o que o
  assistente sugere perguntar. A ação que ela não pode fazer não fica cinza:
  ela não é montada
- nenhum dado do estoque vai para a IA. Vai a pergunta e a lista de telas
  possíveis — nenhum lote, nenhum preço, nenhum nome
- o usuário fixa uma tela e ela vira item do menu dele
- ele envia a tela a um colega por dentro do sistema, e o colega abre sob a
  permissão dele, não a de quem enviou
- funciona com IA na nuvem ou com modelo rodando dentro da empresa

Públicos, nesta ordem: pessoa leiga que só precisa lembrar que eu trabalho com
software; dono de empresa com um processo preso em planilha; desenvolvedor.

Me entregue 5 ganchos de abertura de 3 segundos e, para o melhor deles, um
roteiro de 30 segundos com marcação de tempo e o texto que aparece na tela.
```

---

## 3. Carrossel a partir dos prints

Os PNG de `midia/prints/` servem de carrossel sem edição nenhuma. Para escrever
as legendas de cada lâmina:

```
Você é redator de redes sociais, português do Brasil, tom seco e direto.
Vou montar um carrossel de 6 lâminas com prints de um sistema de estoque
farmacêutico onde a tela é montada pela pergunta do usuário, em tempo real,
por um modelo de linguagem que nunca vê os dados.

As lâminas, nesta ordem:
1. tela de login com as pessoas da empresa, cada uma com seu cargo
2. o menu de uma conferente — só o que o cargo dela alcança
3. a pergunta digitada no assistente
4. a tela que nasceu dela: número, gráfico e lista de lotes vencendo
5. a mesma URL aberta pela responsável técnica e por um gerente, lado a lado:
   menus diferentes, e ela vê 2 lotes onde ele vê 1
6. o diálogo de compartilhar, que só lista quem consegue abrir aquela tela

Escreva para cada lâmina um título de no máximo 6 palavras e uma linha de
apoio de no máximo 20 palavras. A última lâmina termina em convite para
conversar, sem "link na bio".
```
