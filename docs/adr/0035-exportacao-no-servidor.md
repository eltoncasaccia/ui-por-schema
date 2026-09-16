# ADR-0035 — Exportação gerada no servidor, a partir do viewmodel

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-16 |
| **Escopo** | Borda HTTP e aplicação |
| **Tarefa** | [T-054](../tasks/T-054-exportacao-csv-xlsx-pdf.md) |
| **Emenda** | [ADR-0029](./0029-relatorio-como-componente.md): a "exportação que já existe" passa a ser esta |

A dependência foi autorizada antes, como exige o [ADR-0028](./0028-processo-de-decisao.md):
em 2026-09-16 o cliente pediu CSV, PDF e planilha ("já registra para
implementar o csv, pdf e .xlsx").

## Contexto

O PRD promete exportação em três lugares: RF-11 (temperatura), RF-14 (custo
invisível "em tela, **exportação** e assistente") e a persona de auditoria. O
que existia era um CSV montado no `select` de `temperatura_historico`, que
viajava no viewmodel em toda leitura e era baixado pelo navegador.

O risco de uma exportação não é o formato. É ela virar um **segundo caminho de
leitura**: se a checagem de permissão ficar numa rota e for esquecida na outra,
o arquivo sai com o que a tela recusaria.

## Decisão

> **O arquivo é gerado no servidor, a partir do viewmodel, por uma rota que usa
> a mesma função de leitura autorizada da tela.**

- **Uma leitura só.** `deps.ler_componente` faz a permissão base,
  `RequiresPorValor`, o escopo de unidade, `load` e `select`. `dados` e
  `exportar` chamam essa função, e nenhuma das duas tem cópia da lógica.
- **Do viewmodel, nunca do `load`.** `application/exportacao/tabelas.py`
  transforma o viewmodel em tabela. O que o `select` não entregou (custo, por
  exemplo) não existe ali para vazar.
- **Registro próprio, e não campo em `ComponentDef`.** Mudar a assinatura do
  contrato de componente para tudo (CONTRATOS §11). Componente fora do
  registro responde `nao_encontrado`.
- **Formato é adaptador.** `estoque/exportacao/` tem CSV (biblioteca padrão),
  XLSX (`openpyxl`) e PDF (`fpdf2`). O contrato 6 do import-linter proíbe
  `application.exportacao` de importar essas bibliotecas; o contrato 7 proíbe o
  assistente de alcançar a exportação.
- **Recusa, nunca corte.** Acima de 5.000 linhas a exportação é recusada com
  uma mensagem que manda estreitar o filtro. Um arquivo truncado parece
  completo.
- **Injeção de fórmula.** Texto que começa com `=`, `+`, `-`, `@`, tab ou CR
  ganha `'` na frente, no CSV e no XLSX, inclusive no título e no recorte.
- **Auditada** como `acao="exportar"`, com formato, params e número de linhas
  (`RN-D05`). Recusa não gera o registro, porque nenhum arquivo saiu.
- **O cliente sabe o que exporta pelo catálogo.** `/api/catalogo` leva
  `exportavel`. O campo é da borda e não entra no prompt.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Gerar no navegador, a partir do viewmodel em cache | mandaria bibliotecas de xlsx e pdf para todo cliente; e a lista paginada no cache é só o que já foi rolado, então o arquivo dependeria de até onde a pessoa desceu |
| Impressão do navegador para PDF | não gera arquivo com cabeçalho, autor e paginação estáveis; o resultado muda com o navegador |
| `pypdf` / `python-docx`, que o usuário citou | `pypdf` lê e manipula PDF, mas não monta tabela; `python-docx` gera Word, não planilha |
| WeasyPrint (HTML → PDF) | exige cairo e pango no container |
| Rota de exportação com cópia da autorização | é exatamente o atalho que esta decisão existe para impedir |

## Consequências

- `temperatura_historico` deixa de carregar `csv` no viewmodel: a leitura da
  tela fica mais leve, e o CSV sai pelo mesmo caminho dos outros componentes.
- `fpdf2` traz o Pillow como dependência. Ele é distribuído como wheel, sem
  pacote de sistema.
- As fontes embutidas do PDF cobrem só latin-1. Português cabe inteiro nelas;
  outros caracteres são trocados antes de gerar, para o PDF não falhar.
- O livro de controlados exportável ([A-23](../tasks/ACHADOS.md)) passa a
  custar só o componente: a exportação já existe.
