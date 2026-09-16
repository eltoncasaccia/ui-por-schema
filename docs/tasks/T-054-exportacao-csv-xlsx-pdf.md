# T-054 — Exportação de relatório em CSV, XLSX e PDF

| | |
|---|---|
| **Trilha** | C/D · componentes e cliente |
| **Tamanho** | G |
| **Depende de** | T-044, T-023 |
| **ADRs** | [0004](../adr/0004-autorizacao-em-tres-momentos.md), [0020](../adr/0020-select-no-servidor.md), [0029](../adr/0029-relatorio-como-componente.md), [0028](../adr/0028-processo-de-decisao.md), **0035 (esta tarefa escreve)** |
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
  - `pdf`: **fpdf2** (LGPL-3.0, Python puro, sem cairo ou pango no container).
    Cabeçalho com Bertoni, título, filtros aplicados, quem gerou e quando.
- **Dependências novas:** `openpyxl` e `fpdf2`. O usuário autorizou os três
  formatos em 2026-09-16 (ADR-0028). A escolha das bibliotecas foi recomendação
  desta tarefa; se o usuário discordar, troca-se o adaptador, não a porta.
- **O CSV da temperatura passa a usar o mesmo caminho.** O campo `csv` do
  viewmodel fica até a view migrar, e sai no mesmo commit, se nada mais o usar.

## Escopo — componentes exportáveis nesta tarefa

`relatorio_movimentacao`, `temperatura_historico`, `temperatura_excursoes`,
`fila_vencimento`, `lote_lista`, `movimento_lista`, `auditoria_trilha`.
Os outros podem entrar em tarefa futura, com uma linha cada no registro.

## Arquivos de propriedade exclusiva

```
api/src/estoque/application/exportacao/__init__.py
api/src/estoque/application/exportacao/tabelas.py      Tabela + registro por componente
api/src/estoque/application/exportacao/porta.py        Exportador (Protocol)
api/src/estoque/exportacao/csv.py                      adapter secundario, como data/ e assistant/
api/src/estoque/exportacao/xlsx.py
api/src/estoque/exportacao/pdf.py
api/src/estoque/server/rotas/exportar.py
api/tests/exportacao/
web/src/shell/BotaoExportar.tsx
web/src/testes/exportar.test.tsx
docs/adr/0035-exportacao-no-servidor.md
```

## Toca, com registro

```
api/pyproject.toml, api/uv.lock          openpyxl, fpdf2
api/src/estoque/server/app.py            incluir o router
api/.importlinter                        application nao importa openpyxl/fpdf nem estoque.exportacao
api/src/estoque/application/registry/componentes/temperatura_historico.py
web/src/views/temperatura_historico.tsx  botao antigo sai
web/src/api.ts                           chamada que devolve Blob
web/src/shell/Workspace.tsx              onde o botao aparece por bloco
docs/tasks/CONTRATOS.md                  §8: rota nova, rev. 2.7
docs/adr/0029-relatorio-como-componente.md  "exportacao que ja existe" aponta para a 0035
docs/RASTREABILIDADE.md                  RF-11, RF-14
```

> ⚠️ Em 2026-09-16, `web/src/api.ts`, `web/src/shell/Workspace.tsx` e
> `docs/tasks/CONTRATOS.md` têm alterações não commitadas de outro trabalho.
> **Não assuma antes de elas entrarem.**

## Critérios de aceite

- [ ] **AC-1** `relatorio_movimentacao` exporta nos três formatos. O conteúdo de
      cada arquivo, lido de volta no teste (`csv`, `openpyxl`, texto extraído do
      PDF), tem as mesmas linhas e colunas do viewmodel de `dados` com os mesmos
      params.
- [ ] **AC-2** O CSV abre no Excel pt-BR sem estragar acentos nem colunas: BOM e
      `;` verificados nos bytes. O XLSX tem número como número e data como data,
      não como texto.
- [ ] **AC-3** O PDF traz título, filtros aplicados, nome de quem gerou, data e
      hora e número de página.
- [ ] **AC-4** Toda exportação gera auditoria com `acao="exportar"`, componente,
      formato e params (`RN-D05`). *(negativo: exportação que falha na
      autorização também deixa rastro, como em `dados`)*
- [ ] **AC-5** **Custo não vaza (RF-14, `RN-A02`).** Um ator sem `custo.ler` que
      pede `metrica=valor` recebe a mesma recusa de `dados`, sem arquivo. Os
      arquivos de `relatorio_movimentacao` gerados para ele não têm coluna nem
      valor de custo, verificado nos bytes dos três formatos. *(negativo)*
- [ ] **AC-6** **Rota sem atalho.** Um componente fora do catálogo do ator, uma
      `unidade_id` fora do escopo e uma requisição sem sessão são recusados. O
      teste roda a mesma tabela de casos negativos de `dados`, contra
      `exportar`. *(negativo)*
- [ ] **AC-7** **Injeção de fórmula.** Uma célula que começa com `=`, `+`, `-`,
      `@`, tab ou CR sai neutralizada no CSV e no XLSX (por exemplo, um lote ou
      uma observação `=HYPERLINK(...)`). *(negativo)*
- [ ] **AC-8** **Teto de linhas.** Acima do teto (valor decidido na execução e
      registrado aqui), a exportação é recusada com uma mensagem que manda
      estreitar o filtro. Nunca trunca em silêncio. *(negativo)*
- [ ] **AC-9** Um componente fora do registro de exportação responde
      `nao_encontrado`, e o cliente não mostra o botão para ele.
- [ ] **AC-10** `import-linter`: `application` não importa `openpyxl` nem `fpdf`,
      e `assistant` não importa `exportacao`. Os dois contratos já foram vistos
      falhar pelo menos uma vez, com o import sabotado.
- [ ] **AC-11** No cliente, o botão "Exportar ▾ (CSV · Planilha · PDF)" aparece
      nos blocos exportáveis, baixa o arquivo com nome legível
      (`movimentacao-por-unidade-90d-2026-09-16.xlsx`) e mostra erro legível
      quando o servidor recusa.
- [ ] **AC-12** `temperatura_historico` exporta pelo caminho novo. O botão
      antigo e o campo `csv` saem, ou fica registrado por que ficam.

## Não faz

- **Livro de controlados exportável (`RN-C05`):** continua como decisão aberta
  em [A-23](./ACHADOS.md), porque custa +1 no catálogo. Com esta tarefa pronta,
  ele passa a custar só o componente.
- **Word (`.docx`):** ninguém pediu.
- **Relatório agendado ou enviado por e-mail:** seria dado de estoque saindo do
  sistema, o que pede outra discussão.
- **Exportar a composição do assistente inteira num PDF só:** cada bloco exporta
  por conta própria. Juntar blocos fica para depois, se houver pedido.
