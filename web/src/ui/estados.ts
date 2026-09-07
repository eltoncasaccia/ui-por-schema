/**
 * Semântica visual dos estados do lote.
 *
 * Alerta (90d) e bloqueio (30d) recebem MATIZES DIFERENTES — âmbar e laranja —
 * porque a diferença entre eles é a diferença entre programar uma venda e
 * recolher da prateleira. Um único tom de "atenção" apagaria isso.
 */
export type Situacao = 'ok' | 'alerta_90' | 'bloqueio_30' | 'vencido'
export type Tom = 'bom' | 'ciano' | 'ambar' | 'laranja' | 'ruim' | 'neutro'

export const SITUACAO: Record<Situacao, { rotulo: string; tom: Tom }> = {
  ok: { rotulo: 'Liberado', tom: 'bom' },
  alerta_90: { rotulo: 'Alerta 90d', tom: 'ambar' },
  bloqueio_30: { rotulo: 'Bloqueio 30d', tom: 'laranja' },
  vencido: { rotulo: 'Vencido', tom: 'ruim' },
}

export function classeEtiqueta(tom: Tom): string {
  return tom === 'neutro' ? 'etiqueta' : `etiqueta etiqueta-${tom}`
}
export function classeTexto(tom: Tom): string {
  return tom === 'neutro' || tom === 'ciano' ? '' : `texto-${tom}`
}
