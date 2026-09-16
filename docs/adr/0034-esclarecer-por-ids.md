# ADR-0034 — Pergunta vaga devolve ids para escolher, nunca uma pergunta escrita

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-14 (implementado) · registrado em 2026-09-16 |
| **Escopo** | Assistente |
| **Emenda** | [ADR-0001](./0001-ui-por-schema.md): campo novo no `ViewSchema`, como manda o CONTRATOS §11 |

## Contexto

Perguntas como "quero registrar" ou "quero ver" cabem em mais de um componente.
Até aqui, o modelo tinha duas saídas, e as duas eram ruins:

- **escolher sozinho**, e acertar ou errar sem que a pessoa perceba a escolha;
- **devolver `blocos: []`**, e a resposta "não sei responder" chega para uma
  pergunta que o sistema sabe responder.

O jeito natural seria o modelo **perguntar de volta**. Só que uma pergunta
escrita pelo modelo é texto livre exibido com cara de tela oficial, que é o
mesmo problema do `titulo` apontado no [A-42](../tasks/ACHADOS.md). Com modelo
real, o texto hostil colado na pergunta chegou ao título em 5 de 6 tentativas.

## Decisão

> **O `ViewSchema` ganha `esclarecer: tuple[ComponentId, ...]`, com até 4
> itens. São ids, nunca texto.**

- **No schema restrito** (`assistant/adapter.py`), `esclarecer` é um `enum`
  com os ids do catálogo **deste ator**. O modelo não consegue nem propor um
  id de fora.
- **Na validação** (`application/schema/validar.py`), uma opção fora do
  catálogo do ator é rejeitada, como acontece com um bloco. O decodificador
  restrito é uma segunda barreira, não a única.
- **O rótulo que a pessoa lê sai do registry** (`label`), montado em
  `server/rotas/assistente.py`. O modelo não escreve nenhuma palavra que
  apareça na tela.
- **No cliente**, uma opção que tem rota abre a tela direto (registrar é
  formulário, não resposta para ler na conversa). Uma opção sem rota vira a
  pergunta explícita que a pessoa escolheu.
- `blocos: []` com `esclarecer` preenchido é **resposta válida**, e não
  "tudo rejeitado".

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Campo `pergunta: str` escrito pelo modelo | é o A-42 outra vez: texto de fora, sem teto, com cara de oficial |
| Sempre escolher o componente mais provável | a escolha errada parece resposta certa, e ninguém percebe |
| Sugestões fixas no cliente, sem o modelo | não reage à pergunta; já existem, na tela vazia (`shell/sugestoes.ts`) |

## Consequências

- O vocabulário do modelo cresce por um campo, mas não por texto: o que ele
  pode dizer continua sendo um subconjunto do catálogo filtrado por permissão.
- O `strict` do decodificador exige `esclarecer` em `required`. Um provedor
  sem saída estruturada pode omitir o campo, e o default `()` cobre esse caso.
- **Teste negativo:** `api/tests/schema/test_esclarecer.py`. Uma opção
  privativa do RT, pedida para Ivo, é descartada e registrada como rejeição, e
  o schema restrito de Ivo não contém o id.
