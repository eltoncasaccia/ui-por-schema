import { BarraFaixas } from '../ui/BarraFaixas'
import { Tabela, type Coluna } from '../ui/Tabela'
import { SITUACAO, classeTexto, type Tom } from '../ui/estados'
import type { ViewModel } from '../generated/componentes'
import type { View } from './tipos'
import { dataBr } from './fila_vencimento'

type VM = ViewModel<'lote_lista'>
export type Linha = VM['linhas'][number]

/** O status efetivo (ADR-0022) — o que vale agora, não o que está gravado. */
export type StatusLote = Linha['status']

export const UNIDADE: Record<string, string> = {
  'cd-matriz': 'CD Matriz',
  'cd-refrigerado': 'CD Refrigerado',
  'filial-uberlandia': 'Uberlândia',
}

/**
 * Semântica visual do status do lote.
 *
 * `bloqueado` e `vencido` recebem matizes DIFERENTES de propósito: bloqueado é
 * uma decisão humana reversível — o RT desbloqueia — e vencido é terminal. Um
 * único tom de "ruim" apagaria a diferença entre ligar para o RT e recolher da
 * prateleira. `descartado` e `esgotado` são neutros: nada a fazer, nada a
 * alarmar.
 */
export const STATUS_LOTE: Record<StatusLote, { rotulo: string; tom: Tom }> = {
  quarentena: { rotulo: 'Quarentena', tom: 'ciano' },
  liberado: { rotulo: 'Liberado', tom: 'bom' },
  bloqueado: { rotulo: 'Bloqueado', tom: 'laranja' },
  descartado: { rotulo: 'Descartado', tom: 'neutro' },
  vencido: { rotulo: 'Vencido', tom: 'ruim' },
  esgotado: { rotulo: 'Esgotado', tom: 'neutro' },
}

const COLUNAS: Coluna<Linha>[] = [
  { chave: 'produto', rotulo: 'Produto', render: (l) => l.produto },
  { chave: 'numero', rotulo: 'Lote', render: (l) => <span className="mono fraco">{l.numero}</span> },
  // Unidade é campo no modo cartão porque é ela que distingue dois lotes de
  // mesmo número (RN-L08). Escondê-la faria duas linhas parecerem duplicata.
  { chave: 'unidade', rotulo: 'Unidade', campo: true, render: (l) => UNIDADE[l.unidade] ?? l.unidade },
  { chave: 'validade', rotulo: 'Validade', campo: true, render: (l) => <span className="mono">{dataBr(l.validade)}</span> },
  {
    chave: 'dias', rotulo: 'Dias', num: true, campo: true,
    // Minus tipográfico, não hífen: alinha com os dígitos tabulares.
    render: (l) => (
      <span className={classeTexto(SITUACAO[l.situacao].tom)}>
        {l.dias_restantes < 0 ? `−${Math.abs(l.dias_restantes)}` : l.dias_restantes}
      </span>
    ),
  },
  { chave: 'saldo', rotulo: 'Saldo', num: true, campo: true, render: (l) => l.saldo.toLocaleString('pt-BR') },
  {
    chave: 'endereco', rotulo: 'Endereço', campo: true,
    render: (l) => l.endereco ? <span className="mono fraco">{l.endereco}</span> : <span className="fraco">—</span>,
  },
  {
    chave: 'status', rotulo: 'Status',
    render: (l) => <span className={`etiqueta etiqueta-${STATUS_LOTE[l.status].tom}`}>{STATUS_LOTE[l.status].rotulo}</span>,
  },
]

/**
 * A lista diz, no topo, QUAL RECORTE ela representa.
 *
 * É o contrapeso do risco R-5: um filtro que o modelo esqueceu devolve uma
 * lista maior, e uma lista maior parece uma resposta boa. Escrever o recorte na
 * tela transforma "alargou em silêncio" em "alargou, e está escrito ali".
 */
export const view: View<'lote_lista'> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">Lotes</span>
      <span className="mono fraco" style={{ fontSize: 11 }}>{vm.escopo}</span>
    </div>
    {vm.total > 0 && (
      <div className="cartao-corpo" style={{ paddingBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 22, fontWeight: 600 }}>{vm.total}</span>
          <span className="suave" style={{ fontSize: 13 }}>
            lote{vm.total === 1 ? '' : 's'}
            {vm.recorte && vm.recorte.length > 0 ? ` · ${vm.recorte.join(' · ')}` : ''}
          </span>
        </div>
        {/* Status é identidade, não magnitude: barra neutra, sem rampa. */}
        <BarraFaixas faixas={vm.resumo} tipo="unidade" />
      </div>
    )}
    <Tabela
      colunas={COLUNAS}
      linhas={vm.linhas}
      // A chave é o id do lote, nunca o número: dois lotes de mesmo número em
      // unidades diferentes são registros distintos (RN-L08), e chavear pelo
      // número faria o React tratar os dois como o mesmo.
      chave={(l) => l.lote_id}
      titulo={(l) => (
        <>
          <div style={{ fontWeight: 500, overflowWrap: 'anywhere' }}>{l.produto}</div>
          <div className="mono fraco" style={{ fontSize: 11, marginTop: 2 }}>lote {l.numero}</div>
        </>
      )}
      etiqueta={(l) => ({ texto: STATUS_LOTE[l.status].rotulo, tom: STATUS_LOTE[l.status].tom })}
    />
  </div>
)
