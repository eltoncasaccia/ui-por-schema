/**
 * Contrato do sistema de design, verificado na folha de estilo.
 *
 * jsdom não aplica CSS, então testar aparência por `getComputedStyle` não prova
 * nada. O que dá para provar — e o que já quebrou de verdade — é que as regras
 * que impedem o layout de quebrar continuam declaradas.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const css = readFileSync(join(import.meta.dirname, '..', 'estilo.css'), 'utf8')

/** Casa o seletor no INÍCIO de uma linha — senão `.nav-item` acha
 *  `.fixada-linha .nav-item` e o teste passa a testar outra regra. */
function regra(seletor: string): string {
  const esc = seletor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const m = new RegExp(`^${esc}\\s*\\{`, 'm').exec(css)
  if (!m) throw new Error(`seletor ausente: ${seletor}`)
  return css.slice(m.index, css.indexOf('}', m.index))
}

describe('tokens', () => {
  it('define os dois temas', () => {
    expect(css).toContain(':root[data-tema="escuro"]')
    expect(css).toContain('@media (prefers-color-scheme: dark)')
  })

  it('o tema do sistema não vaza quando o usuário escolheu claro', () => {
    // Sem o :not, quem escolhe claro num SO escuro continua no escuro.
    expect(css).toContain(':root:not([data-tema="claro"])')
  })

  it('todo token de cor existe nos dois temas', () => {
    const nomes = [...regra(':root').matchAll(/--(s0|s1|s2|campo|linha|texto|dim|fraco|acento|bom|ambar|laranja|ruim):/g)]
      .map((m) => m[1])
    const escuro = regra(':root[data-tema="escuro"]')
    for (const n of nomes) expect(escuro, `--${n} falta no escuro`).toContain(`--${n}:`)
  })
})

describe('componentes não quebram', () => {
  it('rótulo e valor do indicador quebram palavra longa', () => {
    expect(regra('.indicador-rotulo')).toContain('overflow-wrap: anywhere')
    expect(regra('.indicador-valor')).toContain('overflow-wrap: anywhere')
  })

  it('o valor do indicador escala com a largura, em vez de estourar', () => {
    expect(regra('.indicador-valor')).toContain('clamp(')
  })

  it('a grade de indicadores nunca fica mais larga que o container', () => {
    // Sem o `min()`, a largura mínima estoura a coluna estreita do assistente
    // e as colunas se sobrepõem. Foi um bug real.
    expect(regra('.grade-indicadores')).toMatch(/minmax\(min\(\d+px, 100%\), 1fr\)/)
  })

  it('dentro do assistente os indicadores empilham', () => {
    expect(css).toContain('.assistente-dock .grade-indicadores')
  })

  it('alvo de toque de 44px é token, não número solto', () => {
    expect(regra(':root')).toContain('--toque: 44px')
    expect(regra('.nav-item')).toContain('min-height: var(--toque)')
  })
})

describe('sem clichês', () => {
  it('nenhum cartão tem barra de acento na borda esquerda', () => {
    // Está na lista de clichês da própria diretriz de design, e era o que o
    // indicador fazia: decoração repetindo o que a etiqueta já diz.
    expect(regra('.indicador')).not.toContain('border-left')
    expect(regra('.cartao')).not.toContain('border-left')
  })

  it('o número é o elemento dominante do indicador', () => {
    const valor = regra('.indicador-valor')
    const rotulo = regra('.indicador-rotulo')
    expect(valor).toContain('clamp(')
    expect(rotulo).toContain('font-size: 12px')
  })
})

describe('shell responsivo', () => {
  it('é mobile-first: o layout de coluna vem antes da media query', () => {
    expect(css.indexOf('.shell { display: flex; flex-direction: column')).toBeLessThan(
      css.indexOf('@media (min-width: 900px)'),
    )
  })

  it('divisores arrastáveis só existem no desktop', () => {
    expect(regra('.divisor')).toContain('display: none')
    expect(css.slice(css.indexOf('@media (min-width: 900px)'))).toContain('.divisor {')
  })

  it('respeita quem pediu menos movimento', () => {
    expect(css).toContain('prefers-reduced-motion: reduce')
  })
})
