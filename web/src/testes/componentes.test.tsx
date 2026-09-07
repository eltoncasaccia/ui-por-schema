/**
 * Testes de comportamento dos componentes.
 *
 * O que importa aqui não é "renderiza sem erro" — é que o componente não
 * quebre nas situações que já quebraram: coluna estreita, rótulo longo,
 * número negativo, lista vazia, e a semântica de cor dos estados do lote.
 */
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Indicador } from '../ui/Indicador'
import { Tabela, type Coluna } from '../ui/Tabela'
import { SITUACAO } from '../ui/estados'
import { view as ViewIndicador, formatar } from '../views/estoque_indicador'
import { view as ViewFila, dataBr, type Linha } from '../views/fila_vencimento'
import { agrupar } from '../render/motor'
import type { Bloco } from '../api'

describe('Indicador', () => {
  it('mostra rótulo, valor e nota', () => {
    render(<Indicador rotulo="Em quarentena" valor="3" nota="lotes" tom="ciano" />)
    expect(screen.getByText('Em quarentena')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
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
      <ViewIndicador vm={{ metrica: 'lotes_em_quarentena', rotulo: 'Quarentena', valor: 3, unidade_medida: 'lotes' }} />,
    )
    expect(a.querySelector('.indicador')).toHaveClass('tom-ciano')
    const { container: b } = render(
      <ViewIndicador vm={{ metrica: 'lotes_bloqueados', rotulo: 'Bloqueados', valor: 1, unidade_medida: 'lotes' }} />,
    )
    expect(b.querySelector('.indicador')).toHaveClass('tom-ruim')
  })

  it('singular e plural na nota', () => {
    render(<ViewIndicador vm={{ metrica: 'x', rotulo: 'R', valor: 1, unidade_medida: 'lotes' }} />)
    expect(screen.getByText('lote')).toBeInTheDocument()
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
    render(<ViewFila vm={{ janela_dias: 90, total: 2, linhas: LINHAS }} />)
    expect(screen.getByText('−10')).toBeInTheDocument()
  })

  it('cada linha carrega a etiqueta do seu estado', () => {
    render(<ViewFila vm={{ janela_dias: 90, total: 2, linhas: LINHAS }} />)
    expect(screen.getByText('Vencido')).toBeInTheDocument()
    expect(screen.getByText('Bloqueio 30d')).toBeInTheDocument()
  })

  it('lista vazia não quebra', () => {
    render(<ViewFila vm={{ janela_dias: 30, total: 0, linhas: [] }} />)
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
