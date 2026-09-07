import { useEffect, useState } from 'react'

/**
 * Observa a largura do próprio container, não da janela.
 *
 * A tabela precisa virar cartões quando a COLUNA é estreita — e a coluna do
 * assistente é estreita mesmo num monitor grande. Media query olharia a janela
 * e erraria exatamente esse caso.
 */
export function useEstreito(limite = 520): [(n: HTMLElement | null) => void, boolean] {
  const [no, setNo] = useState<HTMLElement | null>(null)
  const [estreito, setEstreito] = useState(false)

  useEffect(() => {
    if (!no) return
    if (typeof ResizeObserver === 'undefined') return  // jsdom, navegador antigo
    const obs = new ResizeObserver(([e]) => {
      if (e) setEstreito(e.contentRect.width < limite)
    })
    obs.observe(no)
    return () => obs.disconnect()
  }, [no, limite])

  return [setNo, estreito]
}
