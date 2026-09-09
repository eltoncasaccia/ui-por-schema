# ADR-0032 — A borda HTTP quebrada por área

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-09 |
| **Escopo** | Ciclo 1 |
| **Relacionado** | [ADR-0031](0031-ports-and-adapters.md) · [ADR-0030](0030-layout-de-diretorios.md) |

## Contexto

`server/app.py` chegou a **817 linhas e 20 endpoints** num arquivo só. O
[ADR-0031](0031-ports-and-adapters.md) descreve `server/` como o adapter
primário — a casca fina que traduz HTTP para caso de uso. Uma casca de 817
linhas não é fina, e a descrição parou de valer.

O custo apareceu em três lugares, e nenhum deles é estético:

1. **Propriedade exclusiva de arquivo virou ficção.** T-011, T-025, T-037 e
   T-040 declararam `server/app.py` e escreveram todas nele. A regra que existe
   para tornar o trabalho paralelo seguro não podia ser cumprida, porque o corte
   de tarefas era por área e o arquivo era um só.

2. **Ler uma rota custava o arquivo inteiro.** Mexer no `/api/comandos/{nome}`
   — 33 linhas — obrigava a carregar as outras 784. Numa sessão com orçamento
   de contexto, isso é caro toda vez, e é caro de novo a cada releitura depois
   de editar.

3. **Nada impedia o crescimento.** Não havia regra que dissesse onde uma rota
   nova deve morar, então ela morava onde a anterior morava.

## Decisão

> **Uma rota por área, num router próprio. `app.py` é raiz de composição: monta
> a aplicação, registra o que vale para TODA rota, e não conhece nenhuma regra
> de negócio.**

```
server/
  app.py       montagem, middleware de CSRF, 3 handlers de erro, ciclo de vida
  deps.py      o núcleo que toda rota usa: motor, CFG, OBS, ok, ator, repos, Tx
  rotas/
    saude.py  auth.py  catalogo.py  assistente.py
    views.py  compartilhamento.py   dados.py      comandos.py
```

**Três coisas ficam em `app.py`, e as três pelo mesmo motivo: valem para todas
as rotas, e uma rota nova não pode esquecê-las.**

- o middleware de CSRF — **middleware e não dependência por rota**, porque
  dependência esquecida numa rota nova é um buraco silencioso, e rota nova é
  exatamente o que se acrescenta com pressa;
- os três handlers de erro, incluindo o serializador único que descarta
  `detalhe_interno` ([ADR-0014](0014-erros-que-nao-vazam.md));
- o ciclo de vida do motor.

**`deps.py` existe para que os routers não importem `app.py`.** Se importassem,
`app.py` teria que importá-los de volta para registrá-los, e o ciclo só se
resolveria com import tardio dentro de função — o tipo de solução que funciona e
esconde o problema.

`CFG` e `_engine` são **reexportados** por `app.py`: continuam importáveis de
`estoque.server.app`, apontando para o mesmo objeto.

## O contrato que sustenta isso

`api/.importlinter`, **contrato 5** — `independence` entre os oito routers.

Sem ele, a divisão se desfaz sozinha: bastava uma rota importar um helper da
vizinha para o monolito voltar por dentro — oito arquivos que só rodam juntos, o
que é pior que um arquivo de 817 linhas, porque parece resolvido.

E o contrato tem **teste negativo**
(`tests/arquitetura/test_verificador_falha_quando_violado.py`): um fixture
introduz `rotas.auth -> rotas.comandos` de propósito e afirma que o
`lint-imports` sai diferente de zero. Uma regra que nunca falhou não é evidência
de nada.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Deixar como estava | O custo já estava cobrado: quatro tarefas escreveram no mesmo arquivo, e a propriedade exclusiva não era verificável |
| Um router só, em `rotas.py` | Move o problema 40 linhas para o lado. O que dói é o tamanho do arquivo, não o nome dele |
| `deps` como `Depends()` do FastAPI por rota | Mais idiomático, e foi tentador. Mas o CSRF **precisa** ser middleware (rota nova não pode esquecê-lo), e ter metade transversal em middleware e metade em `Depends` seria pior de explicar que a assimetria atual |
| Reexportar as rotas em `app.py` para não tocar nos testes | Um shim de compatibilidade permanente para poupar cinco linhas de import. Os testes que quebraram inspecionam **código-fonte por caminho de módulo** — é natural que sigam o código |

## Consequências

**Boas.** Uma tarefa que mexe numa rota lê 60–180 linhas em vez de 817. O corte
de tarefas por área passa a ter um arquivo por área, então propriedade exclusiva
volta a ser cumprível. E rota nova tem um lugar óbvio para morar.

**O preço.** Os imports se repetem entre os módulos: 817 linhas viraram 965
somando tudo. É o custo de módulos independentes, e o contrato 5 é o que impede
que alguém "economize" essas linhas fazendo um router importar o outro.

**Aceito com ressalva.** `deps.py` cria estado de módulo (`motor`, `CFG`, `OBS`)
na importação, como `app.py` fazia antes. Não é bonito para teste, mas é
exatamente o comportamento anterior — mudá-lo seria outra decisão, e esta já é
grande o bastante.
