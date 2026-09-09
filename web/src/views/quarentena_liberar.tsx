import { useState } from 'react'
import { SITUACAO, classeTexto } from '../ui/estados'
import { Etiqueta } from '../ui/Etiqueta'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { dataBr } from './fila_vencimento'
import { STATUS_LOTE } from './lote_lista'

type VM = ViewModel<'quarentena_liberar'>
type Campo = VM['conferencia'][number]['campo']

/**
 * O formulário de decisão do RT.
 *
 * **Esta view não escreve** (ADR-0002). Ela desenha o formulário e guarda o
 * que foi marcado; quem posta para `/api/comandos/lote_liberar_quarentena` é o
 * motor de render, que conhece o `CommandDef.confirm` — a view não busca dado,
 * não conhece permissão e não decide regra.
 *
 * **Por que os dois botões não têm o mesmo peso.** Liberar é a ação que coloca
 * mercadoria à venda, e é a que exige a conferência completa; reprovar é a
 * saída conservadora e está sempre disponível. Dar a ambos o mesmo destaque
 * ensinaria que são simétricos, e eles não são: um erro para liberar chega ao
 * paciente, um erro para reprovar chega ao estoque.
 *
 * `obrigatorio` vem do servidor, item por item — a temperatura só é exigida de
 * termolábil, e essa decisão é da classe do produto, não da tela.
 */
export const view: View<'quarentena_liberar'> = ({ vm }) => {
  const [marcados, setMarcados] = useState<Record<string, boolean>>({})
  const [justificativa, setJustificativa] = useState('')

  const pendentes = vm.conferencia.filter((i) => i.obrigatorio && !marcados[i.campo])
  const justificado = justificativa.trim().length >= 10
  const podeLiberar = vm.pode_decidir && pendentes.length === 0 && justificado
  const podeReprovar = vm.pode_decidir && justificado

  function alternar(campo: Campo) {
    setMarcados((m) => ({ ...m, [campo]: !m[campo] }))
  }

  return (
    <div className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">Liberação · lote {vm.numero}</span>
        <Etiqueta tom={STATUS_LOTE[vm.status_efetivo].tom}>
          {STATUS_LOTE[vm.status_efetivo].rotulo}
        </Etiqueta>
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

        {vm.aviso_validade && (
          <p
            className={classeTexto(vm.dias_restantes < 0 ? 'ruim' : 'laranja')}
            style={{ marginTop: 12, fontSize: 13 }}
          >
            {vm.aviso_validade}
          </p>
        )}

        {!vm.pode_decidir && vm.motivo && (
          <p className="fraco" style={{ marginTop: 12, fontSize: 13 }}>
            {vm.motivo}
          </p>
        )}

        <div style={{ marginTop: 16 }}>
          <div className="campo-rotulo">Conferência</div>
          <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0' }}>
            {vm.conferencia.map((item) => (
              <li key={item.campo} style={{ margin: '6px 0' }}>
                <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}>
                  <input
                    type="checkbox"
                    checked={!!marcados[item.campo]}
                    disabled={!vm.pode_decidir}
                    onChange={() => alternar(item.campo)}
                  />
                  <span>{item.rotulo}</span>
                  {!item.obrigatorio && <span className="fraco">(opcional)</span>}
                </label>
              </li>
            ))}
          </ul>
        </div>

        <div style={{ marginTop: 16 }}>
          <label className="campo-rotulo" htmlFor="justificativa-liberacao">
            Justificativa
          </label>
          <textarea
            id="justificativa-liberacao"
            value={justificativa}
            disabled={!vm.pode_decidir}
            onChange={(e) => setJustificativa(e.target.value)}
            rows={2}
            style={{ width: '100%', marginTop: 6, font: 'inherit' }}
          />
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
          <button type="button" disabled={!podeLiberar} data-acao="liberar">
            Liberar
          </button>
          <button type="button" disabled={!podeReprovar} data-acao="reprovar">
            Reprovar
          </button>
        </div>

        {/* Diz o que falta, em vez de só desabilitar. Um botão morto sem
            explicação lê-se como sistema quebrado. */}
        {vm.pode_decidir && pendentes.length > 0 && (
          <p className="fraco" style={{ marginTop: 8, fontSize: 12 }}>
            Falta conferir: {pendentes.map((i) => i.rotulo.toLowerCase()).join(', ')}.
          </p>
        )}
      </div>
    </div>
  )
}
