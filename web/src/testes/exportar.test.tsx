/**
 * T-054 — o botão de exportar no bloco. AC-9 (lado do cliente) e AC-11.
 *
 * Sobe `Composicao` de verdade, com a view real de `relatorio_movimentacao`;
 * só a fronteira (`api`) é mockada. O que se prova: o botão existe só para o
 * que o catálogo DESTE ator marca como exportável, o pedido leva os params do
 * bloco, e a recusa do servidor aparece em texto — não some.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Bloco, EntradaCatalogo, FormatoExportacao } from '../api'
import type { ViewModel } from '../generated/componentes'

const dados = vi.fn<(tipo: string, params: Record<string, unknown>) => Promise<unknown>>()
const catalogo = vi.fn<() => Promise<EntradaCatalogo[]>>()
const exportar = vi.fn<
  (id: string, params: Record<string, unknown>, formato: FormatoExportacao) =>
    Promise<{ arquivo: Blob; nome: string }>
>()
const etagAtual = vi.fn(() => undefined)

vi.mock('../api', async (original) => {
  const real = await original<typeof import('../api')>()
  return { ...real, api: { dados, catalogo, exportar, etagAtual } }
})

const { Composicao } = await import('../render/motor')
const { ErroApi } = await import('../api')

const PARAMS = { agrupar_por: 'unidade', periodo: '90' }
const BLOCO: Bloco = { tipo: 'relatorio_movimentacao', params: PARAMS, tamanho: 'inteira' }

const VM: ViewModel<'relatorio_movimentacao'> = {
  eixo: 'por unidade', metrica: 'quantidade', metrica_rotulo: 'Quantidade movimentada',
  unidade_medida: 'unidades', total: 10, grupos: 1, escopo: '1 unidade',
  recorte: 'últimos 90 dias', truncado: false,
  linhas: [{ chave: 'cd-matriz', rotulo: 'Matriz', numero: 10, movimentos: 2 }],
  cursor: null, tem_mais: false,
}

function entrada(id: string, exportavel: boolean): EntradaCatalogo {
  return { id, label: id, description: '', examples: [], params: {}, exportavel }
}

// `MemoryRouter`: `BlocoRender` usa `useSearchParams` desde a T-055.
function montar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Composicao blocos={[BLOCO]} atorId="u-marco" />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const criarUrl = vi.fn(() => 'blob:teste')
const clicar = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

beforeEach(() => {
  dados.mockReset().mockResolvedValue(VM)
  catalogo.mockReset()
  exportar.mockReset()
  clicar.mockClear()
  criarUrl.mockClear()
  Object.assign(URL, { createObjectURL: criarUrl, revokeObjectURL: vi.fn() })
})

afterEach(() => vi.clearAllTimers())

describe('exportar um bloco', () => {
  it('AC-11 · pede o formato escolhido com os params do bloco e baixa o arquivo', async () => {
    catalogo.mockResolvedValue([entrada('relatorio_movimentacao', true)])
    const arquivo = new Blob(['x'])
    exportar.mockResolvedValue({ arquivo, nome: 'movimentacao-por-unidade-2026-09-16.xlsx' })
    montar()

    fireEvent.click(await screen.findByRole('button', { name: /Exportar/ }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Planilha (.xlsx)' }))

    await waitFor(() => expect(clicar).toHaveBeenCalledOnce())
    expect(exportar).toHaveBeenCalledWith('relatorio_movimentacao', PARAMS, 'xlsx')
    expect(criarUrl).toHaveBeenCalledWith(arquivo)
    const a = clicar.mock.contexts[0] as HTMLAnchorElement
    expect(a.download).toBe('movimentacao-por-unidade-2026-09-16.xlsx')
  })

  it('AC-11 · os três formatos estão no menu', async () => {
    catalogo.mockResolvedValue([entrada('relatorio_movimentacao', true)])
    montar()
    fireEvent.click(await screen.findByRole('button', { name: /Exportar/ }))
    expect(screen.getAllByRole('menuitem').map((b) => b.textContent)).toEqual([
      'CSV', 'Planilha (.xlsx)', 'PDF',
    ])
  })

  it('AC-11 · Esc e clique fora fecham o menu sem exportar', async () => {
    catalogo.mockResolvedValue([entrada('relatorio_movimentacao', true)])
    montar()
    const botao = await screen.findByRole('button', { name: /Exportar/ })
    fireEvent.click(botao)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    fireEvent.click(botao)
    fireEvent.mouseDown(document.body)
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    expect(exportar).not.toHaveBeenCalled()
  })

  it('AC-11 · recusa do servidor aparece em texto, e a tela continua', async () => {
    catalogo.mockResolvedValue([entrada('relatorio_movimentacao', true)])
    exportar.mockRejectedValue(
      new ErroApi('invalido', 'Mais de 5000 linhas. Estreite o filtro para exportar.'),
    )
    montar()
    fireEvent.click(await screen.findByRole('button', { name: /Exportar/ }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'PDF' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Estreite o filtro')
    expect(clicar).not.toHaveBeenCalled()
    expect(screen.getByText('Matriz')).toBeInTheDocument()
  })

  it('AC-9 · componente que o servidor não exporta não tem botão', async () => {
    catalogo.mockResolvedValue([entrada('relatorio_movimentacao', false)])
    montar()
    await screen.findByText('Matriz')
    await waitFor(() => expect(catalogo).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: /Exportar/ })).not.toBeInTheDocument()
  })

  it('AC-9 · componente fora do catálogo deste ator não tem botão', async () => {
    catalogo.mockResolvedValue([entrada('lote_lista', true)])
    montar()
    await screen.findByText('Matriz')
    await waitFor(() => expect(catalogo).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: /Exportar/ })).not.toBeInTheDocument()
  })
})
