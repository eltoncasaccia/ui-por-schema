# T-037 — Autenticação, sessão e CSRF

| | |
|---|---|
| **Onda** | W1 |
| **Trilha** | B |
| **Tamanho** | **G** |
| **Depende de** | T-004, T-036 |
| **Bloqueia** | T-011, T-038 |
| **ADRs** | [0019](../adr/0019-autenticacao-e-cadastro.md), [0014](../adr/0014-erros-que-nao-vazam.md) |
| **Regras** | RN-A03, RN-A06, RN-D01 |
| **Requisitos** | CS-06 · achado A-02 |

## Objetivo

Identidade real, sem abrir buraco de permissão. É o que faz `RN-D01` (autoria na
auditoria) deixar de ser hipotético.

## Arquivos de propriedade exclusiva

```
api/src/estoque/auth/**   api/tests/auth/**
web/src/app/login.tsx     web/src/app/registrar.tsx
```

## Escopo

### Faz
- `POST /api/auth/registrar` → usuário com `papel=None`, `unidades=∅`.
- `POST /api/auth/entrar` → sessão em cookie `httpOnly`+`Secure`+`SameSite=Lax`.
- `POST /api/auth/sair` → invalida a sessão no servidor.
- Senha com **argon2id**.
- **CSRF**: token de dupla submissão em toda escrita + `Origin` conferido.
- Rate limit por conta e por IP no login.
- Resposta e **tempo** uniformes para usuário inexistente e senha errada.
- Entrada demo pelas sete personas, **só** com `MODO_DEMO=true`.

### Não faz
Atribuir papel (T-038). Reset de senha — **fora de escopo, declarado**.

## Critérios de aceite

- [ ] **AC-1** Recém-cadastrado tem `papel=None`, catálogo **vazio** e nenhum `load`
      autorizado. *(negativo — ADR-0019, não há escalação por formulário)*
- [ ] **AC-2** Escrita sem token CSRF é recusada. *(negativo — achado A-02)*
- [ ] **AC-3** Escrita com `Origin` de outro domínio é recusada. *(negativo)*
- [ ] **AC-4** Login com usuário inexistente e com senha errada devolvem corpo
      **idêntico**, com diferença de tempo abaixo do limiar. *(negativo — ADR-0014
      aplicado ao login)*
- [ ] **AC-5** Senha nunca aparece em log, em auditoria ou em resposta. *(negativo)*
- [ ] **AC-6** Usuário desativado perde acesso imediatamente, com a sessão ainda
      válida. *(negativo — `RN-A06`; é o que JWT sem estado não daria)*
- [ ] **AC-7** Com `MODO_DEMO=false`, a rota de entrada demo devolve **404** — não
      403, não escondida na interface: **não registrada**. *(negativo)*
- [ ] **AC-8** Rate limit no login dispara e é auditado.
- [ ] **AC-9** Hash é argon2id com parâmetros explícitos e versionados.

## Armadilhas

AC-4 quebra por temporização: se o servidor não verificar hash quando o usuário não
existe, a resposta volta mais rápido e enumera contas. Verifique um hash falso.
