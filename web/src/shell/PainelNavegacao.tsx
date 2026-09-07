import { Icone } from '../ui/icones'

/**
 * Menu convencional, por TAREFA do domínio.
 *
 * O catálogo cru do registry — ids, descrições, enums — saiu daqui e foi para a
 * aba do Execution Trace, que é onde ele serve de evidência. Num menu ele era
 * só ruído: ninguém navega por "estoque_indicador".
 */
export interface ItemNav {
  id: string
  rotulo: string
  sub: string
  icone: (p: { tamanho?: number }) => JSX.Element
  /** Id do componente registrado que este item abre. */
  componente: string
  params?: Record<string, unknown>
}

export const MENU: ItemNav[] = [
  { id: 'vencimento', rotulo: 'Vencimento', sub: 'o que vence em 90 dias',
    icone: Icone.Relogio, componente: 'fila_vencimento', params: { janela: '90' } },
  { id: 'quarentena', rotulo: 'Quarentena', sub: 'aguardando liberação do RT',
    icone: Icone.Caixa, componente: 'estoque_indicador', params: { metrica: 'lotes_em_quarentena' } },
  { id: 'bloqueados', rotulo: 'Bloqueados', sub: 'fora de circulação',
    icone: Icone.Lote, componente: 'estoque_indicador', params: { metrica: 'lotes_bloqueados' } },
]

export function PainelNavegacao({
  atual, aoAbrir,
}: { atual: string | null; aoAbrir: (i: ItemNav) => void }) {
  return (
    <div className="painel">
      <div className="painel-cabeca"><span className="titulo-painel">Navegação</span></div>
      <div className="painel-corpo">
        {MENU.map((i) => (
          <button
            key={i.id}
            className={`nav-item ${atual === i.id ? 'is-atual' : ''}`}
            onClick={() => aoAbrir(i)}
            aria-current={atual === i.id ? 'page' : undefined}
          >
            <span className="nav-icone"><i.icone tamanho={18} /></span>
            <span className="nav-titulo">{i.rotulo}</span>
            <span className="nav-sub">{i.sub}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
