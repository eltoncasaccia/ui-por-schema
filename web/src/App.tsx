import { useEffect, useState } from 'react'
import { api, type Bloco, type EntradaCatalogo, type Eu } from './api'
import { sessao, useSessao, viewKeyLocal } from './estado/sessao'
import { BarraAtividades, type PainelId } from './shell/BarraAtividades'
import { Login } from './shell/Login'
import { PainelAssistente } from './shell/PainelAssistente'
import { PainelCatalogo } from './shell/PainelCatalogo'
import { PainelDebug } from './shell/PainelDebug'
import { PainelFixadas } from './shell/PainelFixadas'
import { Workspace } from './shell/Workspace'

/**
 * O shell da aplicação — estrutura fixa, conteúdo adaptável.
 *
 * Repare no pouco que existe aqui: cada painel lê o que lhe interessa. E repare
 * que o assistente é UMA superfície, ao lado do workspace — não o app inteiro
 * (§11.2 e §11.5 da arquitetura).
 */
export function App() {
  const [eu, setEu] = useState<Eu | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [painel, setPainel] = useState<PainelId>('navegacao')
  const [lateral, setLateral] = useState(true)
  const [assistente, setAssistente] = useState(true)
  const [debug, setDebug] = useState(false)
  useSessao()

  useEffect(() => {
    api.eu().then(setEu).catch(() => setEu(null)).finally(() => setCarregando(false))
  }, [])

  if (carregando) return <p className="muted" style={{ padding: 32 }}>carregando…</p>
  if (!eu) return <Login aoEntrar={setEu} />

  /** Abrir pelo catálogo produz o MESMO tipo de composição que o assistente. */
  function abrirDoCatalogo(c: EntradaCatalogo) {
    const blocos: Bloco[] = [{ tipo: c.id, params: {}, tamanho: 'inteira' }]
    sessao.compos({
      id: crypto.randomUUID(), titulo: c.label, origem: 'sistema',
      blocos, schema: { versao: 1, blocos: blocos.map((b) => ({ tipo: b.tipo, params: b.params })) },
      viewKey: viewKeyLocal(blocos),
    })
  }

  function abrirFixada(titulo: string, blocos: Bloco[]) {
    sessao.compos({
      id: crypto.randomUUID(), titulo, origem: 'sistema', blocos,
      schema: { versao: 1, blocos }, viewKey: viewKeyLocal(blocos),
    })
  }

  function sair() {
    void api.sair(); sessao.reset(); setEu(null)
  }

  return (
    <div className={`shell ${lateral ? 'has-side' : ''} ${assistente ? 'has-assistant' : ''} ${debug ? 'has-debug' : ''}`}>
      <BarraAtividades
        painel={painel} lateralAberta={lateral} assistenteAberto={assistente} debugAberto={debug}
        aoPainel={(p) => { if (p === painel && lateral) setLateral(false); else { setPainel(p); setLateral(true) } }}
        aoAssistente={() => setAssistente((v) => !v)}
        aoDebug={() => setDebug((v) => !v)}
      />

      {lateral && (
        <div className="side-panel">
          {painel === 'navegacao' && <PainelCatalogo eu={eu} aoAbrir={abrirDoCatalogo} />}
          {painel === 'fixadas' && <PainelFixadas aoAbrir={abrirFixada} />}
          <div style={{ borderTop: '1px solid var(--line)', padding: 12 }}>
            <div className="ator-info">
              <strong>{eu.nome}</strong>
              <span className="badge badge-neutral">{eu.papel}</span>
            </div>
            <div className="muted code" style={{ fontSize: 11, margin: '4px 0 8px' }}>
              {eu.unidades.join(' · ')}
            </div>
            <button className="ghost-button" onClick={sair}>sair</button>
          </div>
        </div>
      )}

      <Workspace eu={eu} />
      {assistente && <div className="assistant-dock"><PainelAssistente eu={eu} /></div>}
      {debug && <PainelDebug eu={eu} aoFechar={() => setDebug(false)} />}
    </div>
  )
}
