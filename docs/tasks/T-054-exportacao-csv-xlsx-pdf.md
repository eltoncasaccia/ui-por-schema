# T-054 — Exportação de relatório em CSV, XLSX e PDF

| | |
|---|---|
| **Trilha** | C/D · componentes e cliente |
| **Tamanho** | G |
| **Depende de** | T-044, T-023 |
| **ADRs** | [0004](../adr/0004-autorizacao-em-tres-momentos.md), [0020](../adr/0020-select-no-servidor.md), [0029](../adr/0029-relatorio-como-componente.md), [0028](../adr/0028-processo-de-decisao.md), [0035](../adr/0035-exportacao-no-servidor.md) |
| **RN** | `RN-A02`, `RN-D05`, `RN-F03` |
| **Origem** | pedido do usuário em 2026-09-16: "senti falta de geração de relatório e exportação em PDF, planilha" |
| **Escrita em** | 2026-09-16 |

## Por que existe

O PRD promete exportação em três lugares: RF-11 (temperatura exportável), RF-14
(custo invisível "em tela, **exportação** e assistente") e a persona Sandra
(auditoria, "trilha completa, exportação"). O que existe hoje é **um** botão:
"Baixar CSV" em `temperatura_historico`.

O ADR-0029 diz que `relatorio_movimentacao` "reaproveita a exportação que já
existe". Essa exportação não existe fora da temperatura, então a promessa do ADR
não tem código. Não há PDF nem planilha em lugar nenhum.

## O que já foi conferido

- **CSV atual:** `temperatura_historico.py` monta o texto no `select`
  (`_csv_pontos`, `_csv_baldes`), e a view baixa por `Blob`
  (`web/src/views/temperatura_historico.tsx:15`). Nenhum outro componente
  exporta.
- **`pypdf` e `python-docx` não servem.** Nenhuma das duas está em
  `api/pyproject.toml`. `pypdf` lê e manipula PDFs que já existem, mas não gera
  documento com tabela. `python-docx` gera Word, não planilha.
- **O caminho de leitura autorizado é `server/rotas/dados.py`.** Ele confere a
  permissão base, o `RequiresPorValor`, o escopo de unidade, `load`, `select` e
  auditoria. A exportação precisa passar exatamente por esse caminho.
- **A paginação de `dados` limita a 200** (`PaginaPedido.limite`). Um relatório
  exportado precisa de mais linhas, com teto.

## Decisão

- **A exportação é gerada no servidor, a partir do viewmodel.** O arquivo sai do
  resultado do `select`, com a identidade real. Por construção, o arquivo contém
  o que a tela mostraria e nada além: se o `select` não entrega custo, a planilha
  também não tem (RF-14). Gerar no cliente também confiaria no viewmodel, mas
  obrigaria a mandar ao navegador bibliotecas pesadas de xlsx e pdf.
- **Rota nova:** `POST /api/componentes/{id}/exportar`, com o mesmo corpo de
  `dados`, mais `formato: Literal["csv", "xlsx", "pdf"]`. A autorização é
  idêntica à de `dados`. **Isto é mudança do CONTRATOS §8** e vai registrada
  como rev. 2.7 no mesmo commit.
- **Sem mudar `ComponentDef`:** a transformação viewmodel → tabela mora num
  registro próprio, `application/exportacao/tabelas.py`
  (`{componente_id: Callable[[VM], Tabela]}`). Mexer na assinatura de
  `ComponentDef` pararia tudo (CONTRATOS §11). Componente que não está no
  registro não exporta, e a rota responde `nao_encontrado`.
- **Formatos são adaptadores atrás de uma porta** (`Exportador`), para o
  `application` não importar `openpyxl` nem `fpdf`:
  - `csv`: biblioteca padrão, separador `;`, UTF-8 com BOM (abre direto no
    Excel pt-BR);
  - `xlsx`: **openpyxl** (MIT);
  - `pdf`: **fpdf2** (LGPL-3.0, sem cairo ou pango no container). *Na execução:
    ele traz o Pillow, que é distribuído como wheel, sem pacote de sistema.*
    Cabeçalho com Bertoni, título, filtros aplicados, quem gerou e quando.
- **Dependências novas:** `openpyxl` e `fpdf2`. O usuário autorizou os três
  formatos em 2026-09-16 (ADR-0028). A escolha das bibliotecas foi recomendação
  desta tarefa; se o usuário discordar, troca-se o adaptador, não a porta.
- **O CSV da temperatura passa a usar o mesmo caminho.** O campo `csv` do
  viewmodel fica até a view migrar, e sai no mesmo commit, se nada mais o usar.
- **Uma leitura autorizada só** *(decidido na execução)*: a sequência de
  `dados` (permissão, `RequiresPorValor`, escopo, `load`, `select`) foi para
  `deps.ler_componente`, e as duas rotas a chamam. Uma cópia em `exportar`
  seria o atalho que a tarefa existe para impedir.
- **O cliente sabe o que exporta pelo catálogo** *(decidido na execução)*:
  `/api/catalogo` leva `exportavel`. O campo é da borda e não entra no prompt.
  Uma lista fixa no cliente divergiria do registro do servidor.
- **O botão fica acima do bloco** *(decidido na execução, vendo no
  navegador)*: embaixo, numa lista com rolagem infinita, ele nunca aparecia.

## Escopo — componentes exportáveis nesta tarefa

`relatorio_movimentacao`, `temperatura_historico`, `temperatura_excursoes`,
`fila_vencimento`, `lote_lista`, `movimento_lista`, `auditoria_trilha`.
Os outros podem entrar em tarefa futura, com uma linha cada no registro.

## Arquivos de propriedade exclusiva

```
api/src/estoque/application/exportacao/__init__.py
api/src/estoque/application/exportacao/tabelas.py      Tabela + registro por componente
api/src/estoque/application/exportacao/porta.py        Exportador (Protocol)
api/src/estoque/exportacao/__init__.py                 adapter secundario, como data/ e assistant/
api/src/estoque/exportacao/_celula.py                  formatacao comum aos tres
api/src/estoque/exportacao/formato_csv.py              (formato_*: `csv.py` sombrearia o modulo padrao)
api/src/estoque/exportacao/formato_xlsx.py
api/src/estoque/exportacao/formato_pdf.py
api/src/estoque/server/rotas/exportar.py
api/tests/exportacao/
api/tests/server/test_t054_exportar.py                 borda HTTP mora em tests/server (usa `borda`)
api/tests/arquitetura/violacoes/formato*               violacao de proposito dos contratos 6 e 7
web/src/render/BotaoExportar.tsx                       render/, e nao shell/: e' parte do bloco
web/src/testes/exportar.test.tsx
docs/adr/0035-exportacao-no-servidor.md
```

## Toca, com registro

```
api/pyproject.toml, api/uv.lock          openpyxl, fpdf2
api/src/estoque/server/app.py            incluir o router
api/src/estoque/server/deps.py           ler_componente, comum a dados e exportar
api/src/estoque/server/rotas/dados.py    passa a chamar ler_componente
api/src/estoque/server/rotas/catalogo.py `exportavel` na resposta
api/.importlinter                        contratos 6 e 7; exportar no contrato 5
api/src/estoque/application/registry/componentes/temperatura_historico.py
api/tests/registry/test_temperatura_historico.py  AC-2 da T-023 foi para tests/exportacao
api/tests/registry/test_paginacao.py     a pagina agora passa por ler_componente
api/tests/server/test_t011_ac.py         corpo valido da rota nova na varredura
api/tests/arquitetura/test_verificador_falha_quando_violado.py  7 contratos
web/src/views/temperatura_historico.tsx  botao antigo sai
web/src/api.ts                           chamada que devolve Blob; `exportavel`
web/src/render/motor.tsx                 o botao entra acima de cada bloco
web/src/estilo.css                       .exportar, com tokens
web/src/generated/*                      make types (o `csv` saiu do viewmodel)
docs/tasks/CONTRATOS.md                  §8: rota nova, rev. 2.7
docs/adr/0029-relatorio-como-componente.md  "exportacao que ja existe" aponta para a 0035
docs/adr/README.md                       indice
docs/RASTREABILIDADE.md                  CA-07, RN-A02
```

`web/src/shell/Workspace.tsx`, previsto na escrita, não foi tocado: o botão
é por bloco, e o bloco é montado em `render/motor.tsx`.

## Critérios de aceite

- [x] **AC-1** `relatorio_movimentacao` exporta nos três formatos. O conteúdo de
      cada arquivo, lido de volta no teste (`csv`, `openpyxl`, texto extraído do
      PDF), tem as mesmas linhas e colunas do viewmodel de `dados` com os mesmos
      params.
      *CSV comparado linha a linha e total com `/dados`; XLSX e PDF com todos os
      rótulos. Os outros seis componentes geram os três formatos (18 casos).
      No app real, com o banco de desenvolvimento: 178 lotes na tela e 178
      linhas na planilha baixada pelo navegador.*
- [x] **AC-2** O CSV abre no Excel pt-BR sem estragar acentos nem colunas: BOM e
      `;` verificados nos bytes. O XLSX tem número como número e data como data,
      não como texto.
      *Verificado nos bytes e com `openpyxl`: `data_type == "n"`, data como
      `datetime`, formato `"R$" #,##0.00`. Hora convertida para São Paulo. Não
      aberto num Excel de verdade.*
- [x] **AC-3** O PDF traz título, filtros aplicados, nome de quem gerou, data e
      hora e número de página.
      *Texto extraído com `pypdf` (dependência só de teste); PDF de 300 linhas
      numera "página N de N". Conferido a olho, renderizado em PNG.*
- [x] **AC-4** Toda exportação gera auditoria com `acao="exportar"`, componente,
      formato e params (`RN-D05`). *(negativo: uma exportação recusada não gera
      registro de `exportar`)*
      *Corrigido na execução: o texto escrito dizia que a recusa "também deixa
      rastro, como em `dados`", mas `dados` não audita recusa. O registro diz
      que um arquivo saiu, e na recusa nenhum saiu. Os dois lados foram testados
      contra o banco.*
- [x] **AC-5** **Custo não vaza (RF-14, `RN-A02`).** Um ator sem `custo.ler` que
      pede `metrica=valor` recebe a mesma recusa de `dados`, sem arquivo. Os
      arquivos de `relatorio_movimentacao` gerados para ele não têm coluna nem
      valor de custo, verificado nos bytes dos três formatos. *(negativo)*
      *403 em JSON, sem arquivo, nos três formatos. O arquivo do RT não tem
      "R$" nem "Valor". O contraponto é o diretor exportando "Valor (R$)".
      Sabotado (sem `autorizar_params_ou_falhar`): os negativos ficaram
      vermelhos nas duas rotas. No app real, a RT recebeu 403.*
- [x] **AC-6** **Rota sem atalho.** Um componente fora do catálogo do ator, uma
      `unidade_id` fora do escopo e uma requisição sem sessão são recusados. O
      teste roda a mesma tabela de casos negativos de `dados`, contra
      `exportar`. *(negativo)*
      *Quatro negativos parametrizados nas duas rotas, com o mesmo código
      (unidade fora do escopo é 403 nas duas, e não 404 como presumido na
      escrita). Também: sem sessão (401), sem CSRF (403), formato fora do enum
      (422). Contraponto: o gerente exporta a própria unidade.*
- [x] **AC-7** **Injeção de fórmula.** Uma célula que começa com `=`, `+`, `-`,
      `@`, tab ou CR sai neutralizada no CSV e no XLSX (por exemplo, um lote ou
      uma observação `=HYPERLINK(...)`). *(negativo)*
      *Também no título e no recorte. No XLSX, nenhuma célula com
      `data_type == "f"`. Negativo não vira texto. Sabotado (`neutralizar`
      devolvendo o texto cru): 9 testes vermelhos.*
- [x] **AC-8** **Teto de linhas.** Acima do teto (**5.000 linhas**), a exportação é recusada com uma mensagem que manda
      estreitar o filtro. Nunca trunca em silêncio. *(negativo)*
      *Conferido pelo `tem_mais` da lista paginada e pelo tamanho da tabela da
      que não pagina (`movimento_lista`). Sabotado: os dois ficaram vermelhos.
      O relatório de movimentação continua com o próprio teto de leitura
      (500), declarado como "amostra" no recorte, que sai no arquivo.*
- [x] **AC-9** Um componente fora do registro de exportação responde
      `nao_encontrado`, e o cliente não mostra o botão para ele.
      *Servidor: `estoque_indicador` e id inexistente dão 404; o catálogo marca
      `exportavel`. Cliente: sem botão para não exportável nem para componente
      fora do catálogo do ator. Sabotado no cliente: os dois vermelhos.*
- [x] **AC-10** `import-linter`: `application` não importa `openpyxl` nem `fpdf`,
      e `assistant` não importa `exportacao`. Os dois contratos já foram vistos
      falhar pelo menos uma vez, com o import sabotado.
      *No projeto real (`import openpyxl` em `porta.py`, `import
      estoque.exportacao` em `prompt.py`): os dois contratos BROKEN, e o 7 pelo
      caminho indireto. Revertido. Fixture versionada em
      `tests/arquitetura/violacoes/formato`.*
- [x] **AC-11** No cliente, o botão "Exportar ▾ (CSV · Planilha · PDF)" aparece
      nos blocos exportáveis, baixa o arquivo com nome legível
      (`movimentacao-por-unidade-90d-2026-09-16.xlsx`) e mostra erro legível
      quando o servidor recusa.
      *Vitest (6 testes, com Esc e clique fora) e no navegador, com
      `playwright-cli` como Marco: menu com os três formatos, download
      `lotes-2026-09-16.xlsx`.*
- [x] **AC-12** `temperatura_historico` exporta pelo caminho novo. O botão
      antigo e o campo `csv` saem, ou fica registrado por que ficam.
      *Os dois saíram, junto com `exportavel` do viewmodel. Os testes de AC-2
      da T-023 foram para `tests/exportacao/test_tabelas.py` (pontos e baldes).
      No app real: PDF de 5 páginas para a RT.*

## Fechamento — 2026-09-16

A exportação passa pelo mesmo caminho autorizado da tela, e cada proteção foi
vista falhando. Números: `make check` com 981 testes da API (2 skips
intencionais do CS-04) e 142 do web; 7 contratos do import-linter.

O que ficou de fora, ou não foi conferido:

- **Excel de verdade:** o formato foi conferido com `openpyxl` e nos bytes, não
  abrindo o arquivo no Excel.
- **Hora da temperatura:** o componente recorta o período em UTC. Numa
  exportação de 01/08, a primeira linha sai "31/07 21:00" em São Paulo. A tela
  mostra igual, então não é divergência desta tarefa, mas quem lê estranha.
- **Três formatos com biblioteca nova:** `openpyxl` e `fpdf2` em produção;
  `pypdf` e `types-openpyxl` só em desenvolvimento.

## Não faz

- **Livro de controlados exportável (`RN-C05`):** continua como decisão aberta
  em [A-23](./ACHADOS.md), porque custa +1 no catálogo. Com esta tarefa pronta,
  ele passa a custar só o componente.
- **Word (`.docx`):** ninguém pediu.
- **Relatório agendado ou enviado por e-mail:** seria dado de estoque saindo do
  sistema, o que pede outra discussão.
- **Exportar a composição do assistente inteira num PDF só:** cada bloco exporta
  por conta própria. Juntar blocos fica para depois, se houver pedido.
