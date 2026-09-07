import { useEffect, useRef } from 'react'

/**
 * Carrega a próxima página quando a sentinela entra em vista.
 *
 * Sentinela, não `scroll`: o listener de scroll dispara centenas de vezes por
 * segundo e precisa medir a caixa a cada uma. O observador só acorda quando o
 * elemento aparece.
 */
export function useScrollInfinito(carregarMais: () => void, ativo: boolean) {
  const alvo = useRef<HTMLDivElement | null>(null)
  const fn = useRef(carregarMais)
  fn.current = carregarMais

  useEffect(() => {
    const no = alvo.current
    if (!no || !ativo) return
    if (typeof IntersectionObserver === 'undefined') return  // jsdom
    const obs = new IntersectionObserver(
      (entradas) => { if (entradas[0]?.isIntersecting) fn.current() },
      // Antecipa: começa a buscar antes de a pessoa chegar ao fim.
      { rootMargin: '320px' },
    )
    obs.observe(no)
    return () => obs.disconnect()
  }, [ativo])

  return alvo
}
