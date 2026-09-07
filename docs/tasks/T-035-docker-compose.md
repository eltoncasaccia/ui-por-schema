# T-035 — Docker Compose, Makefile e ambiente

| | |
|---|---|
| **Onda** | W0 — Fundação · **primeira tarefa do projeto** |
| **Trilha** | E |
| **Tamanho** | M |
| **Depende de** | — |
| **Bloqueia** | T-001 |
| **ADRs** | [0016](../adr/0016-api-python-cliente-typescript.md), [0018](../adr/0018-postgres-em-container.md) |

## Objetivo

`git clone` + `docker compose up` = sistema no ar. **É a primeira impressão de
quem abre o repositório**, e por isso é a primeira tarefa.

## Arquivos de propriedade exclusiva

```
docker-compose.yml   Makefile   .env.example   .gitignore
.dockerignore        README.md  LICENSE
.github/workflows/ci.yml
```

## Escopo

### Faz

| Serviço | Imagem | Porta |
|---|---|---|
| `db` | `postgres:17-alpine` | 5432 (só rede interna) |
| `api` | build `api/` | 8000 |
| `web` | build `web/` | 5173 |

- `healthcheck` no `db`; `api` só sobe com o banco pronto.
- Volume nomeado para os dados; `make reset` apaga.
- `Makefile`: `up`, `down`, `logs`, `migrate`, `seed`, `test`, `lint`, `typecheck`,
  `arch`, `eval`, `reset`.
- `.env.example` versionado com **todas** as variáveis, sem valor real.
- `README.md` na raiz: o que é, a tese, como rodar, o diagrama, link para os ADRs,
  e o aviso de que **a Bertoni é uma empresa fictícia**.

### Não faz
Código de aplicação. Os `Dockerfile` de `api/` e `web/` são de T-001.

## Critérios de aceite

- [ ] **AC-1** Em máquina limpa, `git clone` + `docker compose up` sobe os três
      serviços e a interface responde. **Sem passo manual.**
- [ ] **AC-2** `make seed` popula o banco e é idempotente — rodar duas vezes não
      duplica.
- [ ] **AC-3** `.env` está no `.gitignore`; `.env.example` está versionado; nenhum
      segredo real no repositório. *(negativo — verificado em CI)*
- [ ] **AC-4** A porta do Postgres **não** é publicada no host por padrão.
      *(negativo — banco não é serviço público)*
- [ ] **AC-5** CI roda `lint`, `typecheck`, `test` e `arch` dos dois lados.
- [ ] **AC-6** O README da raiz responde "o que é isto" em menos de 30 segundos de
      leitura, com o diagrama de dois processos.
- [ ] **AC-7** `docker compose down -v && docker compose up` reconstrói tudo do
      zero, sem intervenção.

## Armadilhas

AC-1 é o critério que mais vale neste projeto. Um README com sete passos de setup
manual afunda a primeira impressão, por melhor que seja o código.
