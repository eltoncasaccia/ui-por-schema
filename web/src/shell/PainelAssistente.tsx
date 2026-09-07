import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { ErroApi, api, type Eu } from '../api'
import { Composicao as Render } from '../render/motor'
import { sessao, useSessao, viewKeyLocal } from '../estado/sessao'

export function PainelAssistente({ eu }: { eu: Eu }) {
  const { conversa, composicoes, pensando } = useSessao()
  const [rascunho, setRascunho] = useState('')
  const cat = useQuery({ queryKey: [eu.id, 'catalogo'], queryFn: api.catalogo })
  const sugestoes = (cat.data ?? []).flatMap((c) => c.examples).slice(0, 5)

  async function perguntar(texto: string) {
    setRascunho('')
    sessao.pergunta(texto)
    try {
      const c = await api.compor(texto)
      if (c.blocos.length === 0) {
        // Composição vazia é RESPOSTA, não erro: o modelo olhou o catálogo
        // deste ator e não achou nada que sirva.
        sessao.nota('Nada no seu catálogo responde a isso.')
        return
      }
      sessao.compos(
        {
          id: crypto.randomUUID(),
          titulo: texto,
          origem: 'assistente',
          blocos: c.blocos,
          schema: c.schema,
          viewKey: viewKeyLocal(c.blocos),
        },
        c.trace,
        texto,
      )
    } catch (e) {
      sessao.falhou(e instanceof ErroApi ? e.message : 'Falhou.')
    }
  }

  return (
    <div className="panel panel-assistant">
      <div className="assistant-head">
        <h2 className="panel-title">Assistente</h2>
        <div className="assistant-tools">
          <button className="ghost-button" onClick={sessao.limpar} disabled={conversa.length === 0}>
            Limpar
          </button>
        </div>
      </div>

      <div className="conversation">
        {conversa.length === 0 && (
          <div className="assistant-empty">
            <p className="muted">
              Pergunte em português. O modelo escolhe <em>quais componentes compor</em> —
              nunca escreve código, nunca vê os dados, nunca autoriza escrita.
            </p>
            <div className="suggestions">
              {sugestoes.map((s) => (
                <button key={s} className="suggestion" onClick={() => void perguntar(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {conversa.map((m, i) => {
          if (m.papel === 'usuario') return <div key={i} className="msg-user">{m.texto}</div>
          if (m.papel === 'erro') return <div key={i} className="msg-error">{m.texto}</div>
          if (m.papel === 'nota') return <div key={i} className="msg-note">{m.texto}</div>
          const c = composicoes[m.composicaoId]
          if (!c) return null
          return (
            <div key={i} className="msg-assistant">
              <div className="inline-composition">
                <div className="inline-head">
                  <span className="inline-title">{c.blocos.length} componente(s)</span>
                  <div className="inline-actions">
                    <button className="ghost-button" onClick={() => sessao.aoWorkspace(c.id)}>
                      abrir no workspace
                    </button>
                  </div>
                </div>
                <Render blocos={c.blocos} atorId={eu.id} />
              </div>
            </div>
          )
        })}
        {pensando && <div className="msg-note">compondo…</div>}
      </div>

      <form
        className="composer"
        onSubmit={(e) => { e.preventDefault(); if (rascunho.trim()) void perguntar(rascunho) }}
      >
        <input
          className="composer-input"
          value={rascunho}
          onChange={(e) => setRascunho(e.target.value)}
          placeholder="o que está vencendo?"
          aria-label="Pergunta ao assistente"
        />
        <button className="composer-send" disabled={pensando || !rascunho.trim()}>enviar</button>
      </form>
    </div>
  )
}
