import type { Eu } from '../api'
import { Composicao as Render } from '../render/motor'
import { sessao, useSessao } from '../estado/sessao'
import { Icone } from '../ui/icones'

export function Workspace({ eu, aoCompartilhar }: { eu: Eu; aoCompartilhar: () => void }) {
  const { composicoes, noWorkspace, fixadas } = useSessao()
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

  const fixada = fixadas.some((f) => f.viewKey === c.viewKey)

  return (
    <main className="workspace">
      <header className="workspace-cabeca">
        <div style={{ minWidth: 0 }}>
          <h1 className="workspace-titulo" style={{ overflowWrap: 'anywhere' }}>{c.titulo}</h1>
          <div className="workspace-sub">
            <span className={`marca-origem ${c.origem === 'assistente' ? 'marca-assistente' : ''}`}>
              {c.origem === 'assistente' ? 'schema do assistente' : 'schema do sistema'}
            </span>
            <span className="suave">{c.blocos.length} componente{c.blocos.length === 1 ? '' : 's'}</span>
            <span className="mono fraco" style={{ fontSize: 11 }}>{c.viewKey}</span>
          </div>
        </div>
        <div className="workspace-acoes">
          {/* Só a estrela: o rótulo repetia o que o ícone já diz, e o estado
              (fixada ou não) fica no preenchimento, não num texto. */}
          <button className={`estrela ${fixada ? 'is-fixada' : ''}`} onClick={() => sessao.fixar(c)}
            aria-pressed={fixada} aria-label={fixada ? 'Desafixar view' : 'Fixar view'}
            title={fixada ? 'Desafixar' : 'Fixar'}>
            <Icone.Estrela tamanho={16} preenchida={fixada} />
          </button>
          <button className="btn" onClick={aoCompartilhar} aria-label="Compartilhar view">
            <Icone.Compartilhar tamanho={15} /> <span className="so-largo">Compartilhar</span>
          </button>
        </div>
      </header>
      <div className="workspace-corpo">
        <Render blocos={c.blocos} atorId={eu.id} />
      </div>
    </main>
  )
}
