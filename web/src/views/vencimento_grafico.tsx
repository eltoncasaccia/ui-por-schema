import { useState } from 'react'
import type { View } from './tipos'

import type { ViewModel } from '../generated/componentes'

type VM = ViewModel<'vencimento_grafico'>
export type Balde = VM['baldes'][number]

/**
 * A curva de vencimento — barras verticais por período.
 *
 * O eixo do tempo é ordenado e contínuo, e a pergunta é "onde estão os picos":
 * comparação de magnitude ao longo de uma sequência. Não é pizza (não é
 * parte-de-um-todo) nem linha (são contagens discretas por balde).
 *
 * Um eixo só. Rótulo direto no pico e nas pontas — nunca um número em cada
 * barra, que vira ruído. Hover mostra o valor exato de qualquer barra.
 */
export const view: View<'vencimento_grafico'> = ({ vm }) => {
  const [ativo, setAtivo] = useState<number | null>(null)
  const max = Math.max(...vm.baldes.map((b) => b.lotes), 1)
  const passo = Math.max(1, Math.ceil(vm.baldes.length / 8))

  return (
    <section className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">Curva de vencimento</span>
        <span className="mono fraco" style={{ fontSize: 11 }}>
          {vm.horizonte_dias} dias · {vm.escopo}
        </span>
      </div>

      <div className="cartao-corpo">
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
          <span style={{ fontSize: 26, fontWeight: 600, letterSpacing: '-.025em' }}>{vm.total_lotes}</span>
          <span className="suave" style={{ fontSize: 13 }}>
            lote{vm.total_lotes === 1 ? '' : 's'} com saldo vencem neste horizonte
            {vm.pico_rotulo && <> · concentração maior em <strong>{vm.pico_rotulo}</strong></>}
          </span>
        </div>

        {vm.total_lotes === 0 ? (
          <p className="vazio">Nada vence neste horizonte.</p>
        ) : (
          <>
            <div className="gr" role="img"
              aria-label={`Lotes vencendo por período: ${vm.baldes.filter((b) => b.lotes).map((b) => `${b.rotulo}, ${b.lotes}`).join('; ')}`}>
              {vm.baldes.map((b, i) => (
                <div
                  key={b.inicio} className="gr-col"
                  onPointerEnter={() => setAtivo(i)} onPointerLeave={() => setAtivo(null)}
                  onFocus={() => setAtivo(i)} onBlur={() => setAtivo(null)}
                  tabIndex={b.lotes ? 0 : -1}
                  aria-label={`${b.rotulo}: ${b.lotes} lotes`}
                >
                  {ativo === i && b.lotes > 0 && (
                    <span className="gr-dica" role="status">
                      <strong>{b.lotes}</strong> lote{b.lotes === 1 ? '' : 's'}
                      <span className="fraco"> · {b.unidades.toLocaleString('pt-BR')} un</span>
                    </span>
                  )}
                  <span
                    className={`gr-barra gr-u${b.urgencia}`}
                    style={{ height: `${(b.lotes / max) * 100}%` }}
                  />
                </div>
              ))}
            </div>
            <div className="gr-eixo">
              {vm.baldes.map((b, i) => (
                <span key={b.inicio}>{i % passo === 0 ? b.rotulo : ''}</span>
              ))}
            </div>
            <ul className="faixas-legenda" style={{ marginTop: 14 }}>
              {vm.legenda.map((rot, i) => (
                <li key={rot}>
                  <span className={`ponto gr-u${3 - i}`} />
                  <span className="faixas-rotulo">{rot}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  )
}
