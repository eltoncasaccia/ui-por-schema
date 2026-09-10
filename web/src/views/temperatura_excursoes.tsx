import { Etiqueta } from '../ui/Etiqueta'
import type { Tom } from '../ui/estados'
import { Tabela, type Coluna } from '../ui/Tabela'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { STATUS_LOTE, UNIDADE } from './lote_lista'

type VM = ViewModel<'temperatura_excursoes'>
type Excursao = VM['excursoes'][number]
type LotePresente = Excursao['lotes'][number]

const SENTIDO: Record<Excursao['sentido'], { rotulo: string; tom: Tom }> = {
  calor: { rotulo: 'Calor', tom: 'laranja' },
  frio: { rotulo: 'Frio', tom: 'ciano' },
}

function dataBr(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-BR')
}
function horaBr(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

const COLUNAS: Coluna<LotePresente>[] = [
  { chave: 'numero', rotulo: 'Lote', render: (l) => <span className="mono">{l.numero}</span> },
  { chave: 'produto', rotulo: 'Produto', campo: true, render: (l) => l.produto },
  {
    chave: 'status',
    rotulo: 'Status',
    render: (l) => (
      <Etiqueta tom={STATUS_LOTE[l.status]?.tom ?? 'neutro'}>
        {STATUS_LOTE[l.status]?.rotulo ?? l.status}
      </Etiqueta>
    ),
  },
  {
    chave: 'entrou_em',
    rotulo: 'Entrou em',
    campo: true,
    render: (l) => <span className="mono fraco">{horaBr(l.entrou_em)}</span>,
  },
]

/**
 * Cada excursão é uma ocorrência: quando começou, quanto durou, o pico, e — o
 * que a inspeção pede (`RN-F04`) — os lotes que estavam na câmara no período.
 *
 * A lista de lotes é o vínculo, não um enfeite: um lote que entrou depois da
 * excursão não aparece, porque não foi exposto. Sem esse corte, a ocorrência
 * viria com o estoque inteiro e não provaria nada.
 */
function CartaoExcursao({ ex }: { ex: Excursao }) {
  return (
    <article className="cartao" style={{ marginTop: 12 }}>
      <div className="cartao-cabeca">
        <span className="titulo-painel">
          <Etiqueta tom={SENTIDO[ex.sentido].tom}>{SENTIDO[ex.sentido].rotulo}</Etiqueta>{' '}
          pico {ex.pico_celsius.toLocaleString('pt-BR', { minimumFractionDigits: 1 })} °C
        </span>
        <span className="mono fraco" style={{ fontSize: 11 }}>
          {horaBr(ex.inicio)} — {horaBr(ex.fim)}
        </span>
      </div>
      <div className="cartao-corpo">
        <p className="suave" style={{ fontSize: 13, margin: '0 0 10px' }}>
          {ex.duracao_horas > 0
            ? `${ex.duracao_horas.toLocaleString('pt-BR')} h fora da faixa`
            : 'leitura pontual fora da faixa'}{' '}
          · {ex.leituras} leitura{ex.leituras === 1 ? '' : 's'}
        </p>
        {ex.lotes.length === 0 ? (
          <p className="fraco" style={{ fontSize: 13, margin: 0 }}>
            Nenhum lote estava na unidade neste período.
          </p>
        ) : (
          <>
            <p className="fraco" style={{ fontSize: 12, margin: '0 0 6px' }}>
              {ex.lotes.length} lote{ex.lotes.length === 1 ? '' : 's'} expost
              {ex.lotes.length === 1 ? 'o' : 'os'}:
            </p>
            <Tabela
              colunas={COLUNAS}
              linhas={ex.lotes}
              chave={(l) => l.lote_id}
              titulo={(l) => <span className="mono">{l.numero}</span>}
              etiqueta={(l) => ({
                texto: STATUS_LOTE[l.status]?.rotulo ?? l.status,
                tom: STATUS_LOTE[l.status]?.tom ?? 'neutro',
              })}
            />
          </>
        )}
      </div>
    </article>
  )
}

export const view: View<'temperatura_excursoes'> = ({ vm }) => (
  <section className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">
        Excursões · {UNIDADE[vm.unidade] ?? vm.unidade}
      </span>
      <span className="mono fraco" style={{ fontSize: 11 }}>
        {dataBr(vm.de)} — {dataBr(vm.ate)}
      </span>
    </div>
    <div className="cartao-corpo">
      {vm.total_excursoes === 0 ? (
        <p className="suave" style={{ fontSize: 13, margin: 0 }}>
          Nenhuma excursão de temperatura neste período — a cadeia fria se manteve
          entre {vm.faixa_min_c ?? 2} e {vm.faixa_max_c ?? 8} °C.
        </p>
      ) : (
        <>
          <p className="suave" style={{ fontSize: 13, margin: 0 }}>
            {vm.total_excursoes} ocorrência{vm.total_excursoes === 1 ? '' : 's'} fora da
            faixa de {vm.faixa_min_c ?? 2}–{vm.faixa_max_c ?? 8} °C.
          </p>
          {vm.excursoes.map((ex) => (
            <CartaoExcursao key={`${ex.inicio}-${ex.fim}`} ex={ex} />
          ))}
        </>
      )}
    </div>
  </section>
)
