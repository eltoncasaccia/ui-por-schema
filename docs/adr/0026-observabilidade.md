# ADR-0026 — Observabilidade como porta, com LangFuse do outro lado

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-08 |
| **Escopo** | Ciclo 1 |
| **Relacionado** | [ADR-0013](./0013-suite-de-avaliacao.md) — a suíte que alimenta as métricas |

## Contexto

O projeto precisa medir: taxa de schema válido, composição correta, latência,
tokens e custo (PRD §9). Havia o `Trace` interno, que alimenta o painel de
Execution Trace, mas nada persistia entre execuções — cada número era um
retrato, nunca uma série.

## Decisão

> **Observabilidade é uma porta (`Observador`) com implementação nula por
> padrão. LangFuse é uma implementação, não uma dependência.**

O `Trace` deste projeto continua sendo o conceito central — é ele que alimenta
o painel pelo qual a POC é julgada. A ferramenta externa **observa** esse
conceito; não o substitui. Senão a própria evidência do projeto passaria a
depender de um serviço de terceiro estar no ar.

### A assimetria com o adaptador de modelo, e por quê

| Sem chave | Comportamento |
|---|---|
| Modelo | **Levanta.** O sistema não responde |
| Observador | **Nulo.** O sistema segue |

Não é inconsistência: **telemetria ausente degrada o diagnóstico; modelo
ausente falsifica o resultado.** Foi assim que a v1 publicou números de um
parser simulado sem perceber.

### O que é registrado

prompt e schema (reproduzir uma composição ruim) · tokens · custo relatado pelo
provedor · modo pedido e modo efetivo · papel do ator · aceitos e rejeitados ·
nota `schema_valido` por execução.

**O papel importa:** a mesma pergunta compõe diferente por papel, e uma métrica
agregada sem ele mistura experimentos distintos.

### O que NÃO é registrado

Nenhuma linha de dado do estoque. O prompt já não contém dados
([ADR-0012](./0012-injecao-de-prompt-via-dado.md)) e o viewmodel não passa por
aqui. Mandar dado de cliente para serviço de terceiro seria decisão de outra
ordem, e exigiria ADR próprio.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Chamar o SDK do LangFuse direto no endpoint | Acopla a evidência do projeto a um serviço externo, e torna o teste dependente de rede |
| Só OpenTelemetry | Ótimo para latência e erro; não tem o vocabulário de geração, custo por modelo e **nota de avaliação**, que é o que este projeto precisa |
| Guardar tudo na tabela de auditoria | Auditoria é registro regulatório e imutável. Métrica de experimento é outra coisa, com outro ciclo de vida — e misturar as duas polui a trilha que a ANVISA leria |

## Consequências

**Positivas**
- Série histórica de taxa de schema válido, que é a pergunta do projeto.
- Custo por pergunta observável, e vindo do provedor.
- `make eval` publica notas por modo, então a comparação `restrito` × `livre`
  vira gráfico em vez de tabela num relatório.

**Negativas**
- Uma dependência opcional a mais, e um caminho de código que quase nunca roda
  em teste (o nulo é o padrão).
- Dado sai da máquina quando as chaves existem. É opt-in, mas precisa estar
  claro para quem for rodar.

**Riscos aceitos**
- O observador engole exceção de propósito. Falha de telemetria não pode
  derrubar a requisição que ela observa — mas isso significa que telemetria
  quebrada some em silêncio, e só o log denuncia.

## Conformidade

- Sem `LANGFUSE_*`, `criar()` devolve `None` e o sistema usa o nulo.
- Nenhuma chamada ao observador levanta para fora.
- `make eval` recusa rodar com o adaptador mock.

## Referências
- [PRD-001 §9](../prd/PRD-001-ciclo-1.md) · [ADR-0013](./0013-suite-de-avaliacao.md)
