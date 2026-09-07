# T-038 — Gestão de usuários

| | |
|---|---|
| **Onda** | W5 |
| **Trilha** | D |
| **Tamanho** | M |
| **Depende de** | T-037, T-031 |
| **ADRs** | [0019](../adr/0019-autenticacao-e-cadastro.md), [0011](../adr/0011-teto-de-catalogo.md) |
| **Regras** | RN-A01, RN-A06, RN-D01 |

## Objetivo

Atribuir papel e unidades a quem se cadastrou. **Tela com rota, deliberadamente
fora do catálogo do assistente.**

## Arquivos de propriedade exclusiva

```
api/src/estoque/server/rotas/usuarios.py   api/tests/server/test_usuarios.py
web/src/app/telas/usuarios.tsx
```

## Escopo

### Faz
- `GET /api/usuarios` e `PATCH /api/usuarios/{id}` — `requires: usuario.gerenciar`.
- Atribuir papel e unidades; ativar e desativar.
- Toda mudança auditada com valor anterior e novo (`RN-D01`).

### Não faz
**Não registra componente.** Administrar usuário não é coisa que se peça ao
assistente — é raro, sensível e não se beneficia de composição. Fora do catálogo,
não consome a folga de 3 do teto (ADR-0011).

Isso é a aplicação prática de §11.2 da arquitetura: *não deixe o assistente ser o
app.*

## Critérios de aceite

- [ ] **AC-1** Só Marco (Diretor) tem `usuario.gerenciar`. Todos os outros são
      recusados **no servidor**, com requisição direta. *(negativo)*
- [ ] **AC-2** Usuário é **desativado, nunca excluído**; a trilha continua
      resolvendo o nome. *(negativo — `RN-A06`)*
- [ ] **AC-3** Atribuir papel gera auditoria com valor anterior e novo.
- [ ] **AC-4** Ninguém consegue atribuir a si próprio um papel. *(negativo —
      separação de funções)*
- [ ] **AC-5** Contagem de catálogo **inalterada: 22**. Nenhum componente novo.
- [ ] **AC-6** Desativar usuário derruba a sessão dele imediatamente.

## Armadilhas

AC-4 é o buraco óbvio: quem gerencia usuários pode se promover. Marco já é Diretor,
então o risco é teórico aqui — mas a regra precisa existir antes de haver um papel
intermediário com `usuario.gerenciar`.
