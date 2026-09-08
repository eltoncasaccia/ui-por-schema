import { SITUACAO, classeTexto } from '../ui/estados'
import { Etiqueta } from '../ui/Etiqueta'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { dataBr } from './fila_vencimento'
import { STATUS_LOTE, UNIDADE } from './lote_lista'

type VM = ViewModel<'lote_detalhe'>

/** A classe regulatória muda o que a lei exige do lote, não só a aparência. */
const CLASSE: Record<VM['classe'], string> = {
  comum: 'Comum',
  controlado: 'Controlado',
  termolabil: 'Termolábil',
  antimicrobiano: 'Antimicrobiano',
}

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="campo-rotulo">{rotulo}</div>
      <div className="campo-valor">{children}</div>
    </div>
  )
}

/**
 * O detalhe mostra os DOIS status, lado a lado (ADR-0022).
 *
 * `status_registrado` é o que uma pessoa decidiu e o banco guardou.
 * `status_efetivo` é o que vale agora, e inclui `vencido` e `esgotado`, que
 * ninguém digita — saem da data e do saldo. Mostrar só o efetivo esconderia
 * que a decisão humana continua sendo `liberado`, e é essa decisão que o RT
 * precisa reverter. Mostrar só o registrado é o bug que o ADR-0022 nomeia:
 * a tela diria "Liberado" sobre um lote vencido ontem.
 *
 * Quando os dois coincidem, a segunda etiqueta some — repetir a mesma palavra
 * duas vezes ensina o olho a ignorar as duas.
 */
export const view: View<'lote_detalhe'> = ({ vm }) => {
  const divergem = vm.status_registrado !== vm.status_efetivo
  return (
    <div className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">Lote {vm.numero}</span>
        <span className="mono fraco" style={{ fontSize: 11 }}>
          {UNIDADE[vm.unidade] ?? vm.unidade}
        </span>
      </div>
      <div className="cartao-corpo">
        <div style={{ fontWeight: 500, fontSize: 15, overflowWrap: 'anywhere' }}>{vm.produto}</div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', margin: '8px 0 4px' }}>
          <Etiqueta tom={STATUS_LOTE[vm.status_efetivo].tom}>
            {STATUS_LOTE[vm.status_efetivo].rotulo}
          </Etiqueta>
          {divergem && (
            <Etiqueta tom="neutro">registrado: {STATUS_LOTE[vm.status_registrado].rotulo}</Etiqueta>
          )}
          <Etiqueta tom="neutro">{CLASSE[vm.classe]}</Etiqueta>
        </div>

        <div className="linha-cartao-campos" style={{ marginTop: 12 }}>
          <Campo rotulo="Saldo">{vm.saldo.toLocaleString('pt-BR')}</Campo>
          <Campo rotulo="Validade">
            <span className="mono">{dataBr(vm.validade)}</span>
          </Campo>
          <Campo rotulo="Dias restantes">
            {/* Minus tipográfico, não hífen: alinha com os dígitos tabulares. */}
            <span className={classeTexto(SITUACAO[vm.situacao].tom)}>
              {vm.dias_restantes < 0 ? `−${Math.abs(vm.dias_restantes)}` : vm.dias_restantes}
            </span>
          </Campo>
          <Campo rotulo="Fabricação">
            <span className="mono">{dataBr(vm.fabricacao)}</span>
          </Campo>
          <Campo rotulo="Endereço">
            {vm.endereco ? (
              <span className="mono">{vm.endereco}</span>
            ) : (
              <span className="fraco">—</span>
            )}
          </Campo>
          {/* O id aparece porque número NÃO identifica lote (RN-L08): é ele
              que a pessoa cita ao telefone quando dois lotes têm o mesmo
              número em unidades diferentes. */}
          <Campo rotulo="Identificador">
            <span className="mono fraco">{vm.lote_id}</span>
          </Campo>
        </div>
      </div>
    </div>
  )
}
