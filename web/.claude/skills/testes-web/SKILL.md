---
name: testes-web
description: Escreve testes do cliente deste projeto — vitest, Testing Library, o teste de bijeção registry↔views e as invariantes do sistema visual em design.test.ts. Use ao criar ou alterar qualquer teste em web/src/testes/, ao adicionar uma view, ou quando uma regra visual precisar virar asserção.
---

# Testes do `web/`

`vitest` + Testing Library. Tudo em `src/testes/`.

```bash
npx vitest run                              # tudo
npx vitest run src/testes/bijecao.test.ts   # um arquivo
npx vitest                                  # watch
```

---

## Os quatro arquivos, e o que cada um protege

| Arquivo | Protege |
|---|---|
| `bijecao.test.ts` | registry e views não divergirem (ADR-0017) |
| `componentes.test.tsx` | cada view desenha o viewmodel sem quebrar |
| `design.test.ts` | as invariantes do sistema visual |
| `cache.test.ts` | `queryKey` conter o ator — cache não cruzar entre usuários |

---

## Teste de view

A entrada é o **viewmodel gerado**. Nunca monte um objeto solto:

```tsx
import type { ViewModel } from '../generated/componentes'
const vm: ViewModel<'lote_lista'> = { ... }
```

Se o formato mudar na API, o teste **para de compilar** — que é exatamente o
ponto. Um objeto tipado à mão continuaria compilando com o formato errado, e é a
segunda lista que o ADR-0017 existe para impedir.

O que vale testar numa view:

- **os casos vazios e extremos**: lista vazia, um item só, texto longo que
  precisa quebrar, número negativo com minus tipográfico
- **a chave da lista**: `lote_id`, nunca `numero` — dois lotes de mesmo número em
  unidades diferentes são registros distintos (`RN-L08`), e chavear pelo número
  faria o React tratar os dois como o mesmo
- **o que NÃO aparece**: custo, id interno, campo que a permissão removeu
- **o modo estreito**: `Tabela` vira lista de cartões, e nenhum campo some

Não teste estilo inline nem estrutura de DOM — isso engessa a view sem provar
nada. Prove o que o usuário lê.

---

## `bijecao.test.ts` — o mais importante, e o mais lento

Ele **regenera** os arquivos gerados e compara byte a byte. Seis critérios do
ADR-0017, todos verificados provocando a falha:

1. todo id da API tem view
2. toda view corresponde a um id (nada de view órfã)
3. o gerado é regenerável e idêntico — ninguém editou à mão
4. `ComponentId` inexistente não compila
5. renomear campo do viewmodel quebra as views que o usam
6. nenhuma view declara a própria `interface VM`

Se ele reclamar de "view órfã" ou "componente sem view", alguém entregou meia
tarefa. Rode `make gerar-indice && make types` antes de investigar.

**Não relaxe este teste para fazer a suíte passar.** O ADR-0017 diz, com todas as
letras, que sem ele a decisão vira regressão.

---

## `design.test.ts` — regra visual como asserção

Ele lê `src/estilo.css` como texto e afirma invariantes. Regra visual nova que
importa **vira asserção aqui**, não comentário.

O que já é verificado:

- **todo token de cor existe nos dois temas** — claro e escuro, sem exceção
- o tema do sistema não vaza quando o usuário escolheu explicitamente
- **mobile-first:** o layout de coluna vem antes da media query
- alvo de toque de 44px é token (`--toque`), não número solto
- o número é o elemento dominante do indicador
- sem clichês: nenhum cartão com barra de acento na borda esquerda
- `prefers-reduced-motion` é respeitado
- divisor arrastável só existe no desktop

Ao acrescentar um token de cor, acrescente-o **nos dois temas** ou o teste
falha — e essa falha é a feature.

---

## `cache.test.ts` — o bug que já aconteceu

Toda `queryKey` contém o id do ator. Sem isso, a resposta em cache de um usuário
aparece para outro — já aconteceu neste projeto. Ao criar chave nova, acrescente
a asserção correspondente.

---

## Antes de entregar

```bash
npx tsc --noEmit
npx vitest run
npx eslint src
npx tsx scripts/arch-check.ts
```

Nada de `any`, nada de `@ts-expect-error` sem justificativa escrita ao lado.

Se `node_modules` for symlink compartilhado entre worktrees, **não rode
`npm install`** — você mexeria no ambiente das outras sessões.
