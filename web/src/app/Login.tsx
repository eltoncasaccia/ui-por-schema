import { useEffect, useState } from 'react'
import { api, type Eu, type Persona } from '../api'

const PAPEL: Record<string, string> = {
  diretor: 'Diretor', rt: 'RT (farmacêutica)', gerente: 'Gerente',
  conferente: 'Conferente', comprador: 'Comprador', auditoria: 'Auditoria',
}

export function Login({ aoEntrar }: { aoEntrar: (eu: Eu) => void }) {
  const [personas, setPersonas] = useState<Persona[]>([])
  const [erro, setErro] = useState('')
  const [ocupado, setOcupado] = useState('')

  useEffect(() => { api.personas().then(setPersonas).catch(() => setPersonas([])) }, [])

  async function entrar(email: string) {
    setOcupado(email); setErro('')
    try { aoEntrar(await api.entrar(email, 'demo')) }
    catch (e) { setErro(e instanceof Error ? e.message : 'falhou') }
    finally { setOcupado('') }
  }

  return (
    <main style={{ maxWidth: 640, margin: '8vh auto', padding: '0 1.25rem' }}>
      <h1 style={{ fontSize: '1.6rem' }}>Estoque Bertoni</h1>
      <p className="suave" style={{ marginTop: '.4rem' }}>
        Entre como uma das personas para ver o modelo de permissão em ação.
        Cada uma recebe um catálogo diferente — e o assistente só consegue
        propor o que está no catálogo dela.
      </p>

      <div className="cartao" style={{ padding: '.5rem', marginTop: '1.5rem' }}>
        {personas.map((p) => (
          <button
            key={p.email}
            onClick={() => void entrar(p.email)}
            disabled={ocupado !== ''}
            style={{
              display: 'flex', width: '100%', border: 0, background: 'none',
              justifyContent: 'space-between', alignItems: 'center', padding: '.7rem .8rem',
            }}
          >
            <span><strong>{p.nome}</strong> <span className="suave">· {PAPEL[p.papel] ?? p.papel}</span></span>
            <span className="suave mono">{ocupado === p.email ? '…' : '→'}</span>
          </button>
        ))}
        {personas.length === 0 && (
          <p className="suave" style={{ padding: '1rem' }}>
            Nenhuma persona. Rode <code className="mono">make seed</code>.
          </p>
        )}
      </div>

      {erro && <p style={{ color: 'var(--perigo)' }}>{erro}</p>}

      <p className="suave" style={{ fontSize: '.85rem', marginTop: '1.5rem' }}>
        A Bertoni é uma empresa fictícia; todos os dados são gerados. O atalho de
        personas só existe com <code className="mono">MODO_DEMO=true</code> — fora
        dele, a rota nem é registrada.
      </p>
    </main>
  )
}
