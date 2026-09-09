# Architecture Decision Records

Decisões técnicas do projeto, em formato [MADR](https://adr.github.io/madr/)
adaptado. **Os ADRs são normativos para decisões técnicas** — o PRD referencia, não
substitui.

Um ADR nunca é editado depois de aceito. Mudou a decisão? Escreve-se um novo, e o
antigo recebe `Status: Substituído por ADR-XXXX`. O histórico é o valor.

| ADR | Decisão | Escopo | Status |
|---|---|---|---|
| [0001](./0001-ui-por-schema.md) | Compor a interface por schema, nunca por código gerado | Fundacional | Aceito |
| [0002](./0002-plano-render-plano-escrita.md) | Separar plano de render e plano de escrita | Fundacional | Aceito |
| [0003](./0003-catalogo-por-ator.md) | Servir o catálogo filtrado por ator, no servidor | Fundacional | Aceito |
| [0004](./0004-autorizacao-em-tres-momentos.md) | Autorizar em três momentos, e confiar em apenas um | Fundacional | Aceito |
| [0005](./0005-l2-leitura-l1-escrita.md) | L2 para leitura, L1 para escrita | Fundacional | Aceito |
| [0006](./0006-contrato-unico-de-componente.md) | ~~Uma declaração produz tudo sobre o componente~~ | Fundacional | **Substituído por 0017** |
| [0007](./0007-camadas-e-arch-check.md) | Camadas verificadas por script, não por convenção | Fundacional | Aceito, emendado por 0016 |
| [0008](./0008-tanstack-query.md) | TanStack Query para estado de servidor | Ciclo 1 | Aceito |
| [0009](./0009-identidade-de-view.md) | Identidade de view derivada do schema | Ciclo 1 | Aceito, emendado por 0021 |
| [0010](./0010-corte-de-escopo-ciclo-1.md) | Contagem, ajuste e transferência fora do ciclo 1 | Ciclo 1 | Aceito |
| [0011](./0011-teto-de-catalogo.md) | Teto de 25 componentes, sem recuperação de catálogo | Ciclo 1 | Aceito |
| [0012](./0012-injecao-de-prompt-via-dado.md) | Tratar dado do banco como conteúdo hostil no prompt | Ciclo 1 | Aceito, risco residual |
| [0013](./0013-suite-de-avaliacao.md) | Suíte de avaliação como rede de regressão | Ciclo 1 | Aceito |
| [0014](./0014-erros-que-nao-vazam.md) | Negativa de escopo vs. negativa de registro | Fundacional | Aceito |
| [0015](./0015-assistente-exige-conexao.md) | Assistente exige conexão; off-line adiado | Ciclo 1 | Aceito |

| [0016](./0016-api-python-cliente-typescript.md) | API Python e cliente TypeScript, processos separados | Fundacional | Aceito |
| [0017](./0017-registry-servidor-views-cliente.md) | Registry no servidor, views no cliente, ligados por id | Fundacional | Aceito — **substitui 0006** |
| [0018](./0018-postgres-em-container.md) | Postgres em container, acessado só pela API | Ciclo 1 | Aceito |
| [0019](./0019-autenticacao-e-cadastro.md) | Autenticação por sessão, cadastro sem papel | Ciclo 1 | Aceito |
| [0020](./0020-select-no-servidor.md) | `select` roda no servidor; só o viewmodel cruza a rede | Fundacional | Aceito |
| [0021](./0021-viewkey-e-viewid.md) | `viewKey` interna, `viewId` público e revogável | Ciclo 1 | Aceito |
| [0022](./0022-status-registrado-e-efetivo.md) | Status registrado vs. status efetivo | Fundacional | Aceito |
| [0023](./0023-provedor-de-modelo.md) | OpenRouter como provedor, atrás do adaptador | Ciclo 1 | Aceito |
| [0024](./0024-decodificacao-restrita.md) | Decodificação restrita, e o que ela faz com a métrica | Ciclo 1 | Aceito |
| [0025](./0025-agnosticismo-de-provedor.md) | Provedor trocável por configuração; três modos de saída | Fundacional | Aceito — **emenda 0023** |
| [0026](./0026-observabilidade.md) | Observabilidade como porta, com LangFuse do outro lado | Ciclo 1 | Aceito — **não verificado** |
| [0027](./0027-ambiente-verificado.md) | Conferir o `.env` contra o exemplo, por comando | Ferramental | Aceito |
| [0028](./0028-processo-de-decisao.md) | Pergunta curta antes; ADR depois | Processo | Aceito |
| [0029](./0029-relatorio-como-componente.md) | Relatório é componente parametrizado | Ciclo 1 | Aceito |
| [0030](./0030-layout-de-diretorios.md) | ~~Diretórios por dependência permitida~~ | Fundacional | **Substituído por 0031** |
| [0031](./0031-ports-and-adapters.md) | Ports & Adapters, com a regra de dependência no CI | Fundacional | Aceito — **substitui 0030**, emenda 0007 |
| [0032](./0032-borda-http-por-router.md) | A borda HTTP quebrada por área, com `independence` entre os routers | Ciclo 1 | Aceito — detalha 0031 |

## Origem das decisões

Os ADRs 0001 a 0015 vieram da análise inicial. Os ADRs **0016 a 0018** vieram da
mudança de arquitetura (API Python, Postgres em Docker) e o **0019** de escopo novo.

Os ADRs **0020, 0021 e 0022** têm outra origem, e vale registrar: nasceram da
[auditoria A-001](../relatorios/A-001-auditoria-pre-migracao.md), que encontrou
contradições nos documentos antes de qualquer linha de código ser escrita —
`select` no cliente vazando dados, `viewKey` prometendo revogação impossível, e
status derivado sendo armazenado.

[Template para novos ADRs](./0000-template.md)
