import { Indicador } from '../ui/Indicador'
import type { Tom } from '../ui/estados'
import type { View } from './tipos'

export interface Faixa { rotulo: string; valor: number; ordem: number }
export interface VM {
  metrica: string; rotulo: string; valor: number
  unidade_medida: 'lotes' | 'centavos'
  escopo: string
  detalhe: string | null
  faixas: Faixa[]
  tipo_faixa: 'urgencia' | 'unidade' | 'nenhum'
}

/** A métrica carrega o tom: quarentena é informativa, bloqueio é grave. */
const TOM: Record<string, Tom> = {
  lotes_em_quarentena: 'ciano',
  lotes_vencendo_90d: 'ambar',
  lotes_bloqueados: 'ruim',
  valor_em_estoque: 'neutro',
}

export function formatar(valor: number, unidade: VM['unidade_medida']): string {
  return unidade === 'centavos'
    ? (valor / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
    : valor.toLocaleString('pt-BR')
}

export const view: View<VM> = ({ vm }) => (
  <Indicador
    rotulo={vm.rotulo}
    valor={formatar(vm.valor, vm.unidade_medida)}
    escopo={vm.escopo}
    detalhe={vm.detalhe ?? undefined}
    faixas={vm.faixas}
    tipoFaixa={vm.tipo_faixa}
    tom={TOM[vm.metrica] ?? 'neutro'}
  />
)
