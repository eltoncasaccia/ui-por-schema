/**
 * T-055 — a barra de filtro ao redor do bloco (achado A-46).
 *
 * Sobe `Composicao` de verdade, com a view real de `fila_vencimento`; só
 * `api.dados` é mockado. O que vale aqui é o negativo: identificador nunca
 * vira controle (AC-4), e um componente fora do escopo desta tarefa não
 * ganha barra nenhuma.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useSearchParams } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Bloco } from '../api'
import { FILTROS, type ViewModel } from '../generated/componentes'

/** `MemoryRouter` tem história própria, isolada de `window.location` — de
 * propósito, é o que faz o teste não depender de jsdom navegando de verdade.
 * Esta sonda lê a MESMA história por dentro, pelo mesmo hook que
 * `BlocoRender` usa, pra afirmar o AC-2 sem tocar `window.location`. */
function SondaBusca() {
  const [busca] = useSearchParams()
  return <span data-testid="busca">{busca.toString()}</span>
}

const dados = vi.fn<(tipo: string, params: Record<string, unknown>) => Promise<unknown>>()

vi.mock('../api', async (original) => ({
  ...(await original<typeof import('../api')>()),
  api: { dados },
}))

const { Composicao } = await import('../render/motor')

const ATOR = 'u-ivo'

function vencimentoVm(total: number): ViewModel<'fila_vencimento'> {
  return {
    janela_dias: 90,
    total,
    linhas: [],
    resumo: [],
    cursor: null,
    tem_mais: false,
  }
}

function bloco(params: Record<string, unknown>): Bloco {
  return { tipo: 'fila_vencimento', params, tamanho: 'inteira' }
}

function envolver(ui: React.ReactNode, rota = '/') {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={[rota]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  dados.mockReset()
  dados.mockResolvedValue(vencimentoVm(1))
})

describe('AC-1 · controle aparece com o padrão do componente pré-selecionado', () => {
  it('janela e unidade viram <select>, com o valor de params já escolhido', async () => {
    envolver(<Composicao blocos={[bloco({ janela: '90' })]} atorId={ATOR} />)

    const janela = await screen.findByLabelText<HTMLSelectElement>('Janela')
    expect(janela.value).toBe('90')
    expect(screen.getByLabelText('Unidade')).toBeInTheDocument()
  })

  it('trocar o filtro busca de novo, sem recarregar a página', async () => {
    envolver(<Composicao blocos={[bloco({ janela: '90' })]} atorId={ATOR} />)
    await screen.findByLabelText('Janela')
    expect(dados).toHaveBeenCalledTimes(1)

    fireEvent.change(screen.getByLabelText('Janela'), { target: { value: '30' } })

    await waitFor(() => expect(dados).toHaveBeenCalledTimes(2))
    const [, paramsSegundaChamada] = dados.mock.calls[1]!
    expect(paramsSegundaChamada.janela).toBe('30')
  })
})

describe('AC-2 · o filtro escolhido fica na URL', () => {
  it('a URL começa sem o filtro, e trocar o select escreve nela', async () => {
    envolver(
      <>
        <SondaBusca />
        <Composicao blocos={[bloco({ janela: '90' })]} atorId={ATOR} />
      </>,
    )
    await screen.findByLabelText('Janela')
    expect(screen.getByTestId('busca')).toHaveTextContent('')

    fireEvent.change(screen.getByLabelText('Janela'), { target: { value: '30' } })
    await waitFor(() => expect(dados).toHaveBeenCalledTimes(2))

    expect(screen.getByTestId('busca')).toHaveTextContent('fila_vencimento.janela=30')
  })

  it('abrir com a URL já preenchida usa o valor dela, não o padrão do bloco', async () => {
    envolver(
      <Composicao blocos={[bloco({ janela: '90' })]} atorId={ATOR} />,
      '/?fila_vencimento.janela=30',
    )

    const janela = await screen.findByLabelText<HTMLSelectElement>('Janela')
    expect(janela.value).toBe('30')
    const [, params] = dados.mock.calls[0]!
    expect(params.janela).toBe('30')
  })
})

describe('AC-4 · identificador nunca vira controle de filtro (negativo)', () => {
  it('FILTROS não tem lote_id, produto_id, recebimento_id, movimento_id nem ean, em componente nenhum', () => {
    const identificadores = ['lote_id', 'produto_id', 'recebimento_id', 'movimento_id', 'ean']
    for (const [, campos] of Object.entries(FILTROS)) {
      for (const id of identificadores) expect(campos).not.toHaveProperty(id)
    }
  })
})

describe('componente fora do escopo da T-055 não ganha barra', () => {
  it('lote_detalhe não declara filtros — nenhum <select> aparece', async () => {
    const vm: ViewModel<'lote_detalhe'> = {
      lote_id: 'L-1', produto: 'Amoxicilina 500mg', classe: 'comum', numero: 'N-1',
      unidade: 'CD Matriz', fabricacao: '2026-01-01', validade: '2027-01-01',
      dias_restantes: 300, saldo: 10, situacao: 'ok', status_registrado: 'liberado',
      status_efetivo: 'liberado', endereco: null,
    }
    dados.mockResolvedValue(vm)
    envolver(
      <Composicao blocos={[{ tipo: 'lote_detalhe', params: { lote_id: 'L-1' }, tamanho: 'inteira' }]} atorId={ATOR} />,
    )
    await waitFor(() => expect(screen.queryByText('carregando…')).not.toBeInTheDocument())
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })
})
