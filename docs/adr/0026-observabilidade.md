# ADR-0026 — Observabilidade como porta, com LangFuse do outro lado

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-08 |
| **Escopo** | Ciclo 1 |
| **Relacionado** | [ADR-0013](./0013-suite-de-avaliacao.md) — a suíte que alimenta as métricas |
| **Nota** | Exercitado e conferido em 2026-09-08; três defeitos encontrados e corrigidos — ver "O que foi verificado" |

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

### Instância: a hospedada, não uma local

O LangFuse é consumido em `cloud.langfuse.com`, com chaves no `.env`.

Subir uma instância local foi **tentado e revertido**: exige clickhouse, redis e
minio além do próprio serviço — quatro containers a mais. A promessa de que
`docker compose up` sobe o sistema inteiro vale mais que ter telemetria ligada
por padrão, ainda mais quando o sistema funciona inteiro sem ela.

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

## O que foi verificado, em 2026-09-08

O ramo executou. Chaves reais no `.env`, projeto `estoque-bertoni` na nuvem dos
EUA, uma composição real com `anthropic/claude-haiku-4.5` via OpenRouter, e o
trace buscado **de volta** pela API para conferência — não olhado no painel, que
é fácil de confundir com outro.

O que chegou lá: raiz `agent` `compor-interface`, filhos `generation`
`gerar-composicao` (modelo, 4002/65 tokens, US$ 0,004327) e `guardrail`
`validar-schema` (aceitos e rejeitados com motivo), `user_id` e tags nos três, e
três notas presas ao trace — `schema_valido`, `latencia_ms`,
`ms_ate_primeiro_token`.

### Os três defeitos que só a execução revelou

Estavam escritos, tipados e compilados. Nenhum teste os pegaria.

1. **Região errada, em silêncio.** O código lia só `LANGFUSE_HOST`; o `.env`
   trazia `LANGFUSE_BASE_URL` apontando para os EUA. Sem a variável, o SDK caía
   no padrão da Europa — chave dos EUA contra servidor da Europa não autentica.
2. **`span.update_trace()` não existe no SDK v4.** Era como `user_id` e tags
   eram anexados. Levantava `AttributeError` a cada chamada.
3. **A nota do `schema_valido` não chegava a lugar nenhum** — `create_score`
   sem `trace_id`, depois de o span já ter encerrado. É *a* métrica que decide
   o projeto (PRD §9), e ela caía no vazio.

Os três estavam invisíveis pelo mesmo motivo: o `except Exception` largo que
torna a telemetria não-fatal também a torna silenciosa. O risco aceito abaixo
tinha um preço maior do que o registrado, e ele foi cobrado.

## O que continua não verificado

**A duração das observações não é a latência real.** O observador é chamado
depois que a composição termina, e o SDK v4 não aceita `start_time`/`end_time`
arbitrários — então a árvore nasce com duração perto de zero. Preencher esses
milissegundos com número inventado seria a falha da POC v1 de novo, então a
latência real viaja como **nota numérica**, que o painel plota em série, e um
metadado marca a árvore como artificial.

**Fecha assim:** instrumentação ao vivo, envolvendo o pipeline em `app.py` —
tarefa **T-043**.

## Conformidade

- Sem `LANGFUSE_*`, `criar()` devolve `None` e o sistema usa o nulo.
- Nenhuma chamada ao observador levanta para fora.
- `make eval` recusa rodar com o adaptador mock.
- ✅ Execução real conferida em 2026-09-08, com o trace buscado de volta pela API.
- ✅ Duração real de span na rota do assistente (T-043, 2026-09-14): `ao_vivo`
  envolve o trabalho, testado com cliente falso e relógio real. A eval segue
  pós-fato, marcada como artificial. **Não conferido contra a nuvem.**

## Referências
- [PRD-001 §9](../prd/PRD-001-ciclo-1.md) · [ADR-0013](./0013-suite-de-avaliacao.md)
