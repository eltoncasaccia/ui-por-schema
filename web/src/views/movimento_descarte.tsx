import { useState } from 'react'
import { classeTexto } from '../ui/estados'
import { Etiqueta } from '../ui/Etiqueta'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { dataBr } from './fila_vencimento'
import { STATUS_LOTE } from './lote_lista'

type VM = ViewModel<'movimento_descarte'>
type Linha = VM['fila'] extends (infer L)[] | undefined ? L : never
type Motivo = VM['motivos'][number]['valor']

/**
 * A fila do que só sai por descarte, e o formulário com as duas assinaturas.
 *
 * **A dupla identificação é dita antes de preencher**, e não na recusa. §4.1
 * exige gerente e responsável técnico; descobrir isso depois de escrever a
 * justificativa lê-se como falha do sistema, e não como a regra que é.
 *
 * **O lote sai inteiro, e a tela mostra quanto.** O saldo aparece ao lado de
 * cada lote justamente porque o descarte não é parcial: o número que está ali é
 * o que vai ser destruído.
 *
 * **Esta view não escreve** (ADR-0002) e não decide regra: `pode_descartar` e
 * `impedimento` chegam prontos do servidor, e o servidor recusa de novo na hora
 * de gravar (`RN-A03`).
 */
export const view: View<'movimento_descarte'> = ({ vm }) => {
  const fila = vm.fila ?? []
  const [escolhido, setEscolhido] = useState<string | null>(
    vm.alvo?.pode_descartar ? vm.alvo.lote_id : null,
  )
  const [motivo, setMotivo] = useState<Motivo | ''>('')
  const [justificativa, setJustificativa] = useState('')
  const [segunda, setSegunda] = useState('')

  const justificado = justificativa.trim().length >= 10
  const assinado = segunda.trim().length > 0
  const podeEnviar = escolhido !== null && motivo !== '' && justificado && assinado

  function Item({ l }: { l: Linha }) {
    return (
      <li style={{ margin: '6px 0' }}>
        <label
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'baseline',
            fontSize: 13,
            opacity: l.pode_descartar ? 1 : 0.55,
          }}
        >
          <input
            type="radio"
            name="lote-descarte"
            checked={escolhido === l.lote_id}
            disabled={!l.pode_descartar}
            onChange={() => setEscolhido(l.lote_id)}
          />
          <span>
            <span className="mono">{l.numero}</span> <span className="fraco">·</span> {l.produto}{' '}
            <Etiqueta tom={STATUS_LOTE[l.status_efetivo].tom}>
              {STATUS_LOTE[l.status_efetivo].rotulo}
            </Etiqueta>
            <span className="fraco" style={{ display: 'block', fontSize: 12 }}>
              {l.unidade} · vence <span className="mono">{dataBr(l.validade)}</span> · saldo{' '}
              {l.saldo.toLocaleString('pt-BR')}
              {l.impedimento ? ` · ${l.impedimento}` : ''}
            </span>
          </span>
        </label>
      </li>
    )
  }

  return (
    <div className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">Descarte</span>
        <span className="mono fraco" style={{ fontSize: 11 }}>
          {vm.escopo}
        </span>
      </div>

      <div className="cartao-corpo">
        {vm.exige_dupla_identificacao && (
          <p className={classeTexto('ambar')} style={{ fontSize: 13, marginTop: 0 }}>
            O descarte é registrado por <strong>duas pessoas</strong>: o gerente e o
            responsável técnico. O lote sai inteiro e não volta.
          </p>
        )}

        {/* O alvo pedido que NÃO pode ser descartado aparece sozinho, com o
            motivo: é o caso de quem chegou aqui por um lote específico. */}
        {vm.alvo && !vm.alvo.pode_descartar && (
          <p className={classeTexto('laranja')} style={{ fontSize: 13 }}>
            Lote <span className="mono">{vm.alvo.numero}</span>: {vm.alvo.impedimento}
          </p>
        )}

        {fila.length === 0 ? (
          <p className="fraco" style={{ fontSize: 13 }}>
            Nenhum lote vencido ou bloqueado com saldo neste escopo.
          </p>
        ) : (
          <>
            <div className="campo-rotulo">Lote ({vm.total.toLocaleString('pt-BR')})</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0' }}>
              {fila.map((l) => (
                <Item key={l.lote_id} l={l} />
              ))}
            </ul>

            <div className="linha-cartao-campos" style={{ marginTop: 16 }}>
              <div>
                <label className="campo-rotulo" htmlFor="motivo-descarte">
                  Motivo
                </label>
                <select
                  id="motivo-descarte"
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value as Motivo)}
                  style={{ width: '100%', marginTop: 6, font: 'inherit' }}
                >
                  <option value="">—</option>
                  {vm.motivos.map((m) => (
                    <option key={m.valor} value={m.valor}>
                      {m.rotulo}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="campo-rotulo" htmlFor="segunda-identificacao">
                  Segunda identificação
                </label>
                <input
                  id="segunda-identificacao"
                  value={segunda}
                  onChange={(e) => setSegunda(e.target.value)}
                  placeholder="matrícula de quem assina junto"
                  style={{ width: '100%', marginTop: 6, font: 'inherit' }}
                />
              </div>
            </div>

            <div style={{ marginTop: 12 }}>
              <label className="campo-rotulo" htmlFor="justificativa-descarte">
                Justificativa
              </label>
              <textarea
                id="justificativa-descarte"
                value={justificativa}
                onChange={(e) => setJustificativa(e.target.value)}
                rows={2}
                style={{ width: '100%', marginTop: 6, font: 'inherit' }}
              />
            </div>

            <div style={{ marginTop: 16 }}>
              <button type="button" disabled={!podeEnviar}>
                Registrar descarte
              </button>
            </div>

            {escolhido !== null && !assinado && (
              <p className="fraco" style={{ marginTop: 8, fontSize: 12 }}>
                Falta a segunda identificação: gerente e responsável técnico assinam juntos
                (§4.1).
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
