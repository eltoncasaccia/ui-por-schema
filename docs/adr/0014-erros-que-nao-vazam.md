# ADR-0014 — Distinguir negativa de escopo declarado de negativa de registro

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Fundacional |

## Contexto

Há um conflito real entre dois objetivos, e a arquitetura v2 o registrou sem
resolver:

- `RN-A07`: mensagem de erro por falta de permissão **não revela a existência nem o
  conteúdo** do registro negado.
- Erro útil ao modelo: o `NotFoundError` da v1 listava os ids disponíveis para o
  modelo se recuperar sozinho — o que **vaza existência de registro**.

E há um segundo caso, aparentemente contraditório: a arquitetura diz que Odair
pedindo Ribeirão Preto *"não retorna vazio, retorna negado"* (`CA-06`). Negar
explicitamente parece violar `RN-A07`.

## Decisão

> **Escopo declarado nega explicitamente. Registro individual nega de forma
> indistinguível de inexistência.**

| Situação | Resposta | Porquê |
|---|---|---|
| Odair pede a **unidade** Ribeirão Preto | `nao_autorizado` — negativa explícita | A existência da unidade não é segredo: é a própria empresa dele. Retornar vazio ensinaria que Ribeirão não tem estoque, o que é **falso e pior** |
| Odair pede o **lote L-8842**, que está em Ribeirão | `nao_encontrado` — idêntico a inexistente | Distinguir "existe mas você não pode" de "não existe" é um oráculo de enumeração de registros |
| Qualquer erro | Nunca lista ids disponíveis | Correção direta do vazamento da v1 |

A regra separadora: **o que o ator já sabe que existe** (unidades, papéis, tipos de
movimento) pode ser negado por nome. **O que ele descobriria pela resposta**
(registros individuais) não.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Sempre `nao_encontrado` | Vazio silencioso ensina fato falso ao usuário e ao modelo. Pior para operação e para confiança |
| Sempre `nao_autorizado` | Vira oráculo: iterar ids revela quais existem |
| Mensagem diferente por papel | Complexidade sem ganho; a diferença é o que vaza |

## Consequências

**Positivas**
- Resolve um conflito que ficaria como bug de segurança descoberto tarde.
- Dá regra clara para quem escreve `load` novo, em vez de julgamento caso a caso.

**Negativas**
- Depuração fica mais difícil: `nao_encontrado` legítimo e negado são iguais na
  resposta. Mitigação: o **log do servidor** distingue os dois; a resposta não.
- O modelo perde a capacidade de se autocorrigir a partir do erro.

## Conformidade

- Teste `CS-03`: autenticado como Odair, requisitar um id de lote de Ribeirão
  devolve resposta **byte a byte idêntica** à de um id inexistente.
- Teste: nenhum corpo de erro contém lista de ids.

## Referências
- [Arquitetura v2 §6](../03-arquitetura-v2.md) · `RN-A07`, `CA-06`
