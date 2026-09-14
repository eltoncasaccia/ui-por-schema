import { useState } from 'react'
import { dispararComando } from '../render/comando'
import { SITUACAO, classeTexto } from '../ui/estados'
import { Etiqueta } from '../ui/Etiqueta'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { dataBr } from './fila_vencimento'
import { STATUS_LOTE } from './lote_lista'

type VM = ViewModel<'movimento_saida'>
type Candidato = VM['proposta']
type Motivo = VM['motivos'][number]['valor']

/**
 * A proposta do FEFO em destaque, as alternativas abaixo, e o preço de trocar
 * cobrado na hora.
 *
 * **A justificativa aparece no instante em que o operador sai da proposta**, e
 * não no fim do formulário. Um campo que só se revela ao submeter ensina que a
 * regra é burocracia de saída; ao lado da escolha, ele mostra que a escolha é
 * que tem custo — que é o que `RN-L03` quer dizer.
 *
 * **Os lotes indisponíveis continuam na lista**, desabilitados e com o motivo.
 * Sumir com eles faria o operador procurar de novo o lote que ele viu na
 * prateleira; mostrar por que não serve encerra a busca.
 *
 * A view não decide regra: `proposto`, `disponivel` e `motivo` chegam prontos
 * do servidor, e o servidor recusa de novo na hora de gravar (`RN-A03`).
 */
export const view: View<'movimento_saida'> = ({ vm }) => {
  const [escolhido, setEscolhido] = useState<string | null>(vm.proposta?.lote_id ?? null)
  const [motivo, setMotivo] = useState<Motivo | ''>('')
  const [justificativa, setJustificativa] = useState('')
  const [quantidade, setQuantidade] = useState('')
  const [clienteId, setClienteId] = useState('')
  const [notaFiscal, setNotaFiscal] = useState('')

  const trocou = escolhido !== null && escolhido !== vm.proposta?.lote_id
  const opcao = vm.motivos.find((m) => m.valor === motivo)
  const qtd = Number(quantidade)
  const podeEnviar =
    escolhido !== null &&
    motivo !== '' &&
    Number.isInteger(qtd) &&
    qtd > 0 &&
    (!trocou || justificativa.trim().length >= 10)

  function Linha({ c, destaque }: { c: NonNullable<Candidato>; destaque?: boolean }) {
    return (
      <li style={{ margin: '6px 0' }}>
        <label
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'baseline',
            fontSize: 13,
            opacity: c.disponivel ? 1 : 0.55,
          }}
        >
          <input
            type="radio"
            name="lote-saida"
            checked={escolhido === c.lote_id}
            disabled={!c.disponivel}
            onChange={() => setEscolhido(c.lote_id)}
          />
          <span>
            <span className="mono">{c.numero}</span>
            {destaque && (
              <>
                {' '}
                <Etiqueta tom="bom">FEFO</Etiqueta>
              </>
            )}{' '}
            <span className="fraco">·</span> vence{' '}
            <span className="mono">{dataBr(c.validade)}</span>{' '}
            <span className={classeTexto(SITUACAO[c.situacao].tom)}>
              ({c.dias_restantes < 0 ? `−${Math.abs(c.dias_restantes)}` : c.dias_restantes} d)
            </span>{' '}
            <span className="fraco">·</span> saldo {c.saldo.toLocaleString('pt-BR')}
            {!c.disponivel && (
              <span className="fraco" style={{ display: 'block', fontSize: 12 }}>
                {c.motivo ?? STATUS_LOTE[c.status_efetivo].rotulo}
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
        <span className="titulo-painel">Saída · {vm.produto}</span>
        <span className="mono fraco" style={{ fontSize: 11 }}>
          {vm.escopo}
        </span>
      </div>

      <div className="cartao-corpo">
        {/* RN-C01: dito ANTES de preencher. Descobrir depois que a saída ficou
            pendente lê-se como falha, e não como a regra que é. */}
        {vm.exige_autorizacao && (
          <p className={classeTexto('ambar')} style={{ fontSize: 13, marginTop: 0 }}>
            Produto controlado: a saída fica <strong>aguardando autorização</strong> do
            responsável técnico, e o saldo só muda quando ele autorizar.
          </p>
        )}

        {vm.sem_estoque ? (
          <p className="fraco" style={{ fontSize: 13 }}>
            Nenhum lote liberado com saldo neste escopo. Não há saída possível.
          </p>
        ) : (
          <>
            <div className="campo-rotulo">Lote</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0' }}>
              {vm.proposta && <Linha c={vm.proposta} destaque />}
              {(vm.alternativas ?? []).map((c) => (
                <Linha key={c.lote_id} c={c} />
              ))}
            </ul>

            {trocou && (
              <div style={{ marginTop: 12 }}>
                <label className="campo-rotulo" htmlFor="justificativa-fefo">
                  Justificativa para não usar o lote proposto
                </label>
                <textarea
                  id="justificativa-fefo"
                  value={justificativa}
                  onChange={(e) => setJustificativa(e.target.value)}
                  rows={2}
                  style={{ width: '100%', marginTop: 6, font: 'inherit' }}
                />
              </div>
            )}

            <div className="linha-cartao-campos" style={{ marginTop: 16 }}>
              <div>
                <label className="campo-rotulo" htmlFor="quantidade-saida">
                  Quantidade
                </label>
                <input
                  id="quantidade-saida"
                  type="number"
                  min={1}
                  value={quantidade}
                  onChange={(e) => setQuantidade(e.target.value)}
                  style={{ width: '100%', marginTop: 6, font: 'inherit' }}
                />
              </div>
              <div>
                <label className="campo-rotulo" htmlFor="motivo-saida">
                  Motivo
                </label>
                <select
                  id="motivo-saida"
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
            </div>

            {/* Cliente e nota só aparecem quando o motivo os exige — é o que
                alimenta o recall (RN-D03), e pedi-los numa avaria seria ruído
                que ensina a preencher qualquer coisa. */}
            {opcao?.exige_destinatario && (
              <div className="linha-cartao-campos" style={{ marginTop: 12 }}>
                <div>
                  <label className="campo-rotulo" htmlFor="cliente-saida">
                    Cliente
                  </label>
                  <input
                    id="cliente-saida"
                    value={clienteId}
                    onChange={(e) => setClienteId(e.target.value)}
                    style={{ width: '100%', marginTop: 6, font: 'inherit' }}
                  />
                </div>
                <div>
                  <label className="campo-rotulo" htmlFor="nota-saida">
                    Nota fiscal
                  </label>
                  <input
                    id="nota-saida"
                    value={notaFiscal}
                    onChange={(e) => setNotaFiscal(e.target.value)}
                    style={{ width: '100%', marginTop: 6, font: 'inherit' }}
                  />
                </div>
              </div>
            )}

            <div style={{ marginTop: 16 }}>
              <button type="button" disabled={!podeEnviar}
                onClick={(e) => {
                  if (!escolhido || !motivo) return
                  // T-051: etag da LINHA escolhida, não do bloco — a pessoa
                  // pode ter trocado a proposta por uma alternativa.
                  const candidato = [vm.proposta, ...(vm.alternativas ?? [])].find(
                    (c) => c?.lote_id === escolhido,
                  )
                  dispararComando(e.currentTarget, {
                    acao: 'movimento_saida',
                    corpo: {
                      lote_id: escolhido,
                      quantidade: qtd,
                      motivo,
                      justificativa_fefo: trocou ? justificativa : null,
                      cliente_id: opcao?.exige_destinatario ? clienteId : null,
                      nota_fiscal: opcao?.exige_destinatario ? notaFiscal : null,
                    },
                    ...(candidato?.etag ? { etag: candidato.etag } : {}),
                  })
                }}>
                {vm.exige_autorizacao ? 'Enviar para autorização' : 'Registrar saída'}
              </button>
            </div>

            {trocou && justificativa.trim().length < 10 && (
              <p className="fraco" style={{ marginTop: 8, fontSize: 12 }}>
                Separar lote diferente do proposto exige justificativa registrada (RN-L03).
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
