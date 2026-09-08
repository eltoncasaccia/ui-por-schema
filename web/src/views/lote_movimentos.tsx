import { Tabela, type Coluna } from '../ui/Tabela'
import { classeTexto, type Tom } from '../ui/estados'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { UNIDADE } from './lote_lista'

type VM = ViewModel<'lote_movimentos'>
type Linha = VM['linhas'][number]

/**
 * O sinal do movimento é do TIPO, não da quantidade.
 *
 * A quantidade é sempre positiva no domínio — quem decide se soma ou subtrai é
 * o tipo. Guardar quantidade negativa faria `saida` de −10 e estorno de saída
 * virar +10, e um bug de sinal em movimento imutável (RN-M02) não tem como ser
 * corrigido depois: só resta um estorno explicando o erro.
 */
const TIPO: Record<Linha['tipo'], { rotulo: string; sinal: '+' | '−'; tom: Tom }> = {
  entrada: { rotulo: 'Entrada', sinal: '+', tom: 'bom' },
  saida: { rotulo: 'Saída', sinal: '−', tom: 'neutro' },
  descarte: { rotulo: 'Descarte', sinal: '−', tom: 'ruim' },
  estorno: { rotulo: 'Estorno', sinal: '+', tom: 'ambar' },
}

const MOTIVO: Record<Linha['motivo'], string> = {
  recebimento: 'Recebimento',
  venda: 'Venda',
  transferencia: 'Transferência',
  avaria: 'Avaria',
  furto: 'Furto',
  erro_de_separacao: 'Erro de separação',
  erro_de_recebimento: 'Erro de recebimento',
  vencimento: 'Vencimento',
  erro_de_contagem_anterior: 'Erro de contagem anterior',
  estorno: 'Estorno',
}

/** `aguardando_autorizacao` é a dupla identificação de controlado (CA-04). */
const STATUS: Record<Linha['status'], { rotulo: string; tom: Tom }> = {
  efetivado: { rotulo: 'Efetivado', tom: 'neutro' },
  aguardando_autorizacao: { rotulo: 'Aguardando autorização', tom: 'ambar' },
  recusado: { rotulo: 'Recusado', tom: 'ruim' },
}

function horaBr(iso: string): string {
  const [data, resto] = iso.split('T')
  const [a, m, d] = (data ?? '').split('-')
  const hm = (resto ?? '').slice(0, 5)
  return d && m && a ? `${d}/${m}/${a} ${hm}`.trim() : iso
}

const COLUNAS: Coluna<Linha>[] = [
  {
    chave: 'criado_em', rotulo: 'Quando', campo: true,
    render: (l) => <span className="mono fraco">{horaBr(l.criado_em)}</span>,
  },
  {
    chave: 'tipo', rotulo: 'Tipo', campo: true,
    render: (l) => <span className={classeTexto(TIPO[l.tipo].tom)}>{TIPO[l.tipo].rotulo}</span>,
  },
  { chave: 'motivo', rotulo: 'Motivo', campo: true, render: (l) => MOTIVO[l.motivo] },
  {
    chave: 'quantidade', rotulo: 'Qtd', num: true, campo: true,
    render: (l) => (
      <span className={classeTexto(TIPO[l.tipo].tom)}>
        {TIPO[l.tipo].sinal}
        {l.quantidade.toLocaleString('pt-BR')}
      </span>
    ),
  },
  {
    chave: 'saldo_apos', rotulo: 'Saldo após', num: true, campo: true,
    render: (l) => <span className="mono">{l.saldo_apos.toLocaleString('pt-BR')}</span>,
  },
  {
    chave: 'autor', rotulo: 'Autor', campo: true,
    render: (l) => (
      <span className="mono fraco">
        {l.autor_id}
        {/* Os dois ids juntos SÃO a evidência da dupla identificação: separá-los
            em telas diferentes é o que faz uma auditoria não conseguir provar
            que houve duas pessoas. */}
        {l.autorizador_id && <> · aut. {l.autorizador_id}</>}
      </span>
    ),
  },
  {
    chave: 'status', rotulo: 'Status',
    render: (l) => (
      <span className={`etiqueta etiqueta-${STATUS[l.status].tom}`}>{STATUS[l.status].rotulo}</span>
    ),
  },
]

/**
 * A trilha de um lote, do recebimento até agora.
 *
 * Movimento é imutável (RN-M02): nada aqui é edição, tudo é acréscimo. Por isso
 * a coluna `saldo_apos` existe — ela deixa a conta conferível linha a linha, e
 * um estorno aparece como LINHA NOVA que aponta para a original, nunca como a
 * original alterada.
 */
export const view: View<'lote_movimentos'> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">Movimentos do lote {vm.numero}</span>
      <span className="mono fraco" style={{ fontSize: 11 }}>
        {UNIDADE[vm.unidade] ?? vm.unidade}
      </span>
    </div>
    <div className="cartao-corpo" style={{ paddingBottom: 4 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 22, fontWeight: 600 }}>{vm.saldo_atual.toLocaleString('pt-BR')}</span>
        <span className="suave" style={{ fontSize: 13 }}>
          em saldo · {vm.total} movimento{vm.total === 1 ? '' : 's'}
          {vm.periodo_dias !== null ? ` nos últimos ${vm.periodo_dias} dias` : ''}
        </span>
      </div>
      <div className="suave" style={{ fontSize: 13, marginTop: 2, overflowWrap: 'anywhere' }}>
        {vm.produto}
      </div>
    </div>
    <Tabela
      colunas={COLUNAS}
      linhas={vm.linhas}
      chave={(l) => l.movimento_id}
      titulo={(l) => (
        <>
          <div style={{ fontWeight: 500 }}>
            {TIPO[l.tipo].rotulo} · {MOTIVO[l.motivo]}
          </div>
          <div className="mono fraco" style={{ fontSize: 11, marginTop: 2 }}>
            {horaBr(l.criado_em)}
          </div>
        </>
      )}
      etiqueta={(l) => ({ texto: STATUS[l.status].rotulo, tom: STATUS[l.status].tom })}
    />
  </div>
)
