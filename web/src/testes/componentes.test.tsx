/**
 * Testes de comportamento dos componentes.
 *
 * O que importa aqui não é "renderiza sem erro" — é que o componente não
 * quebre nas situações que já quebraram: coluna estreita, rótulo longo,
 * número negativo, lista vazia, e a semântica de cor dos estados do lote.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BarraFaixas } from '../ui/BarraFaixas'
import { Indicador } from '../ui/Indicador'
import { Tabela, type Coluna } from '../ui/Tabela'
import { SITUACAO } from '../ui/estados'
import { view as ViewIndicador, formatar } from '../views/estoque_indicador'
import { view as ViewFila, dataBr, type Linha } from '../views/fila_vencimento'
import { view as ViewGrafico } from '../views/vencimento_grafico'
import { agrupar } from '../render/motor'
import type { Bloco } from '../api'

describe('Indicador', () => {
  it('mostra rótulo, valor e nota', () => {
    render(<Indicador rotulo="Em quarentena" valor="3" escopo="2 unidades" tom="ciano" />)
    expect(screen.getByText('Em quarentena')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('em 2 unidades')).toBeInTheDocument()
  })

  it('o detalhe acionável aparece quando existe', () => {
    render(<Indicador rotulo="Em quarentena" valor="3" detalhe="o mais antigo aguarda há 12 dias" />)
    expect(screen.getByText(/aguarda há 12 dias/)).toBeInTheDocument()
  })

  it('sem faixas não desenha barra — número sozinho continua legível', () => {
    const { container } = render(<Indicador rotulo="x" valor="1" />)
    expect(container.querySelector('.faixas')).toBeNull()
  })

  it('rótulo longo não estoura o cartão', () => {
    const { container } = render(<Indicador rotulo="Antimicrobianos_em_quarentena_refrigerada" valor="1" />)
    expect(container.querySelector('.indicador-rotulo')).toBeInTheDocument()
  })

  it('o tom vira classe, e é o único lugar onde a cor aparece', () => {
    const { container } = render(<Indicador rotulo="x" valor="1" tom="ruim" />)
    expect(container.querySelector('.indicador')).toHaveClass('tom-ruim')
  })
})

describe('estoque_indicador', () => {
  it('formata centavos como moeda e lotes como inteiro', () => {
    expect(formatar(24020700, 'centavos')).toMatch(/R\$\s?240\.207/)
    expect(formatar(1234, 'lotes')).toBe('1.234')
  })

  it('cada métrica carrega seu tom: quarentena informa, bloqueio alarma', () => {
    const { container: a } = render(
      <ViewIndicador vm={{ metrica: 'lotes_em_quarentena', rotulo: 'Quarentena', valor: 3, unidade_medida: 'lotes', escopo: '2 unidades', detalhe: null, faixas: [], tipo_faixa: 'nenhum' }} />,
    )
    expect(a.querySelector('.indicador')).toHaveClass('tom-ciano')
    const { container: b } = render(
      <ViewIndicador vm={{ metrica: 'lotes_bloqueados', rotulo: 'Bloqueados', valor: 1, unidade_medida: 'lotes', escopo: '2 unidades', detalhe: null, faixas: [], tipo_faixa: 'nenhum' }} />,
    )
    expect(b.querySelector('.indicador')).toHaveClass('tom-ruim')
  })

  it('mostra o escopo, para o número não ficar sem referência', () => {
    render(<ViewIndicador vm={{ metrica: 'x', rotulo: 'R', valor: 1, unidade_medida: 'lotes', escopo: 'CD Matriz', detalhe: null, faixas: [], tipo_faixa: 'nenhum' }} />)
    expect(screen.getByText('em CD Matriz')).toBeInTheDocument()
  })
})

describe('BarraFaixas', () => {
  const FAIXAS = [
    { rotulo: '61–90 dias', valor: 6, ordem: 0 },
    { rotulo: '31–60 dias', valor: 4, ordem: 1 },
    { rotulo: 'até 30 dias', valor: 2, ordem: 2 },
  ]

  it('identidade nunca por cor sozinha: todo segmento tem rótulo', () => {
    render(<BarraFaixas faixas={FAIXAS} tipo="urgencia" />)
    for (const f of FAIXAS) expect(screen.getByText(f.rotulo)).toBeInTheDocument()
  })

  it('a barra tem descrição acessível com os valores', () => {
    render(<BarraFaixas faixas={FAIXAS} tipo="urgencia" />)
    expect(screen.getByRole('img')).toHaveAccessibleName(/61–90 dias: 6/)
  })

  it('total zero não desenha nada — barra vazia é ruído', () => {
    const { container } = render(<BarraFaixas faixas={[{ rotulo: 'x', valor: 0, ordem: 0 }]} tipo="urgencia" />)
    expect(container.firstChild).toBeNull()
  })

  it('o segmento cresce com o valor, não com a posição', () => {
    const { container } = render(<BarraFaixas faixas={FAIXAS} tipo="urgencia" />)
    const segs = [...container.querySelectorAll('.seg')] as HTMLElement[]
    expect(segs.map((s) => s.style.flexGrow)).toEqual(['6', '4', '2'])
  })
})

describe('estados do lote', () => {
  it('alerta e bloqueio têm tons DIFERENTES', () => {
    // A diferença entre eles é programar uma venda ou recolher da prateleira.
    expect(SITUACAO.alerta_90.tom).not.toBe(SITUACAO.bloqueio_30.tom)
  })

  it('vencido é o tom mais grave, e não se confunde com alerta', () => {
    expect(SITUACAO.vencido.tom).toBe('ruim')
    expect(SITUACAO.vencido.tom).not.toBe(SITUACAO.alerta_90.tom)
  })
})

const RESUMO = [{ rotulo: 'até 30 dias', valor: 2, ordem: 2 }]
const LINHAS: Linha[] = [
  { lote_id: 'L1', produto: 'Amoxicilina 500mg', numero: 'AV1', unidade: 'cd-matriz',
    validade: '2026-08-28', dias_restantes: -10, saldo: 649, situacao: 'vencido' },
  { lote_id: 'L2', produto: 'Dipirona 500mg', numero: 'D15', unidade: 'cd-matriz',
    validade: '2026-09-22', dias_restantes: 15, saldo: 318, situacao: 'bloqueio_30' },
]

describe('fila_vencimento', () => {
  it('data ISO vira formato brasileiro', () => {
    expect(dataBr('2026-08-28')).toBe('28/08/2026')
  })

  it('dia negativo usa o minus tipográfico, para alinhar com os dígitos', () => {
    render(<ViewFila vm={{ janela_dias: 90, total: 2, linhas: LINHAS, resumo: RESUMO, cursor: null, tem_mais: false }} />)
    expect(screen.getByText('−10')).toBeInTheDocument()
  })

  it('cada linha carrega a etiqueta do seu estado', () => {
    render(<ViewFila vm={{ janela_dias: 90, total: 2, linhas: LINHAS, resumo: RESUMO, cursor: null, tem_mais: false }} />)
    expect(screen.getByText('Vencido')).toBeInTheDocument()
    expect(screen.getByText('Bloqueio 30d')).toBeInTheDocument()
  })

  it('lista vazia não quebra', () => {
    render(<ViewFila vm={{ janela_dias: 30, total: 0, linhas: [], resumo: [], cursor: null, tem_mais: false }} />)
    expect(screen.getByText('Nada aqui.')).toBeInTheDocument()
  })
})

const COLS: Coluna<{ id: string; n: number }>[] = [
  { chave: 'id', rotulo: 'Id', render: (l) => l.id },
  { chave: 'n', rotulo: 'N', num: true, campo: true, render: (l) => l.n },
]

describe('Tabela', () => {
  it('em coluna larga renderiza tabela de verdade — cabeçalho e células', () => {
    render(<Tabela colunas={COLS} linhas={[{ id: 'a', n: 1 }]} chave={(l) => l.id} titulo={(l) => l.id} />)
    const tabela = screen.getByRole('table')
    expect(within(tabela).getByText('Id')).toBeInTheDocument()
  })

  it('nenhuma coluna some: toda coluna do cabeçalho existe', () => {
    render(<Tabela colunas={COLS} linhas={[{ id: 'a', n: 1 }]} chave={(l) => l.id} titulo={(l) => l.id} />)
    expect(screen.getAllByRole('columnheader')).toHaveLength(COLS.length)
  })
})

describe('motor de render', () => {
  const b = (tipo: string, tamanho: string): Bloco => ({ tipo, params: {}, tamanho })

  it('indicadores adjacentes viram UMA grade, não cartões soltos', () => {
    const g = agrupar([b('a', 'linha'), b('b', 'linha'), b('c', 'linha')])
    expect(g).toHaveLength(1)
    expect(g[0]!.itens).toHaveLength(3)
  })

  it('componente inteiro fica sozinho', () => {
    const g = agrupar([b('a', 'linha'), b('t', 'inteira'), b('c', 'linha')])
    expect(g.map((x) => x.tipo)).toEqual(['grade', 'solo', 'grade'])
  })

  it('lista vazia não gera grupo', () => {
    expect(agrupar([])).toEqual([])
  })
})

describe('não vazar existência', () => {
  it('a mensagem de composição vazia não diz que o dado existe', () => {
    // Foi um vazamento real: "nada no seu catálogo responde a isso" conta que
    // há um catálogo, e que o dado pode estar do outro lado dele.
    const fonte = readFileSync(join(import.meta.dirname, '..', 'shell', 'PainelAssistente.tsx'), 'utf8')
    for (const proibido of ['sem permissão', 'não pode ver', 'seu catálogo', 'sem acesso a esse dado']) {
      expect(fonte.toLowerCase()).not.toContain(proibido)
    }
  })

  it('bloco negado por registro não renderiza nada', () => {
    const motor = readFileSync(join(import.meta.dirname, '..', 'render', 'motor.tsx'), 'utf8')
    expect(motor).toContain("e.codigo === 'nao_encontrado') return null")
  })
})

describe('vencimento_grafico', () => {
  const VM = {
    horizonte_dias: 180, escopo: '2 unidades', total_lotes: 30, pico_rotulo: '08 out',
    baldes: [
      { rotulo: '08 set', inicio: '2026-09-08', lotes: 10, unidades: 400, urgencia: 2 },
      { rotulo: '23 set', inicio: '2026-09-23', lotes: 0, unidades: 0, urgencia: 2 },
      { rotulo: '08 out', inicio: '2026-10-08', lotes: 20, unidades: 900, urgencia: 1 },
    ],
    legenda: ['vencidos', 'até 30 dias', '31–90 dias', 'acima de 90 dias'],
  }

  it('a altura da barra é proporcional ao valor, não à posição', () => {
    const { container } = render(<ViewGrafico vm={VM} />)
    const alturas = [...container.querySelectorAll('.gr-barra')].map((b) => (b as HTMLElement).style.height)
    expect(alturas).toEqual(['50%', '0%', '100%'])
  })

  it('tem descrição acessível com os períodos que têm lotes', () => {
    render(<ViewGrafico vm={VM} />)
    expect(screen.getByRole('img')).toHaveAccessibleName(/08 set, 10/)
  })

  it('balde vazio não recebe foco — nada a inspecionar ali', () => {
    const { container } = render(<ViewGrafico vm={VM} />)
    const tabs = [...container.querySelectorAll('.gr-col')].map((c) => c.getAttribute('tabindex'))
    expect(tabs).toEqual(['0', '-1', '0'])
  })

  it('horizonte sem nada não desenha barra nenhuma', () => {
    const { container } = render(
      <ViewGrafico vm={{ ...VM, total_lotes: 0, pico_rotulo: null, baldes: [] }} />,
    )
    expect(container.querySelector('.gr')).toBeNull()
    expect(screen.getByText('Nada vence neste horizonte.')).toBeInTheDocument()
  })

  it('o eixo desbasta rótulos em vez de sobrepor', () => {
    const muitos = Array.from({ length: 24 }, (_, i) => ({
      rotulo: `d${i}`, inicio: `2026-01-${i + 1}`, lotes: i, unidades: i, urgencia: 0,
    }))
    const { container } = render(<ViewGrafico vm={{ ...VM, baldes: muitos }} />)
    const visiveis = [...container.querySelectorAll('.gr-eixo > span')].filter((s) => s.textContent)
    expect(visiveis.length).toBeLessThanOrEqual(8)
  })
})
