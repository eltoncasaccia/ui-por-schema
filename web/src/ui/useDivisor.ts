import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Divisor arrastável entre painéis.
 *
 * Acessível de propósito: é um `separator` com as setas do teclado, não só um
 * alvo de mouse. Quem navega por teclado também precisa ajustar a coluna.
 */
export function useDivisor(inicial: number, min: number, max: number, lado: 'esquerda' | 'direita') {
  const [largura, setLargura] = useState(inicial)
  const arrastando = useRef(false)

  const aoDescer = useCallback((e: React.PointerEvent) => {
    arrastando.current = true
    e.currentTarget.setPointerCapture(e.pointerId)
  }, [])

  useEffect(() => {
    function mover(e: PointerEvent) {
      if (!arrastando.current) return
      const x = lado === 'esquerda' ? e.clientX : window.innerWidth - e.clientX
      setLargura(Math.min(max, Math.max(min, x)))
    }
    function soltar() { arrastando.current = false }
    window.addEventListener('pointermove', mover)
    window.addEventListener('pointerup', soltar)
    return () => {
      window.removeEventListener('pointermove', mover)
      window.removeEventListener('pointerup', soltar)
    }
  }, [min, max, lado])

  const aoTeclado = useCallback((e: React.KeyboardEvent) => {
    const passo = e.shiftKey ? 48 : 16
    const dir = lado === 'esquerda' ? 1 : -1
    if (e.key === 'ArrowLeft') { e.preventDefault(); setLargura((l) => Math.max(min, l - passo * dir)) }
    if (e.key === 'ArrowRight') { e.preventDefault(); setLargura((l) => Math.min(max, l + passo * dir)) }
  }, [min, max, lado])

  return { largura, aoDescer, aoTeclado }
}
