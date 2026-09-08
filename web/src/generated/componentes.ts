/* GERADO por `make types` — NÃO EDITE.
 *
 * Vem do registry da API (`estoque.registry.exportar`). Editar aqui faz o
 * arquivo divergir da fonte, e a divergência só aparece quando alguém
 * confia no tipo errado. Para mudar, mude o componente na API.
 */

export interface VMEstoqueIndicador {
  detalhe?: string | null
  escopo: string
  faixas?: EstoqueIndicadorFaixa[]
  metrica: 'lotes_em_quarentena' | 'lotes_vencendo_90d' | 'lotes_bloqueados' | 'valor_em_estoque'
  rotulo: string
  tipo_faixa?: 'urgencia' | 'unidade' | 'nenhum'
  unidade_medida: 'lotes' | 'centavos'
  valor: number
}
/**
 * Um pedaco da decomposicao. `ordem` posiciona na rampa sequencial.
 */
export interface EstoqueIndicadorFaixa {
  ordem?: number
  rotulo: string
  valor: number
}

/**
 * O viewmodel. E' EXATAMENTE isto que atravessa a rede — nada de `Lote`,
 * nada de linha de banco, nada de custo (ADR-0020, CA-05).
 */
export interface VMFilaVencimento {
  cursor?: string | null
  janela_dias: number
  linhas: FilaVencimentoLinhaVencimento[]
  resumo?: FilaVencimentoFaixaResumo[]
  tem_mais?: boolean
  total: number
}
export interface FilaVencimentoLinhaVencimento {
  dias_restantes: number
  lote_id: string
  numero: string
  produto: string
  saldo: number
  situacao: 'ok' | 'alerta_90' | 'bloqueio_30' | 'vencido'
  unidade: string
  validade: string
}
/**
 * Uma faixa da rampa de urgencia. `ordem` cresce com a urgencia.
 */
export interface FilaVencimentoFaixaResumo {
  ordem: number
  rotulo: string
  valor: number
}

export interface VMVencimentoGrafico {
  baldes: VencimentoGraficoBalde[]
  escopo: string
  horizonte_dias: number
  legenda: string[]
  pico_rotulo: string | null
  total_lotes: number
}
/**
 * Uma barra. `urgencia` posiciona na rampa: 0 tranquilo, 3 vencido.
 */
export interface VencimentoGraficoBalde {
  inicio: string
  lotes: number
  rotulo: string
  unidades: number
  urgencia: number
}

/** Os ids que a API registra. O cliente não inventa id. */
export type ComponentId =
  | 'estoque_indicador'
  | 'fila_vencimento'
  | 'vencimento_grafico'

/** Usado pelo teste de bijeção: toda view precisa corresponder a um destes. */
export const IDS_DA_API: readonly ComponentId[] = [
  'estoque_indicador',
  'fila_vencimento',
  'vencimento_grafico',
] as const

/** O viewmodel de cada componente — o que de fato atravessa a rede. */
export interface ViewModels {
  estoque_indicador: VMEstoqueIndicador
  fila_vencimento: VMFilaVencimento
  vencimento_grafico: VMVencimentoGrafico
}

export type ViewModel<Id extends ComponentId> = ViewModels[Id]

/** O layout obedece ao componente, nunca ao modelo. */
export const TAMANHOS: Record<ComponentId, string> = {
  estoque_indicador: 'linha',
  fila_vencimento: 'inteira',
  vencimento_grafico: 'inteira',
}
