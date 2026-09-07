import { BarraFaixas, type Faixa } from '../ui/BarraFaixas'
import { Tabela, type Coluna } from '../ui/Tabela'
import { SITUACAO, classeTexto, type Situacao } from '../ui/estados'
import type { View } from './tipos'

export interface Linha {
  lote_id: string; produto: string; numero: string; unidade: string
  validade: string; dias_restantes: number; saldo: number; situacao: Situacao
}
export interface VM {
  janela_dias: number; total: number; linhas: Linha[]
  resumo: Faixa[]; cursor: string | null; tem_mais: boolean
}

const UNIDADE: Record<string, string> = {
  'cd-matriz': 'CD Matriz',
  'cd-refrigerado': 'CD Refrigerado',
  'filial-uberlandia': 'Uberlândia',
}

export function dataBr(iso: string): string {
  const [a, m, d] = iso.split('-')
  return d && m && a ? `${d}/${m}/${a}` : iso
}

const COLUNAS: Coluna<Linha>[] = [
  { chave: 'produto', rotulo: 'Produto', render: (l) => l.produto },
  { chave: 'numero', rotulo: 'Lote', render: (l) => <span className="mono fraco">{l.numero}</span> },
  { chave: 'unidade', rotulo: 'Unidade', campo: true, render: (l) => UNIDADE[l.unidade] ?? l.unidade },
  { chave: 'validade', rotulo: 'Validade', campo: true, render: (l) => <span className="mono">{dataBr(l.validade)}</span> },
  {
    chave: 'dias', rotulo: 'Dias', num: true, campo: true,
    // O minus tipográfico, não o hífen: alinha com os dígitos tabulares.
    render: (l) => (
      <span className={classeTexto(SITUACAO[l.situacao].tom)}>
        {l.dias_restantes < 0 ? `−${Math.abs(l.dias_restantes)}` : l.dias_restantes}
      </span>
    ),
  },
  { chave: 'saldo', rotulo: 'Saldo', num: true, campo: true, render: (l) => l.saldo.toLocaleString('pt-BR') },
  {
    chave: 'situacao', rotulo: 'Situação',
    render: (l) => <span className={`etiqueta etiqueta-${SITUACAO[l.situacao].tom}`}>{SITUACAO[l.situacao].rotulo}</span>,
  },
]

/**
 * A fila abre com o resumo, não com a primeira linha.
 *
 * "12 lotes" não diz se é grave. A distribuição por urgência responde isso
 * antes de a pessoa ler linha por linha — e cobre a fila INTEIRA, não a página
 * carregada: um resumo que muda ao rolar não é resumo.
 */
export const view: View<VM> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">Fila de vencimento</span>
      <span className="mono fraco" style={{ fontSize: 11 }}>janela {vm.janela_dias} dias</span>
    </div>
    {vm.total > 0 && (
      <div className="cartao-corpo" style={{ paddingBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 22, fontWeight: 600 }}>{vm.total}</span>
          <span className="suave" style={{ fontSize: 13 }}>
            lote{vm.total === 1 ? '' : 's'} com saldo vencendo nesta janela
          </span>
        </div>
        <BarraFaixas faixas={vm.resumo} tipo="urgencia" />
      </div>
    )}
    <Tabela
      colunas={COLUNAS}
      linhas={vm.linhas}
      chave={(l) => l.lote_id}
      titulo={(l) => (
        <>
          <div style={{ fontWeight: 500, overflowWrap: 'anywhere' }}>{l.produto}</div>
          <div className="mono fraco" style={{ fontSize: 11, marginTop: 2 }}>lote {l.numero}</div>
        </>
      )}
      etiqueta={(l) => ({ texto: SITUACAO[l.situacao].rotulo, tom: SITUACAO[l.situacao].tom })}
    />
  </div>
)
