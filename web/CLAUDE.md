# CLAUDE.md — `web/`

Cliente em React + TypeScript, Vite, TanStack Query, Vitest. Sem framework de
CSS: um sistema de tokens em `src/estilo.css`.

Leia primeiro o [`CLAUDE.md` da raiz](../CLAUDE.md) — a tese, o protocolo de
leitura e o processo valem para os dois projetos. Aqui fica só o que é
específico do TypeScript.

---

## Comandos

```bash
npx vitest run                  # testes
npx vitest run src/testes/bijecao.test.ts
npx tsc --noEmit                # tipos
npx eslint src                  # lint
npx tsx scripts/arch-check.ts   # regras de arquitetura do lado TS
npm run dev                     # Vite em modo desenvolvimento
```

`node_modules` pode ser um symlink compartilhado entre worktrees. **Nesse caso,
não rode `npm install`** — a instalação mexeria no chão das outras sessões.

---

## Como o código se divide

| Pasta | Papel | Regra |
|---|---|---|
| `views/` | uma view por componente registrado | **não busca dado, não decide regra, não conhece permissão.** Recebe `vm` e desenha |
| `ui/` | peças reutilizáveis: `Tabela`, `Indicador`, `BarraFaixas`, `Etiqueta` | sem conhecimento de domínio |
| `render/motor.tsx` | recebe o schema validado e monta a tela | decide layout a partir de `tamanho`, nunca do modelo |
| `shell/` | a moldura: painéis, login, navegação, workspace | |
| `estado/`, `query/` | sessão e cache | |
| `generated/` | **gerado** — não edite | `make types` |
| `testes/` | suíte | |

### `views/` é a camada mais restrita do projeto

Verificado por `scripts/arch-check.ts`, não combinado:

- não importa `query/` nem o cliente de API — dado chega por `props.vm`
- **não contém `useEffect`** — view que busca, sincroniza ou agenda deixou de ser
  função do viewmodel e virou um componente com vida própria
- não importa `@tanstack/react-query`
- não usa `dangerouslySetInnerHTML` — o schema vem de um modelo de linguagem

Uma view é, por contrato, `(props: { vm }) => JSX.Element`. Só isso.

---

## A bijeção registry ↔ views

Todo id registrado na API tem **exatamente uma** view em `src/views/<id>.tsx`, e
vice-versa ([ADR-0017](../docs/adr/0017-registry-servidor-views-cliente.md)).
Entregar um lado só **quebra o CI**.

A view importa o viewmodel **gerado** e nunca declara o próprio tipo:

```tsx
import type { View } from './tipos'
type VM = ViewModel<'fila_vencimento'>       // ✅ vem do registry da API
// interface VM { ... }                       // ❌ tipo escrito à mão continua
//                                            //    compilando depois de a API mudar
export const view: View<'fila_vencimento'> = ({ vm }) => ( ... )
```

`Record<ComponentId, ...>` em `views/indice.ts` é a metade que o **compilador**
garante. A outra — view sobrando, sem registro na API — é o teste de bijeção,
porque tipo nenhum enxerga o servidor.

Depois de criar ou remover uma view: `make gerar-indice && make types`.

---

## O sistema visual

Tudo em `src/estilo.css`, como tokens. **Nunca escreva cor, espaçamento ou raio
literal num componente** — `src/testes/design.test.ts` verifica as invariantes.

| Grupo | Tokens |
|---|---|
| superfícies | `--s0` chão · `--s1` painéis · `--s2` cartões · `--campo` |
| texto | `--texto` · `--dim` · `--fraco` |
| espaçamento | `--e1` 4px … `--e6` 40px |
| forma | `--raio` · `--raio-sm` · `--barra` · `--toque` 44px |
| estado | `--bom` `--ciano` `--ambar` `--laranja` `--ruim` (+ `-b` para borda) |

### A semântica dos tons não é decorativa

`--ambar` e `--laranja` são **matizes diferentes de propósito**: alerta de 90
dias e bloqueio de 30 dias são a diferença entre *programar uma venda* e
*recolher da prateleira*. Um único tom de "atenção" apagaria isso. Pelo mesmo
motivo, `bloqueado` (decisão humana, reversível) e `vencido` (terminal) não
compartilham cor.

Use os mapas prontos — `SITUACAO` em `ui/estados.ts`, `STATUS_LOTE` em
`views/lote_lista.tsx` — em vez de inventar outro.

### Regras que os testes impõem

- **Todo token de cor existe nos dois temas.** Claro e escuro, sem exceção.
- **Mobile-first:** o layout de coluna vem **antes** da media query.
- **Tabela que não quebra:** em coluna estreita, `Tabela` vira lista de cartões.
  Rolagem horizontal esconde coluna, e coluna escondida numa tabela de lotes é
  um dado regulatório que sumiu.
- **Sem clichês:** nada de barra de acento na borda esquerda do cartão.
- **Respeite `prefers-reduced-motion`.**
- Divisor arrastável só existe no desktop.

---

## Testes

Convenções em [`.claude/skills/testes-web`](.claude/skills/). O resumo:

- `vitest` + Testing Library. Arquivos em `src/testes/`.
- Teste de view usa o **viewmodel gerado** como entrada — se o formato mudar na
  API, o teste para de compilar, que é o ponto.
- `design.test.ts` lê o CSS como texto e afirma invariantes. Regra visual nova
  que importa vira asserção ali.
- `bijecao.test.ts` é o que impede registry e views de divergirem. Ele
  **regenera** os arquivos gerados e compara byte a byte — por isso é o mais
  lento, e por isso não se mexe nele sem entender o ADR-0017.
