import { Etiqueta } from '../ui/Etiqueta'
import type { Tom } from '../ui/estados'
import { Tabela, type Coluna } from '../ui/Tabela'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'

type VM = ViewModel<'movimento_lista'>
type Linha = VM['linhas'][number]

/** Entrada e estorno somam; saída e descarte subtraem. A cor diz a direção. */
export const TIPO_MOVIMENTO: Record<Linha['tipo'], { rotulo: string; tom: Tom; sinal: string }> = {
  entrada: { rotulo: 'Entrada', tom: 'bom', sinal: '+' },
  estorno: { rotulo: 'Estorno', tom: 'ciano', sinal: '+' },
  saida: { rotulo: 'Saída', tom: 'neutro', sinal: '−' },
  descarte: { rotulo: 'Descarte', tom: 'ruim', sinal: '−' },
}
const TIPO = TIPO_MOVIMENTO

const STATUS: Record<Linha['status'], Tom> = {
  efetivado: 'neutro',
  aguardando_autorizacao: 'ambar',
  recusado: 'ruim',
}

function horaBr(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

const COLUNAS: Coluna<Linha>[] = [
  {
    chave: 'criado_em',
    rotulo: 'Quando',
    render: (l) => <span className="mono">{horaBr(l.criado_em)}</span>,
  },
  {
    chave: 'tipo',
    rotulo: 'Tipo',
    render: (l) => <Etiqueta tom={TIPO[l.tipo].tom}>{TIPO[l.tipo].rotulo}</Etiqueta>,
  },
  {
    chave: 'quantidade',
    rotulo: 'Qtd.',
    num: true,
    // O sinal vem do TIPO, nunca do número (CONTRATOS §3). Mostrá-lo aqui é o
    // que evita ler "10" e ter de lembrar de qual lado ele cai.
    render: (l) => (
      <span className="mono">
        {TIPO[l.tipo].sinal}
        {l.quantidade.toLocaleString('pt-BR')}
      </span>
    ),
  },
  { chave: 'motivo', rotulo: 'Motivo', campo: true, render: (l) => l.motivo },
  {
    chave: 'lote_id',
    rotulo: 'Lote',
    campo: true,
    render: (l) => <span className="mono fraco">{l.lote_id}</span>,
  },
  {
    chave: 'autor',
    rotulo: 'Quem',
    // RN-C01: as duas identidades quando houve autorização. Mostrar só o autor
    // esconderia metade da dupla identificação — que é o ponto dela.
    render: (l) => (
      <span>
        <span className="mono">{l.autor}</span>
        {l.autorizador && (
          <span className="fraco" style={{ display: 'block', fontSize: 11 }}>
            autorizado por <span className="mono">{l.autorizador}</span>
          </span>
        )}
      </span>
    ),
  },
  {
    chave: 'status',
    rotulo: 'Situação',
    render: (l) => (
      <span>
        <Etiqueta tom={STATUS[l.status]}>{l.status_rotulo}</Etiqueta>
        {l.parado_ha_dias != null && l.parado_ha_dias >= 2 && (
          <span className="fraco" style={{ display: 'block', fontSize: 11 }}>
            parado há {l.parado_ha_dias} d
          </span>
        )}
        {/* RN-M03: os dois lados do vínculo. Nada some. */}
        {l.estorna && (
          <span className="fraco" style={{ display: 'block', fontSize: 11 }}>
            estorna <span className="mono">{l.estorna}</span>
          </span>
        )}
        {l.estornado_por && (
          <span className="fraco" style={{ display: 'block', fontSize: 11 }}>
            estornado por <span className="mono">{l.estornado_por}</span>
          </span>
        )}
      </span>
    ),
  },
]

/**
 * Os movimentos, e a fila do RT no mesmo componente (ADR-0011).
 *
 * **Não há ação nenhuma nesta tela**, e é de propósito: `RN-M02` e `CA-08` —
 * movimento não se edita nem se exclui, por ninguém. A garantia não é a ausência
 * de um botão aqui; é o componente não declarar `commands`, o banco recusar
 * `UPDATE`/`DELETE` e o gatilho recusar desfazer um efetivado. Esta view apenas
 * não contradiz as três.
 *
 * **O contador de pendentes aparece mesmo quando o filtro não é esse.** Um
 * controlado esperando autorização é estoque travado e paciente sem remédio; só
 * quem filtrou por ele veria, e quem não filtrou é justamente quem precisa ser
 * avisado.
 */
export const view: View<'movimento_lista'> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">
        {vm.total.toLocaleString('pt-BR')} {vm.total === 1 ? 'movimento' : 'movimentos'}
      </span>
      <span className="mono fraco" style={{ fontSize: 11 }}>
        {vm.escopo} · {vm.recorte}
      </span>
    </div>

    <div className="cartao-corpo">
      {vm.pendentes > 0 && (
        <p style={{ margin: '0 0 12px', fontSize: 13 }}>
          <Etiqueta tom="ambar">
            {vm.pendentes} {vm.pendentes === 1 ? 'aguarda' : 'aguardam'} autorização
          </Etiqueta>
        </p>
      )}

      {vm.total === 0 ? (
        <p className="fraco" style={{ fontSize: 13, margin: 0 }}>
          Nenhum movimento neste recorte.
        </p>
      ) : (
        <Tabela
          colunas={COLUNAS}
          linhas={vm.linhas}
          chave={(l) => l.movimento_id}
          // Em coluna estreita a tabela vira cartão, e este é o título dele:
          // tipo e quantidade, que é o que identifica a linha de relance.
          titulo={(l) => (
            <span>
              {TIPO[l.tipo].rotulo} {TIPO[l.tipo].sinal}
              {l.quantidade.toLocaleString('pt-BR')}
            </span>
          )}
          etiqueta={(l) => ({ texto: l.status_rotulo, tom: STATUS[l.status] })}
        />
      )}
    </div>
  </div>
)
