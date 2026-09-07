import { useEffect, useState } from 'react'
import { api, type Eu, type Persona } from '../api'

const PAPEL: Record<string, string> = {
  diretor: 'Diretor', rt: 'RT — farmacêutica responsável', gerente: 'Gerente',
  conferente: 'Conferente', comprador: 'Comprador', auditoria: 'Auditoria',
}

export function Login({ aoEntrar }: { aoEntrar: (eu: Eu) => void }) {
  const [personas, setPersonas] = useState<Persona[]>([])
  const [erro, setErro] = useState('')
  const [ocupado, setOcupado] = useState('')

  useEffect(() => { api.personas().then(setPersonas).catch(() => setPersonas([])) }, [])

  async function entrar(email: string) {
    setOcupado(email); setErro('')
    try {
      // A resposta do login É o ator completo — a mesma forma de /auth/eu.
      aoEntrar(await api.entrar(email, 'demo'))
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'falhou')
      setOcupado('')
    }
  }

  return (
    <main className="login">
      <h1>Estoque Bertoni</h1>
      <p className="muted">
        Uma IA compõe a interface escolhendo entre componentes registrados — sem
        gerar código, sem tocar nos dados, sem autorizar escrita.
      </p>
      <p className="muted" style={{ marginTop: 12 }}>
        Entre como duas pessoas diferentes e compare o catálogo. Não é a tela que
        muda: é o <strong>vocabulário que o modelo recebe</strong>.
      </p>

      <div className="login-lista">
        {personas.map((p) => (
          <button key={p.email} className="login-item" onClick={() => void entrar(p.email)}
            disabled={ocupado !== ''}>
            <span>
              <strong>{p.nome}</strong>
              <span className="login-papel"> · {PAPEL[p.papel] ?? p.papel}</span>
            </span>
            <span className="muted code">{ocupado === p.email ? '…' : '→'}</span>
          </button>
        ))}
        {personas.length === 0 && (
          <p className="muted" style={{ padding: 16 }}>
            Nenhuma persona. A API subiu? <code className="code">docker compose logs api</code>
          </p>
        )}
      </div>

      {erro && <p className="msg-error" style={{ marginTop: 12 }}>{erro}</p>}

      <p className="aviso">
        A Bertoni Distribuidora Farmacêutica é <strong>fictícia</strong> e todos os
        dados são gerados. O atalho de personas só existe com
        <code className="code"> MODO_DEMO=true</code> — fora dele a rota nem é registrada.
      </p>
    </main>
  )
}
