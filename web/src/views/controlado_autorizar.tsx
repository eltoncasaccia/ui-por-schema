import { useState } from 'react'
import { classeTexto } from '../ui/estados'
import { Etiqueta } from '../ui/Etiqueta'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'

type VM = ViewModel<'controlado_autorizar'>
type Pendente = NonNullable<VM['alvo']>

function dataHoraBr(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

/**
 * A fila do RT e a decisão — as duas metades do `CA-04` que o operador vê.
 *
 * **Ordenada por quanto tempo o pedido está parado, não por quando chegou.** Um
 * controlado esperando há cinco dias é estoque travado e paciente sem remédio; a
 * data de submissão sozinha esconderia isso atrás de uma coluna que ninguém
 * compara de cabeça.
 *
 * **Autorizar e recusar não são simétricos.** Autorizar move mercadoria
 * controlada, e é a ação que a fiscalização audita; recusar é conservador e
 * reversível por um novo pedido. Dar o mesmo peso visual ensinaria que dá na
 * mesma.
 *
 * O motivo é exigido nas DUAS — autorizar sem justificativa registrada não serve
 * a quem lê a trilha depois, que é exatamente o público dela.
 *
 * A view não decide nada: `pode_decidir` chega pronto do servidor, e o servidor
 * recusa de novo, e o banco recusa uma terceira vez (`RN-A04`).
 */
export const view: View<'controlado_autorizar'> = ({ vm }) => {
  const [motivo, setMotivo] = useState('')
  const alvo = vm.alvo
  const justificado = motivo.trim().length >= 10
  const habilitado = alvo !== null && alvo !== undefined && vm.pode_decidir && justificado

  function Linha({ p, atual }: { p: Pendente; atual: boolean }) {
    return (
      <li style={{ margin: '8px 0' }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', fontSize: 13 }}>
          <span style={{ fontWeight: atual ? 600 : 400 }}>{p.produto}</span>
          <span className="fraco">·</span>
          <span className="mono">{p.quantidade.toLocaleString('pt-BR')}</span>
          {p.parado_ha_dias >= 2 && (
            <Etiqueta tom={p.parado_ha_dias >= 5 ? 'ruim' : 'ambar'}>
              parado há {p.parado_ha_dias} d
            </Etiqueta>
          )}
        </div>
        <div className="fraco" style={{ fontSize: 12 }}>
          lote <span className="mono">{p.lote_id}</span> · {p.unidade} · submetido por{' '}
          <span className="mono">{p.autor}</span> em {dataHoraBr(p.submetido_em)}
        </div>
      </li>
    )
  }

  return (
    <div className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">Controlados aguardando autorização</span>
        <span className="mono fraco" style={{ fontSize: 11 }}>
          {vm.escopo}
        </span>
      </div>

      <div className="cartao-corpo">
        {vm.total === 0 ? (
          <p className="fraco" style={{ fontSize: 13, margin: 0 }}>
            Nada aguardando autorização neste escopo.
          </p>
        ) : (
          <>
            <div className="campo-rotulo">
              {vm.total} {vm.total === 1 ? 'pendência' : 'pendências'}
            </div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0' }}>
              {(vm.fila ?? []).map((p) => (
                <Linha
                  key={p.movimento_id}
                  p={p}
                  atual={p.movimento_id === alvo?.movimento_id}
                />
              ))}
            </ul>
          </>
        )}

        {alvo && (
          <div
            style={{
              marginTop: 20,
              paddingTop: 16,
              borderTop: '1px solid var(--linha, rgba(128,128,128,.25))',
            }}
          >
            <div className="campo-rotulo">Decisão</div>
            <p style={{ fontSize: 13, margin: '6px 0 0' }}>
              {alvo.quantidade.toLocaleString('pt-BR')} de {alvo.produto}, lote{' '}
              <span className="mono">{alvo.lote_id}</span>.
            </p>

            {/* RN-A04, dito antes de o botão sumir: um controle desabilitado sem
                explicação lê-se como sistema quebrado. */}
            {!vm.pode_decidir && vm.motivo_impedimento && (
              <p className={classeTexto('laranja')} style={{ fontSize: 13 }}>
                {vm.motivo_impedimento}
              </p>
            )}

            <div style={{ marginTop: 12 }}>
              <label className="campo-rotulo" htmlFor="motivo-autorizacao">
                Motivo
              </label>
              <textarea
                id="motivo-autorizacao"
                value={motivo}
                disabled={!vm.pode_decidir}
                onChange={(e) => setMotivo(e.target.value)}
                rows={2}
                style={{ width: '100%', marginTop: 6, font: 'inherit' }}
              />
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
              <button type="button" disabled={!habilitado} data-decisao="autorizar">
                Autorizar
              </button>
              <button type="button" disabled={!habilitado} data-decisao="recusar">
                Recusar
              </button>
            </div>

            {vm.pode_decidir && !justificado && (
              <p className="fraco" style={{ marginTop: 8, fontSize: 12 }}>
                As duas decisões exigem motivo registrado — é o que a trilha guarda.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
