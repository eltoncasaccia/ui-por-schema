import { useEffect, useState } from 'react'
import { api, type Eu } from './api'
import { Login } from './app/Login'
import { Painel } from './app/Painel'

export function App() {
  const [eu, setEu] = useState<Eu | null>(null)
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    api.eu().then(setEu).catch(() => setEu(null)).finally(() => setCarregando(false))
  }, [])

  if (carregando) return <p className="suave" style={{ padding: '2rem' }}>carregando…</p>
  if (!eu) return <Login aoEntrar={setEu} />
  return <Painel eu={eu} aoSair={() => { void api.sair(); setEu(null) }} />
}
