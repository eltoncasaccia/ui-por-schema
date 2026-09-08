import { BarraFaixas } from '../ui/BarraFaixas'
import { Tabela, type Coluna } from '../ui/Tabela'
import { SITUACAO, classeTexto } from '../ui/estados'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { dataBr } from './fila_vencimento'
import { UNIDADE } from './lote_lista'

type VM = ViewModel<'quarentena_fila'>
type Linha = VM['linhas'][number]

const CLASSE: Record<Linha['classe'], string> = {
  comum: 'Comum',
  controlado: 'Controlado',
  termolabil: 'Termolábil',
  antimicrobiano: 'Antimicrobiano',
}

const COLUNAS: Coluna<Linha>[] = [
  { chave: 'produto', rotulo: 'Produto', render: (l) => l.produto },
  { chave: 'numero', rotulo: 'Lote', render: (l) => <span className="mono fraco">{l.numero}</span> },
  { chave: 'unidade', rotulo: 'Unidade', campo: true, render: (l) => UNIDADE[l.unidade] ?? l.unidade },
  { chave: 'classe', rotulo: 'Classe', campo: true, render: (l) => CLASSE[l.classe] },
  {
    // A idade na fila é o que ordena o trabalho do RT — não a validade.
    // Lote parado há 11 dias na quarentena é dinheiro imobilizado e prateleira
    // ocupada, mesmo que vença só daqui a dois anos.
    chave: 'parado', rotulo: 'Parado há', num: true, campo: true,
    render: (l) => <span className="mono">{l.fabricado_ha_dias} d</span>,
  },
  {
    chave: 'validade', rotulo: 'Validade', campo: true,
    render: (l) => <span className="mono">{dataBr(l.validade)}</span>,
  },
  {
    chave: 'dias', rotulo: 'Dias', num: true, campo: true,
    render: (l) => (
      <span className={classeTexto(SITUACAO[l.situacao].tom)}>
        {l.dias_restantes < 0 ? `−${Math.abs(l.dias_restantes)}` : l.dias_restantes}
      </span>
    ),
  },
  { chave: 'saldo', rotulo: 'Saldo', num: true, campo: true, render: (l) => l.saldo.toLocaleString('pt-BR') },
]

/**
 * A fila de quarentena abre com o número que dói: quantos já venceram parados.
 *
 * Um lote que vence DENTRO da quarentena é a pior combinação do sistema — foi
 * pago, foi recebido, ocupou geladeira e nunca chegou a ser vendável. Somar
 * esse caso no total geral o esconderia; ele aparece separado, e some da tela
 * quando é zero, porque um contador cravado em zero deixa de ser lido.
 */
export const view: View<'quarentena_fila'> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">Fila de quarentena</span>
      <span className="mono fraco" style={{ fontSize: 11 }}>{vm.escopo}</span>
    </div>
    {vm.total > 0 && (
      <div className="cartao-corpo" style={{ paddingBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 22, fontWeight: 600 }}>{vm.total}</span>
          <span className="suave" style={{ fontSize: 13 }}>
            lote{vm.total === 1 ? '' : 's'} aguardando liberação
          </span>
          {vm.vencidos > 0 && (
            <span className="etiqueta etiqueta-ruim">
              {vm.vencidos} venceu{vm.vencidos === 1 ? '' : 'ram'} na fila
            </span>
          )}
        </div>
        <BarraFaixas faixas={vm.resumo} tipo="unidade" />
      </div>
    )}
    <Tabela
      colunas={COLUNAS}
      linhas={vm.linhas}
      // Id, nunca número: dois lotes de mesmo número em unidades diferentes são
      // registros distintos (RN-L08).
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
