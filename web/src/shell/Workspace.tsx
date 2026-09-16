import type { Eu } from '../api'
import { Composicao as Render } from '../render/motor'
import { useSessao } from '../estado/sessao'
import { CabecalhoTela } from './CabecalhoTela'

export function Workspace({ eu }: { eu: Eu }) {
  const { composicoes, noWorkspace } = useSessao()
  const c = noWorkspace ? composicoes[noWorkspace] : undefined

  if (!c) {
    return (
      <main className="workspace">
        <div className="workspace-vazio">
          <h1 style={{ fontSize: 19, marginBottom: 8 }}>Workspace</h1>
          <p className="vazio">
            Abra uma tela pela navegação, ou pergunte ao assistente e envie a
            resposta para cá. Os dois caminhos produzem o mesmo tipo de schema e
            passam pelo mesmo pipeline.
          </p>
        </div>
      </main>
    )
  }

  return (
    <main className="workspace">
      <CabecalhoTela titulo={c.titulo} composicao={c}>
        <span className={`marca-origem ${c.origem === 'assistente' ? 'marca-assistente' : ''}`}>
          {c.origem === 'assistente' ? 'schema do assistente' : 'schema do sistema'}
        </span>
        <span className="suave">{c.blocos.length} componente{c.blocos.length === 1 ? '' : 's'}</span>
        <span className="mono fraco" style={{ fontSize: 11 }}>{c.viewKey}</span>
      </CabecalhoTela>
      <div className="workspace-corpo">
        <Render blocos={c.blocos} atorId={eu.id} />
      </div>
    </main>
  )
}
