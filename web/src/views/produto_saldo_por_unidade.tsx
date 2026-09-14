import { Tabela, type Coluna } from '../ui/Tabela'
import { Etiqueta } from '../ui/Etiqueta'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'

type VM = ViewModel<'produto_saldo_por_unidade'>
type Linha = VM['linhas'][number]

const COLUNAS: Coluna<Linha>[] = [
  { chave: 'unidade', rotulo: 'Unidade', render: (l) => l.unidade },
  {
    chave: 'saldo', rotulo: 'Saldo', num: true, campo: true,
    render: (l) => (
      <span>
        {l.saldo.toLocaleString('pt-BR')}
        {l.abaixo_do_minimo && <> <Etiqueta tom="ambar">abaixo do mínimo</Etiqueta></>}
      </span>
    ),
  },
  {
    chave: 'lotes', rotulo: 'Lotes', num: true, campo: true,
    render: (l) => l.lotes.toLocaleString('pt-BR'),
  },
  {
    // RN-P06: a faixa é da unidade, não do produto — cada linha tem a sua.
    chave: 'minimo', rotulo: 'Mín–máx', num: true, campo: true,
    render: (l) =>
      l.minimo == null || l.maximo == null
        ? '—'
        : `${l.minimo.toLocaleString('pt-BR')}–${l.maximo.toLocaleString('pt-BR')}`,
  },
]

/**
 * Onde está o estoque de um produto. RN-P01: produto não tem saldo — o que a
 * tabela mostra é a soma dos lotes de cada unidade, e só das unidades do
 * usuário (a porta já intersectou o escopo). O total no topo é a soma das
 * linhas exibidas, nunca de mais que isso.
 */
export const view: View<'produto_saldo_por_unidade'> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">{vm.nome}</span>
      {!vm.ativo && <Etiqueta tom="laranja">Inativo</Etiqueta>}
    </div>
    <div className="cartao-corpo" style={{ paddingBottom: 4 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 22, fontWeight: 600 }}>{vm.total.toLocaleString('pt-BR')}</span>
        <span className="suave" style={{ fontSize: 13 }}>
          em {vm.linhas.length} unidade{vm.linhas.length === 1 ? '' : 's'}
        </span>
      </div>
    </div>
    <Tabela
      colunas={COLUNAS}
      linhas={vm.linhas}
      chave={(l) => l.unidade_id}
      titulo={(l) => <div style={{ fontWeight: 500 }}>{l.unidade}</div>}
    />
  </div>
)
