import { Tabela, type Coluna } from '../ui/Tabela'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { dataBr } from './fila_vencimento'

type VM = ViewModel<'rastreabilidade'>
type LinhaCliente = NonNullable<VM['clientes']>[number]
type LinhaLote = NonNullable<VM['lotes']>[number]

const COL_CLIENTE: Coluna<LinhaCliente>[] = [
  { chave: 'cliente', rotulo: 'Cliente', render: (l) => l.cliente },
  {
    chave: 'nota_fiscal', rotulo: 'Nota fiscal', campo: true,
    render: (l) => l.nota_fiscal ? <span className="mono fraco">{l.nota_fiscal}</span> : <span className="fraco">—</span>,
  },
  { chave: 'data', rotulo: 'Data', campo: true, render: (l) => <span className="mono">{dataBr(l.data)}</span> },
  { chave: 'quantidade', rotulo: 'Qtd.', num: true, campo: true, render: (l) => l.quantidade.toLocaleString('pt-BR') },
]

const COL_LOTE: Coluna<LinhaLote>[] = [
  { chave: 'produto', rotulo: 'Produto', render: (l) => l.produto },
  { chave: 'numero', rotulo: 'Lote', campo: true, render: (l) => <span className="mono fraco">{l.numero}</span> },
  { chave: 'quantidade_total', rotulo: 'Qtd. total', num: true, campo: true, render: (l) => l.quantidade_total.toLocaleString('pt-BR') },
  { chave: 'primeira', rotulo: 'Primeira', campo: true, render: (l) => <span className="mono">{dataBr(l.primeira)}</span> },
  { chave: 'ultima', rotulo: 'Última', campo: true, render: (l) => <span className="mono">{dataBr(l.ultima)}</span> },
]

/**
 * Rastreabilidade nas duas direções (RN-D03 / RN-D04). O topo diz sempre QUAL
 * consulta é esta — alvo e recorte — porque é o que uma resposta a órgão
 * regulador precisa carregar junto com os números.
 *
 * Só uma das duas listas vem preenchida; `direcao` decide qual.
 */
export const view: View<'rastreabilidade'> = ({ vm }) => {
  const porLote = vm.direcao === 'lote_para_clientes'
  return (
    <div className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">
          {porLote ? 'Clientes do lote' : 'Lotes do cliente'}
        </span>
        <span className="mono fraco" style={{ fontSize: 11 }}>{vm.alvo}</span>
      </div>
      <div className="cartao-corpo" style={{ paddingBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 22, fontWeight: 600 }}>{vm.total_saidas.toLocaleString('pt-BR')}</span>
          <span className="suave" style={{ fontSize: 13 }}>
            saída{vm.total_saidas === 1 ? '' : 's'} · {vm.total_quantidade.toLocaleString('pt-BR')} unidades · {vm.recorte}
          </span>
        </div>
      </div>
      {porLote ? (
        <Tabela
          colunas={COL_CLIENTE}
          linhas={vm.clientes ?? []}
          chave={(l) => `${l.cliente}·${l.nota_fiscal ?? ''}·${l.data}`}
          titulo={(l) => <div style={{ fontWeight: 500 }}>{l.cliente}</div>}
        />
      ) : (
        <Tabela
          colunas={COL_LOTE}
          linhas={vm.lotes ?? []}
          chave={(l) => l.lote_id}
          titulo={(l) => (
            <>
              <div style={{ fontWeight: 500, overflowWrap: 'anywhere' }}>{l.produto}</div>
              <div className="mono fraco" style={{ fontSize: 11, marginTop: 2 }}>lote {l.numero}</div>
            </>
          )}
        />
      )}
    </div>
  )
}
