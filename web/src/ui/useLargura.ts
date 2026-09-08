import { useEffect, useState } from 'react'

/**
 * Largura da janela, OBSERVADA.
 *
 * Ler `window.innerWidth` uma vez no render parece funcionar até alguém
 * redimensionar: o valor congela no que era na montagem, e o shell fica num
 * estado que não corresponde à tela — painel fixo cobrindo o workspace,
 * divisores em lugar nenhum. Foi exatamente o bug da captura.
 */
export function useLargura(): number {
  const [largura, setLargura] = useState(() =>
    typeof window === 'undefined' ? 1280 : window.innerWidth,
  )
  useEffect(() => {
    const aoRedimensionar = () => setLargura(window.innerWidth)
    window.addEventListener('resize', aoRedimensionar)
    return () => window.removeEventListener('resize', aoRedimensionar)
  }, [])
  return largura
}

export const LIMITE_ESTREITO = 900
