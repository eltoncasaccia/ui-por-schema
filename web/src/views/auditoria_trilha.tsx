import { Etiqueta } from '../ui/Etiqueta'
import type { Tom } from '../ui/estados'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'

type VM = ViewModel<'auditoria_trilha'>
type Linha = VM['linhas'][number]

/** De onde a ação partiu. O assistente é caminho de leitura; escrita vem da tela. */
const ORIGEM: Record<string, Tom> = { tela: 'neutro', assistente: 'ciano', sistema: 'ambar' }

function horaBr(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' })
}

/**
 * Um valor de JSON livre em texto.
 *
 * `JSON.stringify` no que não é primitivo, e não `String()`: o ESLint pegou que
 * `String({})` produz `[object Object]` — que numa trilha de auditoria não é
 * feio, é perda de informação. `null` vira texto explícito pelo mesmo motivo.
 */
function texto(v: unknown): string {
  if (v === null) return 'null'
  if (typeof v === 'object') return JSON.stringify(v)
  if (typeof v === 'string') return v
  return JSON.stringify(v) ?? ''
}

/** Um par chave/valor do JSON, achatado numa linha legível. */
function Valores({ rotulo, dados }: { rotulo: string; dados: Record<string, unknown> }) {
  const chaves = Object.keys(dados)
  if (chaves.length === 0) return null
  return (
    <div style={{ fontSize: 12 }}>
      <span className="fraco">{rotulo}: </span>
      {chaves.map((k, i) => (
        <span key={k}>
          {i > 0 && <span className="fraco"> · </span>}
          <span className="fraco">{k}</span> <span className="mono">{texto(dados[k])}</span>
        </span>
      ))}
    </div>
  )
}

/**
 * A trilha, e o que ela não mostra.
 *
 * **Nenhuma ação, para nenhum papel** — `RN-D02`: a trilha é append-only no
 * banco, e nem o Diretor edita. Não há botão porque não há caminho.
 *
 * **Quando o servidor filtra um valor, a tela diz que filtrou** (`filtrada`).
 * Omitir em silêncio seria pior que mostrar: quem audita precisa saber que havia
 * mais ali, e que a ausência é regra e não falha de gravação. É a diferença
 * entre "não teve" e "não te mostro".
 *
 * `JSON.stringify` no valor aninhado, e não uma árvore navegável: a trilha é
 * lida em investigação, e uma linha por evento é o que permite varrer rápido.
 */
export const view: View<'auditoria_trilha'> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">Trilha de auditoria</span>
      <span className="mono fraco" style={{ fontSize: 11 }}>
        {vm.recorte}
      </span>
    </div>

    <div className="cartao-corpo">
      {vm.total === 0 ? (
        <p className="fraco" style={{ fontSize: 13, margin: 0 }}>
          Nenhum evento neste recorte.
        </p>
      ) : (
        <>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {vm.linhas.map((l: Linha) => (
              <li
                key={l.id}
                style={{ padding: '10px 0', borderTop: '1px solid var(--linha, rgba(128,128,128,.18))' }}
              >
                <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
                  <span className="mono fraco" style={{ fontSize: 11 }}>
                    {horaBr(l.criado_em)}
                  </span>
                  <span style={{ fontWeight: 500, fontSize: 13 }}>{l.acao}</span>
                  {l.entidade && (
                    <span className="fraco" style={{ fontSize: 12 }}>
                      {l.entidade}
                      {l.entidade_id && <span className="mono"> {l.entidade_id}</span>}
                    </span>
                  )}
                  <Etiqueta tom={ORIGEM[l.origem] ?? 'neutro'}>{l.origem}</Etiqueta>
                  {l.ator && <span className="mono fraco" style={{ fontSize: 11 }}>{l.ator}</span>}
                </div>

                {l.valor_anterior && <Valores rotulo="antes" dados={l.valor_anterior} />}
                {l.valor_novo && <Valores rotulo="depois" dados={l.valor_novo} />}

                {l.filtrada && (
                  <div className="fraco" style={{ fontSize: 11, marginTop: 2 }}>
                    valores de custo omitidos por regra de acesso (CA-05)
                  </div>
                )}
              </li>
            ))}
          </ul>

          {vm.truncada && (
            <p className="fraco" style={{ fontSize: 12, marginTop: 12 }}>
              Mostrando os {vm.total} eventos mais recentes. Estreite o recorte para ver
              o resto — a trilha não é paginada de propósito: ela cresce sem parar.
            </p>
          )}
        </>
      )}
    </div>
  </div>
)
