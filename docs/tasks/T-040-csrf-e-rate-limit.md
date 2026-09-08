# T-040 — CSRF e rate limit

| | |
|---|---|
| **Onda** | W1 — Núcleo |
| **Trilha** | B |
| **Tamanho** | M |
| **Depende de** | T-037 |
| **Origem** | [A-002](../relatorios/A-002-auditoria-de-execucao.md), achados A-02 e A-03 |
| **ADRs** | [0019](../adr/0019-autenticacao-e-cadastro.md) |
| **Requisitos** | CS-06 · T-037 AC-2, AC-3, AC-8 |
| **Estado** | ✅ **concluída** em 2026-09-08 |

## Objetivo

Implementar a proteção que **três documentos já dizem existir** e que não existe.

## O que existe hoje

| Peça | Estado |
|---|---|
| Cookie `csrf` criado no login | ✅ |
| Cliente envia `X-CSRF-Token` em toda escrita | ✅ |
| **Servidor valida o token** | ❌ **nunca lê o header** |
| **Servidor confere `Origin`** | ❌ |
| **Rate limit no login** | ❌ `auth/` está vazio |

A metade visível foi construída; a metade que protege, não. `SameSite=Lax`
continua valendo e cobre a maior parte dos casos — o que falta é a segunda
camada, que o ADR-0019 declara.

## Arquivos de propriedade exclusiva

```
api/src/estoque/auth/csrf.py     api/src/estoque/auth/limite.py
api/tests/server/test_csrf.py    api/tests/auth/test_limite.py
```

## Escopo

### Faz
- Middleware que exige `X-CSRF-Token` igual ao cookie em todo `POST`/`PATCH`,
  **exceto** `/api/auth/entrar` e `/api/auth/registrar` (não há sessão ainda).
- Verificação de `Origin` contra a origem configurada.
- Rate limit no login: por conta **e** por IP, com resposta `limite` auditada.

### Não faz
Rate limit no endpoint do assistente — é `CS-06` e cabe aqui, mas o limite por
custo de token é decisão separada.

## Critérios de aceite

> **Verificado por** `tests/auth/test_csrf.py` e `tests/auth/test_limite.py`
> (27 testes), mais execução contra o sistema no ar. Cada AC negativo foi
> conferido provocando a falha, não só observando o caminho feliz.

- [x] **AC-1** Escrita sem `X-CSRF-Token` é recusada. *(negativo — T-037 AC-2)*
      → *sem header e sem cookie, os dois recusados · ponta a ponta: `token de origem inválido`*
- [x] **AC-2** Escrita com token diferente do cookie é recusada. *(negativo)*
      → *token ≠ cookie recusado; comparação por `compare_digest`*
- [x] **AC-3** Escrita com `Origin` de outro domínio é recusada. *(negativo — T-037 AC-3)*
      → *origem diferente recusada, inclusive esquema/porta/host quase iguais*
- [x] **AC-4** Login e cadastro continuam funcionando sem token — não há sessão
      para tirá-lo de lá ainda.
      → *`/auth/entrar` e `/auth/registrar` passam sem token — ponta a ponta: Ivo entrou*
- [x] **AC-5** N tentativas de senha errada na mesma conta disparam `limite`.
      *(negativo — T-037 AC-8)*
      → *5 tentativas erradas → `limite`; outra conta segue entrando*
- [x] **AC-6** O mesmo limite vale por IP, para conta inexistente — senão o
      atacante enumera contas testando uma senha em muitas. *(negativo)*
      → *3 contas distintas do mesmo IP estouram o limite de IP sem nenhuma estourar o de conta*
- [x] **AC-7** Toda recusa por limite é auditada.
      → *`login_bloqueado` na trilha, gravado ANTES do raise; bloqueado não gasta hash*
- [x] **AC-8** O contador de tentativas zera após janela, e o teste prova o
      caminho de reabertura — senão um erro de digitação bloqueia para sempre.
      → *janela deslizante reabre sozinha; login certo limpa a conta*

## Armadilhas

AC-6 é o que a maioria esquece: limite só por conta deixa passar o ataque que
testa `senha123` em mil contas. E AC-8 evita transformar a proteção em negação
de serviço contra o próprio usuário.
