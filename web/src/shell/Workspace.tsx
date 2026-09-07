import type { Eu } from '../api'
import { Composicao as Render } from '../render/motor'
import { sessao, useSessao } from '../estado/sessao'

export function Workspace({ eu }: { eu: Eu }) {
  const { composicoes, noWorkspace, fixadas } = useSessao()
  const c = noWorkspace ? composicoes[noWorkspace] : undefined

  if (!c) {
    return (
      <main className="workspace">
        <div className="workspace-empty">
          <h1>Workspace</h1>
          <p className="muted">
            Abra um componente pelo catálogo, ou pergunte ao assistente. Os dois
            caminhos produzem o mesmo tipo de schema e passam pelo mesmo pipeline —
            é o ganho de registrar o componente uma vez só.
          </p>
        </div>
      </main>
    )
  }

  const fixada = fixadas.some((f) => f.viewKey === c.viewKey)

  return (
    <main className="workspace">
      <header className="workspace-head">
        <div>
          <h1>{c.titulo}</h1>
          <p className="workspace-sub">
            <span className={`source-tag ${c.origem === 'assistente' ? 'source-assistant' : ''}`}>
              {c.origem === 'assistente' ? 'schema do assistente' : 'schema do sistema'}
            </span>
            <span className="muted">{c.blocos.length} componente(s)</span>
            <span className="muted code">{c.viewKey}</span>
          </p>
        </div>
        <button
          className={`pin-button ${fixada ? 'is-pinned' : ''}`}
          onClick={() => sessao.fixar(c)}
          title={fixada ? 'Desafixar' : 'Fixar view'}
        >★</button>
      </header>
      <div className="workspace-body">
        <Render blocos={c.blocos} atorId={eu.id} />
      </div>
    </main>
  )
}
