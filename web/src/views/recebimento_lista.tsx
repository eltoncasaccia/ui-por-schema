import { Etiqueta } from '../ui/Etiqueta'
import type { Tom } from '../ui/estados'
import { Tabela, type Coluna } from '../ui/Tabela'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'

type VM = ViewModel<'recebimento_lista'>
type Linha = VM['linhas'][number]

/**
 * O estado da conferência, não um nível: `rascunho` é neutro (ainda não olharam),
 * `conferido` é ciano (conferência feita, aguardando o RT), `liberado` é bom.
 */
export const STATUS_RECEBIMENTO: Record<Linha['status'], { rotulo: string; tom: Tom }> = {
  rascunho: { rotulo: 'Rascunho', tom: 'neutro' },
  conferido: { rotulo: 'Conferido', tom: 'ciano' },
  liberado: { rotulo: 'Liberado', tom: 'bom' },
}

function horaBr(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

const COLUNAS: Coluna<Linha>[] = [
  {
    chave: 'recebido_em',
    rotulo: 'Quando',
    render: (l) => <span className="mono">{horaBr(l.recebido_em)}</span>,
  },
  { chave: 'fornecedor', rotulo: 'Fornecedor', campo: true, render: (l) => l.fornecedor },
  {
    chave: 'nota_fiscal',
    rotulo: 'Nota',
    campo: true,
    render: (l) => <span className="mono fraco">{l.nota_fiscal}</span>,
  },
  {
    chave: 'status',
    rotulo: 'Situação',
    render: (l) => (
      <span>
        <Etiqueta tom={STATUS_RECEBIMENTO[l.status].tom}>{STATUS_RECEBIMENTO[l.status].rotulo}</Etiqueta>
        {/* RN-R04: a divergência é sinal, não bloqueio. Âmbar (resolver), não
            vermelho (terminal): o recebimento conclui com a pendência aberta. */}
        {l.divergencia && (
          <span className="fraco" style={{ display: 'block', fontSize: 11 }}>
            <Etiqueta tom="ambar">divergência</Etiqueta>
          </span>
        )}
      </span>
    ),
  },
]

/**
 * O que entrou, e em que estado da conferência está (T-022).
 *
 * **Não há ação nesta tela.** Registrar recebimento é T-026, liberar quarentena
 * é T-027 — o componente não declara `commands`, e é isso que garante que a
 * interface não ofereça o caminho.
 *
 * O contador de divergências aparece no cabeçalho mesmo quando o filtro não é
 * esse: uma pendência aberta trava a conclusão do recebimento, e quem varre a
 * lista precisa ver quantas há sem abrir uma por uma.
 */
export const view: View<'recebimento_lista'> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">
        {vm.total.toLocaleString('pt-BR')} {vm.total === 1 ? 'recebimento' : 'recebimentos'}
      </span>
      <span className="mono fraco" style={{ fontSize: 11 }}>
        {vm.escopo} · {vm.recorte}
      </span>
    </div>

    <div className="cartao-corpo">
      {vm.com_divergencia > 0 && (
        <p style={{ margin: '0 0 12px', fontSize: 13 }}>
          <Etiqueta tom="ambar">
            {vm.com_divergencia} com divergência a resolver
          </Etiqueta>
        </p>
      )}

      {vm.total === 0 ? (
        <p className="fraco" style={{ fontSize: 13, margin: 0 }}>
          Nenhum recebimento neste recorte.
        </p>
      ) : (
        <Tabela
          colunas={COLUNAS}
          linhas={vm.linhas}
          chave={(l) => l.recebimento_id}
          titulo={(l) => <span>{l.fornecedor}</span>}
          etiqueta={(l) => ({
            texto: STATUS_RECEBIMENTO[l.status].rotulo,
            tom: STATUS_RECEBIMENTO[l.status].tom,
          })}
        />
      )}
    </div>
  </div>
)
