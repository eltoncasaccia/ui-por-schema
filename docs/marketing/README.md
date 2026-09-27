# Material de divulgação — captura e medição

Vídeo e prints para redes sociais e site, gravados **contra o sistema de
verdade**, nunca desenhados. O README não embute print (screenshot desatualizado
mente em silêncio); este material tem outro propósito: mostrar o produto a quem
não conhece o sistema.

**As imagens e os vídeos ficam em `docs/marketing/midia/`, que o `.gitignore`
exclui** (`MARKETING_SAIDA` muda o destino). Ficam no projeto para quem edita
achar sem procurar; ficam fora do git porque vídeo entra no histórico e não sai
mais — e este material se regenera em minutos.

| Pasta | Conteúdo |
|---|---|
| `midia/vertical/` | mp4 1080×1920 — Reels, Stories, TikTok |
| `midia/horizontal/` | mp4 1920×1080 — site, YouTube |
| `midia/prints/` | PNG 2880×1800 |
| `midia/video/` | os `.webm` originais do Playwright |
| `midia/converter.sh` | refaz os dois formatos a partir dos `.webm` |

> Este diretório é para leitor humano decidir o que publicar. **Agente não abre
> os prints** — cada um custa milhares de tokens e não diz nada que a view em
> `web/src/views/` não diga melhor.

### Os outros documentos daqui

| Arquivo | Para quê |
|---|---|
| [`montagem.md`](montagem.md) | o corte de 45 s clipe a clipe, com os tempos, a locução, a cartela final e a legenda do post |
| [`prompts-gemini.md`](prompts-gemini.md) | prompts prontos para colar no Gemini: b-roll, variações de roteiro, legendas de carrossel |

---

## 1. Como regerar

```bash
make up                                        # exige o stack no ar (5173)
cd web && npx tsx scripts/capturar-marketing.ts
CENAS=03-assistente npx tsx scripts/capturar-marketing.ts   # só uma cena
../docs/marketing/midia/converter.sh           # webm → mp4 9:16 e 16:9
```

O script imprime o **timecode de cada beat**, relativo ao início da cena — o
corte na edição é por número, não por olho.

### As cenas

| Cena | O que prova |
|---|---|
| `01-entrada` | quem entra é uma pessoa com um cargo, e o cargo decide a tela |
| `02-menu` | o menu convencional existe — o assistente **não** substitui a navegação |
| `03-assistente` | **a tese:** pergunta em português vira composição de componentes registrados |
| `04-fixar` | a estrela: o usuário monta o próprio menu (`viewKey`, [ADR-0021](../adr/0021-viewkey-e-viewid.md)) |
| `05-compartilhar` | a lista traz **só** quem consegue abrir aquela composição |
| `06-permissao` | Helena e Ivo na mesma URL — três diferenças ao mesmo tempo (abaixo) |
| `07-escuro` | o mesmo sistema em tema escuro |

### O que NÃO é capturado, e por quê

- **Escrita** (registrar recebimento, saída com FEFO). O clique grava de
  verdade, e a captura aponta para o banco de desenvolvimento: o que entra em
  `movimento` e `auditoria` não se apaga (A-44). Para gravar essas cenas,
  apontar antes para `estoque_teste`.
- **Execution Trace.** É o material mais forte que existe para público de
  desenvolvedor — mostra `schema válido`, `aceitos`, `rejeitados` e o tempo, na
  tela, sem narração. Saiu da captura porque, aberto sobre o workspace, o botão
  **Exportar** da view renderiza por cima do conteúdo do painel. Volta assim que
  isso for corrigido: filmar defeito de layout entrega o defeito, não o
  argumento.

---

## 2. Medição: a composição tem substância?

A [R-001](../relatorios/R-001-medicao-modelo-real.md) mediu se o schema é
**válido**. Para divulgação a pergunta é outra e ninguém tinha medido: a tela
que nasce tem **substância**? Uma composição de um bloco só pode estar correta e
ser pobre de filmar.

**Medido em 2026-09-25**, modelo local `qwen2.5:7b` (`PROVEDOR=compativel`,
`MODO_DECODIFICACAO=restrito`), ator Cleide (conferente), via
`web/scripts/medir-composicao.ts`.

| Pergunta | Blocos compostos | Tempo |
|---|---|---|
| o que está vencendo nos próximos 90 dias | **falhou** — "o assistente nao respondeu" | — |
| gráfico de vencimentos por mês **e** a fila de lotes | `vencimento_grafico` + `fila_vencimento` | 7 646 ms |
| o que vence, o que está em quarentena **e** o saldo por unidade | `fila_vencimento` + `quarentena_fila` + `produto_saldo_por_unidade` | 6 913 ms |
| houve excursão de temperatura no refrigerado? | `temperatura_excursoes` | 4 037 ms |

**Schema válido e zero rejeitados nas três que responderam.** Numa execução
anterior, a mesma primeira pergunta respondeu em 3 847 ms com
`fila_vencimento` — ou seja, a falha é intermitente, não é da pergunta.

### O que isso quer dizer

1. **Composição de múltiplos blocos já funciona no modelo local.** Pedindo três
   coisas, vieram três componentes certos, na ordem da pergunta. O teto da
   divulgação não é a riqueza da composição.
2. **O teto é a confiabilidade.** Uma falha em quatro, e uma carga a frio que
   devolve `422` (`invalido`, [`app.py:128`](../../api/src/estoque/server/app.py))
   depois de minutos. É por isso que `capturar-marketing.ts` **aquece o modelo
   fora da gravação** — a primeira tentativa de captura se perdeu inteira
   esperando um cartão que nunca viria.
3. **Trocar de modelo melhora a confiabilidade e a latência, não a riqueza.**
   A R-001 mediu 100 % de schema válido com `claude-sonnet-5` e
   `claude-haiku-4.5`. Nenhum dos dois foi medido *neste* eixo — número de
   blocos por pergunta segue sem medição fora do modelo local.

### Medido de novo em 2026-09-27, com `anthropic/claude-sonnet-5`

Mesmas quatro perguntas, mesmo ator, `PROVEDOR=openrouter`:

| Pergunta | `qwen2.5:7b` local | `claude-sonnet-5` |
|---|---|---|
| o que está vencendo nos próximos 90 dias | **falhou** | `fila_vencimento` · 8 564 ms |
| gráfico **e** fila | 2 blocos · 7 646 ms | 2 blocos · 7 117 ms |
| vence **+** quarentena **+** saldo por unidade | **3 blocos** · 6 913 ms | **2 blocos** · 6 364 ms |
| excursão de temperatura | 1 bloco · 4 037 ms | 1 bloco · 6 670 ms |

**O modelo pago ganha em confiabilidade — 4 de 4 contra 3 de 4 — e só nisso.**
Não é mais rápido (6,4 a 8,6 s contra 4,0 a 7,6 s), e na pergunta de três partes
compôs **menos** blocos que o modelo local: deixou `produto_saldo_por_unidade`
de fora.

Para filmar, a leitura é contraintuitiva e vale registrar: **trocar para o
modelo pago não melhora o vídeo.** Melhora a chance de a gravação não falhar no
meio. Os dois números que importam para a captura — tempo na tela e número de
blocos — ficam iguais ou piores.

---

## 3. Os argumentos, conferidos na tela

O que a captura confirmou, com o print como prova — e não o que se imaginava
antes de gravar.

### Permissão: três diferenças, não uma

Mesma URL `/quarentena`, duas identidades:

| | Helena — RT, 3 unidades | Ivo — gerente, 2 unidades |
|---|---|---|
| item no menu | **Liberar quarentena** | **Quarentena** — só ver |
| "Controlados" no menu | sim | não |
| lotes na fila | 2 (CD Matriz + Uberlândia) | 1 (só CD Matriz) |
| sugestões do assistente | "houve excursão de temperatura?" | "registrar recebimento" |

O roteiro dizia "o botão não aparece". É menos do que o sistema faz: muda o
menu, muda **o escopo do dado**, e muda até o que o assistente sugere perguntar.

### Frases que já estão escritas no produto

Não precisam ser inventadas pelo marketing — estão na interface e no código:

- no painel do assistente: *o modelo escolhe quais componentes compor — nunca
  escreve código, nunca vê os dados, nunca autoriza escrita*
- no diálogo de compartilhar: *compartilha-se o schema, não os dados*; *a pessoa
  abre sob a permissão dela*
- em [`Compartilhar.tsx`](../../web/src/shell/Compartilhar.tsx): *compartilhar
  aponta para uma view, não concede acesso*
- no trace: *componente não registrado é rejeitado e aparece aqui*

### O cliente é fictício, e o material precisa dizer isso

A Bertoni não existe ([documento 01](../01-o-cliente.md)). Posicionar como
demonstração ou caso de estudo, nunca como cliente em produção — um farmacêutico
que descobrir depois perde a confiança no resto.
