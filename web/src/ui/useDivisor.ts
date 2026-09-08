import { useCallback, useEffect, useRef, useState } from 'react'

/** Largura da barra de atividades — o painel esquerdo começa DEPOIS dela. */
const BARRA = 52

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
    // Sem isto o navegador seleciona texto enquanto se arrasta, e o cursor
    // pisca entre `col-resize` e `text`.
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'col-resize'
  }, [])

  useEffect(() => {
    function mover(e: PointerEvent) {
      if (!arrastando.current) return
      // O painel esquerdo começa depois da barra de atividades. Usar `clientX`
      // cru fazia a coluna saltar 52px no primeiro movimento.
      const x = lado === 'esquerda' ? e.clientX - BARRA : window.innerWidth - e.clientX
      setLargura(Math.min(max, Math.max(min, x)))
    }
    function soltar() {
      if (!arrastando.current) return
      arrastando.current = false
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }
    window.addEventListener('pointermove', mover)
    window.addEventListener('pointerup', soltar)
    window.addEventListener('pointercancel', soltar)
    return () => {
      window.removeEventListener('pointermove', mover)
      window.removeEventListener('pointerup', soltar)
      window.removeEventListener('pointercancel', soltar)
    }
  }, [min, max, lado])

  const aoTeclado = useCallback((e: React.KeyboardEvent) => {
    const passo = e.shiftKey ? 48 : 16
    const dir = lado === 'esquerda' ? 1 : -1
    if (e.key === 'ArrowLeft') { e.preventDefault(); setLargura((l) => Math.max(min, Math.min(max, l - passo * dir))) }
    if (e.key === 'ArrowRight') { e.preventDefault(); setLargura((l) => Math.max(min, Math.min(max, l + passo * dir))) }
  }, [min, max, lado])

  return { largura, aoDescer, aoTeclado }
}
