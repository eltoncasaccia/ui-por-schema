import type { View } from './tipos'

export interface VM {
  metrica: string
  rotulo: string
  valor: number
  unidade_medida: 'lotes' | 'centavos'
}

/**
 * O componente recebe uma MÉTRICA e mostra o valor que o servidor calculou.
 * Nunca recebe o número pelo schema — um componente que aceitasse valor literal
 * renderizaria alucinação com a mesma cara de verdade.
 */
export const view: View<VM> = ({ vm }) => {
  const texto =
    vm.unidade_medida === 'centavos'
      ? (vm.valor / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
      : String(vm.valor)
  return (
    <div>
      <div className="suave" style={{ fontSize: '.8rem', textTransform: 'uppercase', letterSpacing: '.04em' }}>
        {vm.rotulo}
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 640, letterSpacing: '-.02em', marginTop: '.15rem' }}>
        {texto}
      </div>
    </div>
  )
}
