import { useEffect, useState } from 'react'

export type Tema = 'sistema' | 'claro' | 'escuro'
const CHAVE = 'estoque:tema'

/** `sistema` não carimba nada — o CSS decide por `prefers-color-scheme`. */
export function useTema(): [Tema, (t: Tema) => void] {
  const [tema, setTema] = useState<Tema>(() => {
    try {
      const g = localStorage.getItem(CHAVE)
      return g === 'claro' || g === 'escuro' ? g : 'sistema'
    } catch { return 'sistema' }  // navegador com armazenamento bloqueado
  })

  useEffect(() => {
    const raiz = document.documentElement
    if (tema === 'sistema') raiz.removeAttribute('data-tema')
    else raiz.setAttribute('data-tema', tema)
    try { localStorage.setItem(CHAVE, tema) } catch { /* sem persistência, tudo bem */ }
  }, [tema])

  return [tema, setTema]
}
