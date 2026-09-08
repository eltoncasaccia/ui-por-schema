# ADR-0019 — Autenticação por sessão, cadastro sem papel

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Ciclo 1 |
| **Regras** | RN-A01, RN-A03, RN-A06, RN-D01 · corrige achado [A-02](../relatorios/A-001-auditoria-pre-migracao.md) |
| **Implementado** | CSRF e rate limit entregues em [T-040](../tasks/T-040-csrf-e-rate-limit.md) — ficaram por fazer na primeira passada, ver [A-002](../relatorios/A-002-auditoria-de-execucao.md) |

## Contexto

O ciclo 1 precisa de identidade real: sem `Ator`, nada em ADR-0003, ADR-0004 ou
`RN-D01` funciona. Foi decidido acrescentar cadastro de usuário com senha, para
que log e rastreabilidade apontem para pessoas.

Isso cria um conflito com o domínio. Este é um distribuidor farmacêutico com
papéis regulados: se qualquer pessoa se cadastra e **escolhe o próprio papel**,
`RN-R02` (liberação privativa do RT) e `CA-04` (dupla identificação) viram enfeite.
Cadastro livre seria escalação de privilégio por formulário.

## Decisão

> **Cadastro cria usuário sem papel e sem unidade — zero permissões, não vê nada.
> Papel e unidades são atribuídos por quem tem `usuario.gerenciar`, com auditoria.**

| Aspecto | Decisão |
|---|---|
| Senha | **argon2id**. Nunca SHA, nunca MD5, nunca bcrypt novo |
| Sessão | Cookie `httpOnly` + `Secure` + `SameSite=Lax`, sessão no servidor |
| **Proibido** | JWT em `localStorage` — XSS vira roubo de sessão permanente |
| **CSRF** | `SameSite=Lax` **mais** token de dupla submissão em toda escrita, mais verificação de `Origin` |
| Brute force | Rate limit por conta e por IP no login, reusando a infra de `CS-06` |
| Enumeração | Mensagem e tempo de resposta idênticos para usuário inexistente e senha errada |
| Reset de senha | **Fora de escopo, declarado.** Melhor ausente que malfeito |
| Desativação | `RN-A06`: usuário é desativado, nunca excluído |

### CSRF é achado de auditoria, não detalhe

`httpOnly` protege contra roubo de cookie por XSS. **Não protege contra CSRF.**
Sem token, `POST /lotes/:id/liberacao` fica disparável por site de terceiro
enquanto Helena estiver logada — e a requisição chega com a sessão válida dela.

### Enumeração de usuário é o ADR-0014 aplicado ao login

"Usuário não existe" e "senha errada" precisam ser indistinguíveis — **inclusive
no tempo de resposta**. Verificar o hash mesmo quando o usuário não existe, para
não vazar por temporização. É a mesma regra que já vale para registro fora de
escopo.

### Usuários demo

A tela de login oferece entrada direta como Cleide, Helena, Ivo, Odair, Marco,
Rafael ou Sandra, rotulada como demonstração. Quem abre o projeto experimenta o
modelo de permissão em segundos — que é o que este projeto tem de mais
demonstrável.

Só existe quando `MODO_DEMO=true`. **Em qualquer outro modo o atalho não é
registrado como rota** — não é escondido na interface, não existe no servidor.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Cadastro escolhendo o papel | Escalação de privilégio por formulário. Destrói `CA-04` e `RN-R02` |
| Só usuários semeados, sem cadastro | Mais seguro e menos demonstrável. O pedido de cadastro é legítimo |
| OAuth / provedor externo | Escopo inventado, e nenhum papel do domínio vem de provedor externo |
| JWT sem estado | Sem revogação. `RN-A06` exige desativar usuário com efeito imediato |

## Consequências

**Positivas**
- Autoria real em toda a trilha de auditoria.
- Cadastro existe sem abrir buraco de permissão.
- A tela de gestão de usuário exercita `usuario.gerenciar`, que estava declarada e
  sem uso (achado A-06).

**Negativas**
- Recém-cadastrado vê uma tela vazia até alguém lhe dar papel. É o comportamento
  correto e é uma experiência ruim — mitigada por mensagem explícita, não por
  permissão temporária.
- Sessão com estado exige armazenamento e limpeza.

**Riscos aceitos**
- `MODO_DEMO` é um caminho de autenticação alternativo. Risco contido por não
  existir a rota fora do modo demo, e por teste que afirma a ausência.

## Conformidade

- Teste: `POST /auth/registrar` produz usuário com `papel = None` e `unidades = []`.
- Teste: usuário sem papel recebe catálogo **vazio** e nenhum `load` autorizado.
- Teste: escrita sem token CSRF é recusada. *(negativo)* ✅
- Teste: escrita com token divergente do cookie é recusada. *(negativo)* ✅
- Teste: N tentativas de senha errada disparam `limite`, por conta **e** por IP.
  *(negativo)* ✅ — limite só por conta deixaria passar o ataque que testa uma
  senha em mil contas
- Teste: login com usuário inexistente e com senha errada devolvem corpo idêntico,
  com diferença de tempo abaixo do limiar. *(negativo)*
- Teste: com `MODO_DEMO=false`, a rota de entrada demo devolve 404. *(negativo)*
- Nenhuma senha, hash ou cookie em log ou trilha de auditoria.

## Referências
- ADR-0004 · [ADR-0014](./0014-erros-que-nao-vazam.md) · [A-001 achado A-02](../relatorios/A-001-auditoria-pre-migracao.md)
