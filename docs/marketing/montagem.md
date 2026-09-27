# Montagem — o corte de 45 s, clipe a clipe

Guia para montar no CapCut (ou qualquer editor) a partir do que está em
`midia/vertical/`. Os tempos dentro de cada clipe são os **beats** que
`capturar-marketing.ts` imprime ao gravar — se você regravar, os números mudam
e o script reimprime os novos.

**Todos os clipes são mudos.** A locução e a trilha entram na edição.

---

## 1. A linha do tempo

| # | Clipe | Usar de → até | Dura | Texto queimado na tela |
|---|---|---|---|---|
| 1 | `01-entrada` | 1,5 → 4,5 | 3 s | Eu não programei essa tela. |
| 2 | `03-assistente` | 2,0 → 12,0 | 10 s | Ela nasceu da pergunta. |
| 3 | `03-assistente` | 15,5 → 19,1 | 3,6 s | *(sem texto — deixa a tela respirar)* |
| 4 | `06-permissao` | 3,5 → 12,5 | 9 s | Mesma pergunta. Telas diferentes. |
| 5 | `04-fixar` | 2,0 → 9,0 | 7 s | Gostou? Fixa. Vira seu menu. |
| 6 | `05-compartilhar` | 4,0 → 11,0 | 7 s | Ela abre com a permissão dela. |
| 7 | `07-escuro` | 3,0 → 8,0 | 5 s | *(cartela final por cima)* |

**Total: 44,6 s.** Corte seco entre todos, sem transição — transição em demo de
software parece apresentação de PowerPoint.

### Os beats de cada clipe, para ajustar o corte

Duração total de cada arquivo e o que acontece dentro dele:

| Clipe | Dura | Beats |
|---|---|---|
| `01-entrada` | 8,2 s | 2,5 tela de entrada · 3,7 dentro, como Cleide |
| `02-menu` | 7,7 s | 2,6 menu de Cleide · 5,8 fila de vencimento |
| `03-assistente` | 19,1 s | 2,0 painel aberto · 4,3 pergunta digitada · 5,7 enviada · **10,5 a tela existe** · 17,1 promovida a tela inteira |
| `04-fixar` | 9,8 s | 3,5 estrela · 7,6 o menu que ela montou |
| `05-compartilhar` | 14,6 s | 5,4 a lista de quem consegue abrir · 9,3 mensagem · 9,4 entregue |
| `06-permissao` | 13,1 s | 5,6 Helena na quarentena · 7,4 menu do Ivo · 11,1 Ivo na mesma URL |
| `07-escuro` | 8,9 s | 4,8 lotes, tema escuro |

`02-menu` ficou de fora do corte de 45 s por falta de tempo. Ele é o que
responde a objeção *"então virou chatbot?"* — entra na versão de 60 s, entre o
1 e o 2.

---

## 2. A locução

Fala de ~2,5 palavras por segundo. Cada bloco cabe no clipe correspondente.

> **[1]** Esse sistema tem uma tela que ninguém programou.
>
> **[2]** Ela nasce quando alguém pergunta. Em português, do jeito que a pessoa fala. Quatro segundos.
>
> **[4]** A mesma pergunta, feita por duas pessoas, devolve telas diferentes. Muda o menu, muda o dado que ela alcança, e muda até o que o assistente sugere perguntar.
>
> **[5]** Gostou da tela? Fixa, e ela vira item do seu menu.
>
> **[6]** Manda pra colega, e ela abre com a permissão dela, não com a sua.
>
> **[7]** *(silêncio — a cartela fala sozinha)*

**Cartela final**, sobre o clipe 7:

```
A IA escolhe o que te mostrar.
Nunca o que gravar.

roda com IA na nuvem ou dentro da sua empresa

Elton Casaccia
```

---

## 3. Ajustes no CapCut

- **Formato:** 9:16. Os clipes já são 1080×1920 com o sistema encaixado no
  terço central — o espaço em cima é onde o texto queimado vai, e o de baixo
  fica livre da interface do Instagram.
- **Nada de zoom automático ("Ken Burns").** Interface com texto pequeno fica
  ilegível quando se move.
- **Legenda automática não serve:** a locução é gravada depois. Escreva o texto
  à mão, exatamente como está na tabela.
- **Trilha:** entra no clipe 2 e sai no 7. Volume baixo, sem batida marcada — o
  assunto é estoque farmacêutico, não academia.
- **Exportar:** 1080×1920, 30 fps, qualidade alta. Para o site, refazer o mesmo
  corte com os arquivos de `midia/horizontal/`.

---

## 4. A legenda do post

> Passei os últimos meses construindo um sistema de estoque para uma
> distribuidora farmacêutica onde a tela não existe até alguém perguntar.
>
> Você digita "o que está vencendo nos próximos 90 dias" e o sistema monta a
> tela: o número, o gráfico, a lista e a ação. Se quem perguntou não pode
> liberar quarentena, a ação não aparece — não está escondida, ela não foi
> montada.
>
> E o detalhe que mais interessa a quem tem dado sensível: nada do estoque vai
> para a IA. Ela recebe a pergunta e o cardápio de telas. Só isso.
>
> Funciona com IA na nuvem ou com modelo rodando dentro da empresa.
>
> Se você tem um processo que hoje vive em planilha e ninguém aguenta mais, me
> chama.

**O cliente é fictício** ([documento 01](../01-o-cliente.md)) — se alguém
perguntar, é uma demonstração construída como caso de estudo. Dizer isso de
saída vale mais que ser descoberto depois.
