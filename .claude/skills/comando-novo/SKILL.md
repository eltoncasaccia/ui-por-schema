---
name: comando-novo
description: Cria um comando de escrita — schema-folha em api/src/estoque/application/commands/entradas/, executável em commands/, e o CommandDef que o componente declara. Use ao executar tarefa de W4, ao ver "POST /api/comandos/<nome>" no escopo da tarefa, ou quando ela disser "registra o comando X", "pipeline de comando", "o formulário grava". Cobre requires, idempotência, If-Match, confirmação, o que o pipeline já faz, as armadilhas de saldo e os testes negativos obrigatórios.
---

# Comando novo — o plano de escrita

Um comando tem **três peças**, e as três existem por causa do
[ADR-0002](../../../docs/adr/0002-plano-render-plano-escrita.md): *a saída do
modelo autoriza renderizar, nunca autoriza escrever.*

```
commands/entradas/<dominio>.py   o SCHEMA        módulo-FOLHA: só pydantic e domain
commands/<dominio>.py            o EXECUTÁVEL    registra `Comando`, usa sqlalchemy
registry/componentes/<id>.py     a DESCRIÇÃO     `CommandDef` — sem função nenhuma
```

O componente **declara** o comando; este módulo o **executa**. Os dois se ligam
por nome, e a bijeção é conferida em `tests/commands/test_ac1_barreira.py`.

> **Por que o schema mora num módulo-folha.** O `registry` precisa dele para
> declarar o `CommandDef`, e o contrato 2 do import-linter proíbe
> `registry → sqlalchemy` **inclusive por caminho indireto**. Um import de
> `pipeline`, de `data` ou de SQLAlchemy dentro de `entradas/` quebra o CI na
> hora. Uma definição, dois lados: duas declarações do mesmo formulário
> divergiriam (achado A-11).

`commands/indice.py` é **gerado** por `make gerar-indice`. Não edite.

---

## 0. Leia UM exemplo, não os cinco

Escolha pela forma do seu comando. Ler os outros quatro não ensina mais nada:

| Se o comando… | Imite |
|---|---|
| muda status de uma entidade | `commands/lote.py` + `entradas/lote.py` |
| cria movimento e mexe no saldo | `commands/saida.py` |
| exige duas identidades | `commands/descarte.py` |
| resolve algo pendente (2º passo) | `commands/autorizacao.py` |
| cria várias linhas de uma vez | `commands/recebimento.py` |

**Reuse, não recopie:** `_saldo`, `_travar_lote` e `_dados` vivem em
`commands/saida.py` e são importados por `autorizacao.py`, `estorno.py` e
`descarte.py`. Uma segunda implementação de "quanto tem neste lote" é um bug
esperando data.

---

## 1. A forma

```python
# entradas/<dominio>.py — FOLHA
MotivoX = Literal["...", "..."]        # RN-M05: lista FECHADA, por TIPO

class EntradaX(BaseModel):
    alvo_id: str
    motivo: MotivoX
    justificativa: str = Field(min_length=1)   # complemento, nunca substituto

# <dominio>.py — EXECUTÁVEL
async def _aplicar(entrada: Any, ctx: ContextoComando) -> Efeito: ...
async def _etag_de(entrada: Any, ctx: ContextoComando) -> str | None: ...

COMANDO = registrar(Comando(
    nome="movimento_x",                 # = a chave em `ComponentDef.commands`
    requires=("movimento.criar",),      # tupla é CONJUNÇÃO
    schema=EntradaX,
    aplicar=_aplicar,
    idempotent=False,
    confirm=True,
    etag_de=_etag_de,
))
```

### As quatro decisões que o `Comando` obriga

| Campo | Escolha | Consequência |
|---|---|---|
| `requires` | a permissão do **documento 02 §6** | vazio é recusado no registro (ADR-0004). No `CommandDef` não pode ser **mais forte** que aqui — a fraca é a que vale |
| `idempotent` | `False` se repetir **duplica** | `False` torna `Idempotency-Key` obrigatório. Trocar status para o mesmo valor é `True`; criar movimento nunca é |
| `etag_de` | presente = **atualização** | passa a exigir `If-Match`. Ausente = criação. Devolver `None` vira `nao_encontrado`, indistinguível de fora de escopo |
| `confirm` | `True` se irreversível | **não existe componente `confirm_action`** (achado A-05): confirmar é decisão do motor de render diante desta bandeira |

---

## 2. O que o pipeline JÁ faz — não refaça

`commands/pipeline.py` roda, nesta ordem:

```
buscar → AUTORIZAR → exigir chave → validar → replay
       → [ transação: If-Match → aplicar → auditar → gravar chave ]
```

Portanto o seu `_aplicar` **não** precisa: autorizar, validar o corpo, abrir
transação, gravar auditoria, tratar repetição, nem conferir `If-Match`.

Três garantias que vêm de graça e que é fácil estragar por engano:

- **`AUTORIZAR` vem antes de validar.** Erro de schema devolvido a quem não pode
  executar descreveria o formulário de graça a quem não devia saber que existe.
- **A hora é `ctx.agora`, do servidor, uma vez para o comando inteiro** (`RN-M04`).
  Um `datetime.now()` dentro do comando cria uma segunda noção de "agora",
  diferente da que a auditoria registrou.
- **A recusa também vira trilha.** Auditoria que só registra sucesso descreve um
  sistema onde ninguém tentou o que não podia — que é o que se quer investigar.

O que **você** devolve é o `Efeito`, e ele é o conteúdo da trilha (`RN-D01`):
`valor_anterior` e `valor_novo` precisam **reconstruir o que mudou**. Um comando
que devolvesse só "deu certo" produz trilha que não serve para nada.

---

## 3. Armadilhas, em ordem de gravidade

**O saldo NÃO vem de `repos.lote.saldos`.** Aquilo lê a view materializada
`saldo_lote`, e o papel `estoque_app` não tem privilégio de `REFRESH` (achado
A-20): depois da primeira escrita pela aplicação a view fica para trás e nunca se
recupera. Some os movimentos `efetivado` — é o que `_saldo` faz. Dado velho aqui
autoriza vender o que já saiu.

**Trave o lote ANTES de ler o saldo.** `_travar_lote` (`SELECT … FOR UPDATE`).
Sem isso, duas saídas concorrentes leem 10, tiram 8 cada, e o lote fecha em −6:
`RN-M01` não sobrevive a decisão tomada em paralelo sobre a mesma linha.

**Escopo vale na escrita também.** `_dados(ctx)` monta o `ContextoDados` e a
porta intersecta com as unidades do ator (`RN-A01`). Fora de escopo e inexistente
saem pela **mesma** porta, com a mesma mensagem (ADR-0014) — se diferissem,
alguém mapearia o estoque das outras unidades perguntando id por id.

**Permissão não é a regra toda.** A matriz do §6 diz quem *tem acesso*; a tabela
**§4.1** diz quem *faz a transição*, e ela ganha. O Diretor tem
`movimento.descartar` e **não descarta** — papel não é nível, é conjunto. Duas
camadas: `requires` deixa entrar, `transicao_valida` recusa.

**Movimento é append-only.** O papel da aplicação não tem `UPDATE` nem `DELETE`
em `movimento` (migração 0001). A única exceção é a transição de autorização de
controlado, por `GRANT` de coluna + gatilho (migração 0004). Corrigir se faz por
**estorno**, que é `INSERT`.

**Motivo de lista fechada, por tipo** (`RN-M05`). A lista mora no **módulo-folha**
para o componente conseguir lê-la sem alcançar `commands/` — duas listas
divergem. Texto livre é complemento, nunca substituto. Não há lista de motivos em
documento nenhum: derive do enum `MotivoMovimento` e registre em
[ACHADOS](../../../docs/tasks/ACHADOS.md) (é a família do A-19).

**O sinal vem do tipo, nunca do número.** `quantidade > 0` sempre (`CHECK` da
0001). E `estorno` soma junto com `entrada` na view de saldo — por isso só
**saída** se estorna (achado A-38).

---

## 4. Testes obrigatórios — `api/tests/commands/test_<dominio>_comandos.py`

**Contra Postgres real**, e não contra fake: o que se prova aqui — saldo,
imutabilidade, `CHECK` de banco, concorrência — um duble provaria só que o teste
não chamou nada. Copie a fixture `motor` de `test_saida_comandos.py`; ela **pula
sem banco**, e teste que pula é teste que não existe (rode `make db-local && make db-teste`).
A URL vem de `tests/banco.py` — nunca repita o endereço no arquivo de teste.

> Não dá para "resetar" o saldo entre testes: sem `DELETE` em `movimento`, cada
> teste **mede antes e afirma sobre a diferença**. É mais chato e é o único jeito
> honesto de testar um livro-razão.

| O que provar | Como |
|---|---|
| o caminho feliz | o efeito no banco, não só o retorno: linha criada, status mudado, saldo movido |
| **permissão** *(negativo)* | um papel sem a permissão recebe `nao_autorizado` — e **antes** de qualquer erro de schema |
| **escopo** *(negativo)* | Odair no lote da Matriz: `nao_encontrado`, com mensagem **idêntica** à de id inexistente |
| **regra de estado** *(negativo)* | o estado que a regra proíbe é recusado, e o saldo/status **não muda** |
| **enum fechado** *(negativo)* | motivo plausível e fora da lista é recusado |
| **repetição** *(negativo)* | segunda chamada não duplica o efeito |
| **`If-Match` velho** *(negativo)* | alguém mexeu no alvo no meio: `conflito`, sem aplicar |
| trilha | a linha de auditoria tem `valor_anterior` e `valor_novo` que reconstroem o efeito |

**Depois, sabote.** Para cada proteção acima, quebre-a de propósito e confirme o
teste vermelho. *Uma regra que nunca falhou não é evidência de nada.*

A bijeção declarado ↔ executável e a barreira do assistente já são cobertas por
`test_ac1_barreira.py` — não reescreva, mas rode.

---

## 5. Regenerar e fechar

```bash
make gerar-indice            # commands/indice.py e registry/indice.py
make types                   # só se registrou componente junto
make check-api               # a cada iteração; `make check` inteiro uma vez, no fim
```

Se a tarefa também registra componente, a outra metade está em
`componente-novo` — e o `bijecao.test.ts` cobra a view.

Feche pelo passo 7 da `executar-tarefa`: ACs **verificados** marcados, BOARD e
PROGRESSO no mesmo commit.
