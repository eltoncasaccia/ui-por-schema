import { useState } from 'react'
import { dispararComando } from '../render/comando'
import { SITUACAO, classeTexto } from '../ui/estados'
import { Etiqueta } from '../ui/Etiqueta'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { dataBr } from './fila_vencimento'
import { STATUS_LOTE } from './lote_lista'

type VM = ViewModel<'lote_status_acao'>
type Acao = VM['acoes'][number]['acao']

/**
 * As três transições privativas do RT, num formulário só (ADR-0011).
 *
 * A tela responde à pergunta real de quem a abre — *o que eu posso fazer com
 * este lote agora?* — e a resposta vem pronta do servidor: cada ação chega com
 * `disponivel` e, quando não está, com o motivo. **A view não avalia a máquina
 * de estados**; se avaliasse, haveria duas cópias da tabela §4.1 e elas
 * divergiriam.
 *
 * Desabilitar aqui é cortesia, não controle. O servidor recusa de novo, com a
 * identidade real, mesmo que alguém remova o `disabled` no inspetor (`RN-A03`).
 *
 * O motivo aparece ao lado de cada ação indisponível em vez de num aviso geral:
 * a pergunta "por que não posso desbloquear?" é sobre aquela linha, e uma nota
 * de rodapé obriga o olho a ligar as duas coisas sozinho.
 */
export const view: View<'lote_status_acao'> = ({ vm }) => {
  const [escolhida, setEscolhida] = useState<Acao | null>(null)
  const [justificativa, setJustificativa] = useState('')

  const justificado = justificativa.trim().length >= 10
  const divergem = vm.status !== vm.status_efetivo

  return (
    <div className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">Situação · lote {vm.numero}</span>
        <div style={{ display: 'flex', gap: 6 }}>
          <Etiqueta tom={STATUS_LOTE[vm.status_efetivo].tom}>
            {STATUS_LOTE[vm.status_efetivo].rotulo}
          </Etiqueta>
          {/* ADR-0022: os dois status, e só quando diferem. Repetir a mesma
              palavra duas vezes ensina o olho a ignorar as duas. */}
          {divergem && (
            <Etiqueta tom="neutro">registrado: {STATUS_LOTE[vm.status].rotulo}</Etiqueta>
          )}
        </div>
      </div>

      <div className="cartao-corpo">
        <div style={{ fontWeight: 500, fontSize: 15, overflowWrap: 'anywhere' }}>{vm.produto}</div>

        <div className="linha-cartao-campos" style={{ marginTop: 12 }}>
          <div>
            <div className="campo-rotulo">Unidade</div>
            <div className="campo-valor">{vm.unidade}</div>
          </div>
          <div>
            <div className="campo-rotulo">Saldo</div>
            <div className="campo-valor">{vm.saldo.toLocaleString('pt-BR')}</div>
          </div>
          <div>
            <div className="campo-rotulo">Validade</div>
            <div className="campo-valor">
              <span className="mono">{dataBr(vm.validade)}</span>
            </div>
          </div>
          <div>
            <div className="campo-rotulo">Dias restantes</div>
            <div className="campo-valor">
              <span className={classeTexto(SITUACAO[vm.situacao].tom)}>
                {vm.dias_restantes < 0 ? `−${Math.abs(vm.dias_restantes)}` : vm.dias_restantes}
              </span>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <div className="campo-rotulo">Ação</div>
          <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0' }}>
            {vm.acoes.map((a) => (
              <li key={a.acao} style={{ margin: '6px 0' }}>
                <label
                  style={{
                    display: 'flex',
                    gap: 8,
                    alignItems: 'baseline',
                    fontSize: 13,
                    opacity: a.disponivel ? 1 : 0.55,
                  }}
                >
                  <input
                    type="radio"
                    name="acao-status"
                    checked={escolhida === a.acao}
                    disabled={!a.disponivel}
                    onChange={() => setEscolhida(a.acao)}
                  />
                  <span>
                    {a.rotulo}
                    {a.motivo && (
                      <span className="fraco" style={{ display: 'block', fontSize: 12 }}>
                        {a.motivo}
                      </span>
                    )}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </div>

        <div style={{ marginTop: 16 }}>
          <label className="campo-rotulo" htmlFor="justificativa-status">
            Justificativa
          </label>
          <textarea
            id="justificativa-status"
            value={justificativa}
            disabled={escolhida === null}
            onChange={(e) => setJustificativa(e.target.value)}
            rows={2}
            style={{ width: '100%', marginTop: 6, font: 'inherit' }}
          />
        </div>

        <div style={{ marginTop: 16 }}>
          <button type="button" disabled={escolhida === null || !justificado} data-acao={escolhida ?? ''}
            onClick={(e) => {
              if (!escolhida) return
              dispararComando(e.currentTarget, {
                acao: 'lote_status',
                corpo: { lote_id: vm.lote_id, acao: escolhida, justificativa },
              })
            }}>
            Aplicar
          </button>
        </div>
      </div>
    </div>
  )
}
