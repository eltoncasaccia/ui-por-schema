import { useState } from 'react'
import { dispararComando } from '../render/comando'
import { classeTexto } from '../ui/estados'
import { Etiqueta } from '../ui/Etiqueta'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'

type VM = ViewModel<'movimento_estorno'>
type Lancamento = VM['lancamentos'] extends (infer L)[] | undefined ? L : never
type Motivo = VM['motivos'][number]['valor']

const TOM_TIPO = {
  entrada: 'bom',
  saida: 'ciano',
  estorno: 'ambar',
  descarte: 'ruim',
} as const

/** Data e hora, porque dois lançamentos do mesmo dia se distinguem pela hora. */
function momentoBr(iso: string): string {
  const d = new Date(iso)
  return `${d.toLocaleDateString('pt-BR')} ${d.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  })}`
}

/**
 * O extrato do lote com o que se corrige, e o preço de corrigir dito na hora.
 *
 * **Os lançamentos não-estornáveis continuam na lista**, desabilitados e com o
 * motivo — o mesmo desenho do `movimento_saida`. Sumir com eles faria o operador
 * procurar de novo o lançamento que ele viu no extrato; mostrar por que não
 * serve encerra a busca.
 *
 * **O par original/estorno aparece inteiro.** `RN-M03` quer o erro E a correção
 * visíveis: um extrato "limpo" que escondesse o movimento estornado contaria
 * uma história que a trilha de auditoria contradiz.
 *
 * **Esta view não escreve** (ADR-0002). Ela desenha o formulário e guarda o que
 * foi escolhido; quem posta para `/api/comandos/movimento_estorno` é o motor de
 * render, que conhece o `CommandDef.confirm`. E o servidor recusa de novo, com a
 * identidade real (`RN-A03`).
 */
export const view: View<'movimento_estorno'> = ({ vm }) => {
  const [escolhido, setEscolhido] = useState<string | null>(vm.alvo?.movimento_id ?? null)
  const [motivo, setMotivo] = useState<Motivo | ''>('')
  const [complemento, setComplemento] = useState('')

  const lancamentos = vm.lancamentos ?? []
  const estornaveis = lancamentos.filter((l) => l.pode_estornar)
  const explicado = complemento.trim().length >= 10
  const podeEnviar = escolhido !== null && motivo !== '' && explicado

  function Linha({ l }: { l: Lancamento }) {
    return (
      <li style={{ margin: '6px 0' }}>
        <label
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'baseline',
            fontSize: 13,
            opacity: l.pode_estornar ? 1 : 0.55,
          }}
        >
          <input
            type="radio"
            name="lancamento-estorno"
            checked={escolhido === l.movimento_id}
            disabled={!l.pode_estornar}
            onChange={() => setEscolhido(l.movimento_id)}
          />
          <span>
            <Etiqueta tom={TOM_TIPO[l.tipo]}>{l.tipo}</Etiqueta>{' '}
            <span className="mono">{l.quantidade.toLocaleString('pt-BR')}</span>{' '}
            <span className="fraco">·</span> {l.motivo} <span className="fraco">·</span>{' '}
            <span className="mono fraco">{momentoBr(l.registrado_em)}</span>
            {l.estorna_movimento_id && (
              <span className="fraco" style={{ display: 'block', fontSize: 12 }}>
                corrige <span className="mono">{l.estorna_movimento_id}</span>
              </span>
            )}
            {!l.pode_estornar && l.impedimento && (
              <span className="fraco" style={{ display: 'block', fontSize: 12 }}>
                {l.impedimento}
              </span>
            )}
          </span>
        </label>
      </li>
    )
  }

  return (
    <div className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">Estorno · lote {vm.lote}</span>
        <span className="mono fraco" style={{ fontSize: 11 }}>
          {vm.unidade}
        </span>
      </div>

      <div className="cartao-corpo">
        <div style={{ fontWeight: 500, fontSize: 15, overflowWrap: 'anywhere' }}>{vm.produto}</div>

        <div className="linha-cartao-campos" style={{ marginTop: 12 }}>
          <div>
            <div className="campo-rotulo">Saldo</div>
            <div className="campo-valor">{vm.saldo.toLocaleString('pt-BR')}</div>
          </div>
          <div>
            <div className="campo-rotulo">Lançamentos</div>
            <div className="campo-valor">{vm.total.toLocaleString('pt-BR')}</div>
          </div>
        </div>

        {/* Dito ANTES de escolher: o estorno não apaga nada, e quem espera
            "desfazer" precisa saber que vai criar um lançamento novo. */}
        <p className="fraco" style={{ fontSize: 13 }}>
          O estorno cria um movimento novo que referencia o original. Nada é apagado nem
          editado (RN-M03).
        </p>

        {estornaveis.length === 0 ? (
          <p className={classeTexto('ambar')} style={{ fontSize: 13 }}>
            Nenhum lançamento deste lote pode ser estornado.
          </p>
        ) : (
          <>
            <div className="campo-rotulo">Lançamento</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0' }}>
              {lancamentos.map((l) => (
                <Linha key={l.movimento_id} l={l} />
              ))}
            </ul>

            <div style={{ marginTop: 16 }}>
              <label className="campo-rotulo" htmlFor="motivo-estorno">
                Motivo
              </label>
              <select
                id="motivo-estorno"
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

            <div style={{ marginTop: 12 }}>
              <label className="campo-rotulo" htmlFor="complemento-estorno">
                O que aconteceu
              </label>
              <textarea
                id="complemento-estorno"
                value={complemento}
                onChange={(e) => setComplemento(e.target.value)}
                rows={2}
                style={{ width: '100%', marginTop: 6, font: 'inherit' }}
              />
            </div>

            <div style={{ marginTop: 16 }}>
              <button type="button" disabled={!podeEnviar}
                onClick={(e) => {
                  if (!escolhido || !motivo) return
                  // T-051: etag do LANÇAMENTO escolhido, não do extrato inteiro.
                  const alvo = lancamentos.find((l) => l.movimento_id === escolhido)
                  dispararComando(e.currentTarget, {
                    acao: 'movimento_estorno',
                    corpo: { movimento_id: escolhido, motivo, complemento },
                    ...(alvo?.etag ? { etag: alvo.etag } : {}),
                  })
                }}>
                Registrar estorno
              </button>
            </div>

            {/* Diz o que falta, em vez de só desabilitar: botão morto sem
                explicação lê-se como sistema quebrado. */}
            {escolhido !== null && motivo !== '' && !explicado && (
              <p className="fraco" style={{ marginTop: 8, fontSize: 12 }}>
                O motivo escolhido é da lista fechada; a explicação é o que a auditoria vai
                ler depois (RN-M05).
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
