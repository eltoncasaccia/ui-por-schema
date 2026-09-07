# ADR-0009 — Derivar identidade de view do schema, com id gerado no servidor

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-06 |
| **Escopo** | Ciclo 1 |
| **Emendado por** | [ADR-0021](./0021-viewkey-e-viewid.md) — `viewKey` (hash, interno) e `viewId` (opaco, público, revogável) são identificadores distintos |

> **Emenda.** A auditoria [A-001](../relatorios/A-001-auditoria-pre-migracao.md)
> mostrou que este ADR afirmava três coisas incompatíveis: id gerado no servidor,
> chave por hash de conteúdo, e revogação. Hash de conteúdo não é revogável. O
> [ADR-0021](./0021-viewkey-e-viewid.md) separa os dois identificadores. O
> raciocínio abaixo continua válido; onde se lê "a `viewKey` é o endereço", leia-se
> `viewId`.

## Contexto

Na v1 favoritar duplicava, e a estrela voltava apagada ao reabrir a tela. A causa
não era um bug de UI: o favorito estava chaveado no id da **composição**, criado a
cada renderização. Reabrir a mesma tela gerava id novo.

O problema é geral. Quando a UI é composta dinamicamente, "a mesma tela" perde o id
óbvio. Tudo que precise lembrar de uma tela — favorito, histórico, botão voltar,
telemetria, permissão, auditoria — precisa de identidade explícita. Apps por rota
ganham isso de graça na URL.

Segunda questão, ligada: como o schema vira URL? Serializado no cliente, ou id
gerado no servidor?

## Decisão

> **Uma view é a mesma view quando o schema é o mesmo.** A chave é `viewKey`,
> derivada por hash do schema canonicalizado — nunca da execução.
>
> **O endereço público é um id gerado no servidor**, não o schema serializado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Id por execução | O bug da v1. Nenhuma memória de tela sobrevive a um reload |
| Chavear pelo prompt do usuário | Prompt é não-determinístico: mesma frase, composição diferente |
| Schema serializado na URL (base64) | Mais simples e sem round trip, mas: URL gigante, sem revogação, sem auditoria, e o schema vira segredo em trânsito colável em qualquer lugar |

O argumento que decidiu a favor do servidor: **`RN-D05` obriga auditar a consulta
de qualquer forma.** Se o registro tem que existir por conformidade, ele já é o
endereço. A auditoria paga o round trip.

## Consequências

**Positivas**
- Favorito, histórico e voltar funcionam.
- Revogação existe: um id pode ser invalidado.
- Fundação pronta para compartilhamento no ciclo 2, sem retrabalho.

**Negativas**
- Round trip a mais antes de a URL existir.
- Canonicalização do schema é sutil: ordem de chaves, ordem de blocos e defaults
  precisam de regra determinística, ou a mesma view gera chaves diferentes.

**Riscos aceitos**
- `viewKey` aponta para uma view, **não concede acesso**. Quem abrir carrega sob a
  própria permissão, com o schema revalidado contra o próprio catálogo. Sem isso,
  endereço vira canal de escalação de privilégio.

## Conformidade

- Teste: o mesmo schema com chaves em ordem diferente produz a mesma `viewKey`.
- Teste: abrir uma `viewKey` criada por Marco, autenticado como Odair, carrega sob
  a permissão de Odair — ou nega. Nunca devolve dado de Marco.

## Referências
- [Arquitetura v2 §8 e §11.3](../03-arquitetura-v2.md)
