import { Etiqueta } from '../ui/Etiqueta'
import type { Tom } from '../ui/estados'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { UNIDADE } from './lote_lista'

type VM = ViewModel<'recebimento_detalhe'>

const STATUS: Record<VM['status'], { rotulo: string; tom: Tom }> = {
  rascunho: { rotulo: 'Rascunho', tom: 'neutro' },
  conferido: { rotulo: 'Conferido', tom: 'ciano' },
  liberado: { rotulo: 'Liberado', tom: 'bom' },
}

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="campo-rotulo">{rotulo}</div>
      <div className="campo-valor">{children}</div>
    </div>
  )
}

function horaBr(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

/**
 * UM recebimento, com o que decide se ele pode concluir (T-022).
 *
 * **As duas identificações, sempre que houver as duas** (`RN-R05`). O responsável
 * técnico só é preenchido em recebimento de controlado, e é ele o sinal de que a
 * dupla identificação aconteceu — por isso a linha aparece condicionalmente, e
 * mostrar só o conferente esconderia metade do que a regra exige.
 *
 * **A temperatura de chegada aparece só em carga termolábil** (`RN-F01`): é
 * `null` para o resto, e um campo vazio ali sugeriria uma medição que não se
 * exige.
 *
 * **A divergência é um aviso, não um estado** (`RN-R04`): fica ao lado do status,
 * não no lugar dele — o recebimento conclui com a pendência aberta.
 */
export const view: View<'recebimento_detalhe'> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">{vm.fornecedor}</span>
      <span className="mono fraco" style={{ fontSize: 11 }}>
        {UNIDADE[vm.unidade] ?? vm.unidade}
      </span>
    </div>
    <div className="cartao-corpo">
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', margin: '0 0 4px' }}>
        <Etiqueta tom={STATUS[vm.status].tom}>{STATUS[vm.status].rotulo}</Etiqueta>
        {vm.tem_pendencia_divergencia && (
          <Etiqueta tom="ambar">divergência entre nota e físico</Etiqueta>
        )}
        {vm.temperatura_chegada_c != null && <Etiqueta tom="neutro">termolábil</Etiqueta>}
      </div>

      <div className="linha-cartao-campos" style={{ marginTop: 12 }}>
        <Campo rotulo="Nota fiscal">
          <span className="mono">{vm.nota_fiscal}</span>
        </Campo>
        <Campo rotulo="Recebido em">
          <span className="mono">{horaBr(vm.recebido_em)}</span>
        </Campo>
        <Campo rotulo="Conferente">
          <span className="mono">{vm.conferente}</span>
        </Campo>
        {/* RN-R05: a segunda identidade, quando o recebimento é de controlado. */}
        {vm.responsavel_tecnico && (
          <Campo rotulo="Responsável técnico">
            <span className="mono">{vm.responsavel_tecnico}</span>
          </Campo>
        )}
        {/* RN-F01: só em termolábil. */}
        {vm.temperatura_chegada_c != null && (
          <Campo rotulo="Temperatura de chegada">
            <span className="mono">
              {vm.temperatura_chegada_c.toLocaleString('pt-BR', { minimumFractionDigits: 1 })} °C
            </span>
          </Campo>
        )}
        <Campo rotulo="Identificador">
          <span className="mono fraco">{vm.recebimento_id}</span>
        </Campo>
      </div>

      {vm.tem_pendencia_divergencia && (
        <p className="fraco" style={{ fontSize: 12, margin: '12px 0 0' }}>
          Há divergência entre a nota e o físico. A pendência fica vinculada ao
          recebimento e não impede a conclusão.
        </p>
      )}
    </div>
  </div>
)
