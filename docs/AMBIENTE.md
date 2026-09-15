# Ambiente — o porquê de cada `make`, e o que já quebrou

O [`CLAUDE.md`](../CLAUDE.md) §3 tem os comandos. Este documento tem as **razões**
— leia quando o ambiente brigar, ou antes de mudar alguma coisa aqui. Cada seção
existe porque a falta dela já custou caro.

---

## A armadilha do `make migrate`

`make migrate` roda com o `docker-compose.yml` sozinho, e isso **recria o
container do banco sem o mapeamento de porta**. Depois de migrar, rode
`make db-local` de novo.

Sem a porta publicada em `localhost:15432`, nove testes de imutabilidade **pulam**
— e teste que pula é teste que não existe. A suíte fica verde provando menos do
que você acha que provou.

---

## Dois databases no mesmo Postgres: `estoque` e `estoque_teste`

| Database | Quem grava | Criado por |
|---|---|---|
| `estoque` | você, pelo `make up` | o boot da API (migração e seed) |
| `estoque_teste` | **só** os testes | `make db-teste` |

Até a T-052, os testes gravavam no `estoque`. `movimento` e `auditoria` são
append-only, então não há como apagar só o que um teste deixou. Em 2026-09-14 eram
262 usuários de teste contra 8 reais, visíveis na tela `/usuarios`, e a única
saída foi `make reset`, que levou junto as telas salvas. É o achado **A-44**.

Três coisas sustentam a separação:

- os endereços dos testes moram em `api/tests/banco.py`, e o padrão é
  `estoque_teste`;
- o `conftest.py` põe `DATABASE_URL` no banco de teste quando ninguém a declarou.
  O app sob teste lê dali; sem isso, a fixture gravaria num banco e o servidor
  leria de outro;
- apontar qualquer um deles para o banco de desenvolvimento **para a suíte antes
  de coletar**. Não pula: pular é o que o CI reprova, e o que esconderia a volta do
  problema. Isso vale também para uma `DATABASE_URL` exportada do `.env`, que traz
  o mesmo banco como `db:5432`.

`make db-teste` roda `uv` local contra `localhost:15432`, e **não**
`docker compose run`, que recriaria o container do banco sem a porta (a armadilha
acima). É idempotente: rode de novo a cada migração nova.

O CI não usa nada disso. Ele tem Postgres efêmero e declara as três variáveis.

---

## Dois papéis de banco, e a diferença é regulatória

| Variável | Papel | Quem usa |
|---|---|---|
| `DATABASE_URL` | `estoque_app` — **sem** `UPDATE`/`DELETE` em `movimento` e `auditoria` | a aplicação |
| `DATABASE_URL_ADMIN` | o dono do schema | **só** a migração e o seed |

O dono ignora `REVOKE`. Com ele na aplicação, `RN-M02` (movimento é imutável) e
`RN-D02` valiam **só nos testes** — o sistema que roda aceitaria o `UPDATE` que a
regra proíbe. É o achado **A-27**, e é por isso que os dois papéis existem.

---

## Por que `make env` existe

Acrescentar variável ao `.env.example` **não** atualiza o `.env` de quem já
rodou. A variável ausente cai num padrão que funciona — **e é por funcionar que
passa despercebida.**

Foi exatamente assim que o LangFuse ficou apontando para a região errada por
semanas: nada quebrou, nada avisou, e o dado foi para o lugar errado.

`make env` compara os dois arquivos e aponta a diferença; `make env-completar`
acrescenta as que faltam ([ADR-0027](adr/0027-ambiente-verificado.md)).

---

## Por que os índices são gerados

`registry/indice.py`, `commands/indice.py` e `views/indice.ts` são os **únicos
arquivos que toda tarefa de componente precisaria editar**. 22 componentes
registrados à mão em dois arquivos seriam 44 conflitos de merge garantidos.

O `commands/indice.py` entrou pelo mesmo motivo e pelo achado **A-15**: as
**cinco** tarefas de escrita da W4 precisariam da mesma linha de import nele.

`make arch` falha se qualquer um estiver desatualizado — a geração é verificada,
não confiada.

---

## Derrubar processo preso

```bash
docker compose ps                 # o que está de pé
docker compose down               # encerra tudo
docker compose down -v            # ...e apaga os volumes
lsof -ti:15432 | xargs kill       # se a porta ficou órfã
```
