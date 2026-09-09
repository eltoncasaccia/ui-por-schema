/**
 * Gera os tipos do cliente a partir do contrato do registry. T-039, ADR-0017.
 *
 * O ADR-0006 se orgulhava de não ter uma segunda lista. Com API em Python e
 * views em TypeScript ela existe — e o que impede o apodrecimento é a bijeção
 * verificada, não a disciplina.
 *
 * Uso: `make types` (roda o exportador no container e depois este script).
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { compile } from 'json-schema-to-typescript'

const RAIZ = join(import.meta.dirname, '..')
const ENTRADA = join(RAIZ, 'src', 'generated', 'contrato.json')
const SAIDA = join(RAIZ, 'src', 'generated', 'componentes.ts')

interface Componente {
  id: string
  label: string
  tamanho: string
  viewmodel: Record<string, unknown>
}

function nomeDoTipo(id: string): string {
  return id.split('_').map((p) => p[0]!.toUpperCase() + p.slice(1)).join('')
}

const contrato = JSON.parse(readFileSync(ENTRADA, 'utf8')) as {
  componentes: Componente[]
}

const partes: string[] = [
  '/* GERADO por `make types` — NÃO EDITE.',
  ' *',
  ' * Vem do registry da API (`estoque.registry.exportar`). Editar aqui faz o',
  ' * arquivo divergir da fonte, e a divergência só aparece quando alguém',
  ' * confia no tipo errado. Para mudar, mude o componente na API.',
  ' */',
  '',
]

for (const c of contrato.componentes) {
  const ts = await compile(c.viewmodel, `VM${nomeDoTipo(c.id)}`, {
    bannerComment: '',
    additionalProperties: false,
    style: { semi: false, singleQuote: true },
  })
  partes.push(ts.trim(), '')
}

const ids = contrato.componentes.map((c) => c.id)
partes.push(
  '/** Os ids que a API registra. O cliente não inventa id. */',
  `export type ComponentId =\n${ids.map((i) => `  | '${i}'`).join('\n')}`,
  '',
  '/** Usado pelo teste de bijeção: toda view precisa corresponder a um destes. */',
  `export const IDS_DA_API: readonly ComponentId[] = [\n${ids.map((i) => `  '${i}',`).join('\n')}\n] as const`,
  '',
  '/** O viewmodel de cada componente — o que de fato atravessa a rede. */',
  'export interface ViewModels {',
  ...contrato.componentes.map((c) => `  ${c.id}: VM${nomeDoTipo(c.id)}`),
  '}',
  '',
  'export type ViewModel<Id extends ComponentId> = ViewModels[Id]',
  '',
  '/** O layout obedece ao componente, nunca ao modelo. */',
  'export const TAMANHOS: Record<ComponentId, string> = {',
  ...contrato.componentes.map((c) => `  ${c.id}: '${c.tamanho}',`),
  '}',
  '',
)

writeFileSync(SAIDA, partes.join('\n'))
console.log(`gerado ${SAIDA} — ${ids.length} componentes`)
