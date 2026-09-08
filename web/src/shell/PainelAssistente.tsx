import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { ErroApi, api, type Eu } from '../api'
import { Composicao as Render } from '../render/motor'
import { Icone } from '../ui/icones'
import { sessao, useSessao, viewKeyLocal } from '../estado/sessao'

export function PainelAssistente({
  eu, aoFechar, aoCompartilhar,
}: { eu: Eu; aoFechar: () => void; aoCompartilhar: (composicaoId: string) => void }) {
  const { conversa, composicoes, pensando, fixadas } = useSessao()
  const [rascunho, setRascunho] = useState('')
  const cat = useQuery({ queryKey: [eu.id, 'catalogo'], queryFn: api.catalogo })
  // Sugestões saem do catálogo DESTE ator — que já é filtrado por permissão —
  // e os exemplos são escritos sem nome de unidade nem valor restrito. Sugerir
  // o que a pessoa não pode pedir é oferecer uma porta fechada, e ainda conta
  // que a porta existe.
  const sugestoes = (cat.data ?? []).flatMap((c) => c.examples).slice(0, 5)

  async function perguntar(texto: string) {
    setRascunho('')
    sessao.pergunta(texto)
    try {
      const c = await api.compor(texto)
      if (c.blocos.length === 0) {
        // Composição vazia é RESPOSTA, não erro. E a mensagem não diz que o
        // sistema TEM o dado e não pode mostrar — diz que não sabe responder.
        // Contar que existe já é contar demais (ADR-0014).
        sessao.nota('Não consigo responder isso por aqui.')
        return
      }
      // NÃO vai para o workspace. A composição fica na conversa até a pessoa
      // mandar — o assistente é uma superfície ao lado, não o app inteiro.
      sessao.responde(
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
    <div className="painel" style={{ height: '100%' }}>
      <div className="assistente-cabeca">
        <span className="titulo-painel">Assistente</span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn" onClick={sessao.limpar} disabled={conversa.length === 0}>Limpar</button>
          <button className="btn btn-icone so-estreito" onClick={aoFechar} aria-label="Fechar assistente">
            <Icone.Fechar tamanho={16} />
          </button>
        </div>
      </div>

      <div className="conversa">
        {conversa.length === 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <p className="vazio">
              Pergunte em português. O modelo escolhe <em>quais componentes compor</em> —
              nunca escreve código, nunca vê os dados, nunca autoriza escrita.
            </p>
            <div className="sugestoes">
              {sugestoes.map((s) => (
                <button key={s} className="sugestao" onClick={() => void perguntar(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {conversa.map((m, i) => {
          if (m.papel === 'usuario') return <div key={i} className="msg-usuario">{m.texto}</div>
          if (m.papel === 'erro') return <p key={i} className="msg-erro">{m.texto}</p>
          if (m.papel === 'nota') return <p key={i} className="msg-nota">{m.texto}</p>
          const c = composicoes[m.composicaoId]
          if (!c) return null
          return (
            <div key={i}>
              <div className="composicao-inline">
                <div className="composicao-cabeca">
                  <span>{c.blocos.length} componente{c.blocos.length === 1 ? '' : 's'}</span>
                  {/* As mesmas ações do workspace, sem precisar abrir lá:
                      uma resposta boa costuma ser guardada ou repassada na hora. */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <button
                      className={`estrela ${fixadas.some((f) => f.viewKey === c.viewKey) ? 'is-fixada' : ''}`}
                      onClick={() => sessao.fixar(c)}
                      aria-pressed={fixadas.some((f) => f.viewKey === c.viewKey)}
                      aria-label="Fixar esta resposta" title="Fixar"
                    ><Icone.Estrela tamanho={15} preenchida={fixadas.some((f) => f.viewKey === c.viewKey)} /></button>
                    <button className="estrela" onClick={() => aoCompartilhar(c.id)}
                      aria-label="Compartilhar esta resposta" title="Compartilhar">
                      <Icone.Compartilhar tamanho={15} />
                    </button>
                    <button className="btn btn-primario" style={{ padding: '3px 9px', fontSize: 11 }}
                      onClick={() => sessao.aoWorkspace(c.id)}>
                      ao workspace
                    </button>
                  </div>
                </div>
                <div className="composicao-corpo">
                  <Render blocos={c.blocos} atorId={eu.id} />
                </div>
              </div>
            </div>
          )
        })}
        {pensando && <p className="msg-nota">compondo…</p>}
      </div>

      <form
        className="compositor"
        onSubmit={(e) => { e.preventDefault(); if (rascunho.trim()) void perguntar(rascunho) }}
      >
        <input
          className="compositor-campo"
          value={rascunho}
          onChange={(e) => setRascunho(e.target.value)}
          placeholder="o que está vencendo?"
          aria-label="Pergunta ao assistente"
        />
        <button className="compositor-enviar" disabled={pensando || !rascunho.trim()} aria-label="Perguntar">
          <Icone.Enviar tamanho={17} />
        </button>
      </form>
    </div>
  )
}
