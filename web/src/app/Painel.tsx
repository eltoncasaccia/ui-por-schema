import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { ErroApi, api, type Bloco, type Eu } from '../api'
import { Composicao } from '../render/motor'

export function Painel({ eu, aoSair }: { eu: Eu; aoSair: () => void }) {
  const [pergunta, setPergunta] = useState('')
  const [blocos, setBlocos] = useState<Bloco[] | null>(null)
  const [erro, setErro] = useState('')
  const [pensando, setPensando] = useState(false)

  const catalogo = useQuery({ queryKey: [eu.id, 'catalogo'], queryFn: api.catalogo })

  async function perguntar(texto: string) {
    setPergunta(texto); setPensando(true); setErro(''); setBlocos(null)
    try {
      const c = await api.compor(texto)
      setBlocos(c.blocos)
      if (c.blocos.length === 0) setErro('O assistente não encontrou nada no seu catálogo para esta pergunta.')
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Falhou.")
    } finally {
      setPensando(false)
    }
  }

  /** Sem chave do modelo, o assistente falha — de propósito, nunca em silêncio.
   *  Abrir o componente direto mantém o sistema demonstrável mesmo assim. */
  function abrirDireto(id: string) {
    setBlocos([{ tipo: id, params: {}, tamanho: id === 'estoque_indicador' ? 'linha' : 'inteira' }])
    setErro(''); setPergunta('')
  }

  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', padding: '1.5rem 1.25rem 4rem' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.25rem' }}>Estoque Bertoni</h1>
          <p className="suave" style={{ margin: '.2rem 0 0', fontSize: '.9rem' }}>
            {eu.nome} · <span className="pilula">{eu.papel}</span>{' '}
            <span className="mono">{eu.unidades.join(' · ')}</span>
          </p>
        </div>
        <button onClick={aoSair}>sair</button>
      </header>

      <div className="cartao" style={{ padding: '1rem', marginTop: '1.5rem' }}>
        <form onSubmit={(e) => { e.preventDefault(); if (pergunta.trim()) void perguntar(pergunta) }}>
          <div style={{ display: 'flex', gap: '.6rem' }}>
            <input
              value={pergunta}
              onChange={(e) => setPergunta(e.target.value)}
              placeholder="o que está vencendo nos próximos 90 dias?"
              aria-label="Pergunta ao assistente"
            />
            <button className="primario" disabled={pensando || !pergunta.trim()}>
              {pensando ? 'compondo…' : 'perguntar'}
            </button>
          </div>
        </form>
        {catalogo.data && catalogo.data.length > 0 && (
          <p className="suave" style={{ fontSize: '.85rem', margin: '.7rem 0 0' }}>
            Exemplos: {catalogo.data.flatMap((c) => c.examples).slice(0, 3).map((ex, i) => (
              <button key={i} onClick={() => void perguntar(ex)}
                style={{ border: 0, background: 'none', padding: '0 .35rem', color: 'var(--acento)' }}>
                {ex}
              </button>
            ))}
          </p>
        )}
      </div>

      {erro && (
        <div className="cartao" style={{ padding: '.9rem 1rem', marginTop: '1rem', borderColor: '#e8d6d6' }}>
          <p style={{ margin: 0, color: 'var(--perigo)' }}>{erro}</p>
          {erro.includes('OPENROUTER') && (
            <p className="suave" style={{ margin: '.4rem 0 0', fontSize: '.88rem' }}>
              Ponha <code className="mono">OPENROUTER_API_KEY</code> no <code className="mono">.env</code>.
              O adaptador falha de propósito em vez de cair num simulador — foi assim
              que a primeira POC publicou números que não eram reais.
              Enquanto isso, abra um componente direto abaixo.
            </p>
          )}
        </div>
      )}

      {blocos && blocos.length > 0 && (
        <div style={{ marginTop: '1.5rem' }}>
          <Composicao blocos={blocos} atorId={eu.id} />
        </div>
      )}

      <section style={{ marginTop: '2.5rem' }}>
        <h2 style={{ fontSize: '.95rem' }}>Seu catálogo</h2>
        <p className="suave" style={{ fontSize: '.88rem', margin: '.3rem 0 1rem' }}>
          O vocabulário que o assistente recebe quando <strong>você</strong> pergunta.
          Outro papel recebe outro conjunto — é isso que impede o modelo de propor
          o que você não pode ver.
        </p>
        <div style={{ display: 'grid', gap: '.75rem' }}>
          {catalogo.data?.map((c) => (
            <div key={c.id} className="cartao" style={{ padding: '.85rem 1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                <strong className="mono">{c.id}</strong>
                <button onClick={() => abrirDireto(c.id)} style={{ padding: '.2rem .6rem', fontSize: '.85rem' }}>
                  abrir
                </button>
              </div>
              <p className="suave" style={{ margin: '.35rem 0 .5rem', fontSize: '.88rem' }}>{c.description}</p>
              {Object.entries(c.params).map(([nome, info]) =>
                info.valores ? (
                  <div key={nome} style={{ fontSize: '.82rem' }}>
                    <span className="suave mono">{nome}:</span>{' '}
                    {info.valores.map((v) => <span key={v} className="pilula" style={{ marginRight: '.3rem' }}>{v}</span>)}
                  </div>
                ) : null,
              )}
            </div>
          ))}
          {catalogo.data?.length === 0 && (
            <p className="suave">
              Seu usuário ainda não tem papel atribuído — catálogo vazio, nada visível.
              É o comportamento correto: cadastro não concede permissão.
            </p>
          )}
        </div>
      </section>
    </div>
  )
}
