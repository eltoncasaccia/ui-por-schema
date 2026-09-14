/**
 * `/saida` não tem `:id` na URL — ver o comentário em `TelaSaida.tsx`. O que
 * se prova aqui é só essa parte: sem produto informado, pede o id; com ele
 * (digitado ou por `?produto_id=`), monta o MESMO bloco `movimento_saida`
 * que uma rota comum montaria.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { Eu } from '../../api'

const dados = vi.fn<(tipo: string, params: Record<string, unknown>) => Promise<unknown>>()

vi.mock('../../api', async (original) => {
  const real = await original<typeof import('../../api')>()
  return { ...real, api: { ...real.api, dados: (t: string, p: Record<string, unknown>) => dados(t, p) } }
})

const { TelaSaida } = await import('./TelaSaida')

const EU: Eu = { id: 'u-1', nome: 'Alguém', papel: 'gerente', unidades: [], permissoes: [] }

const VM_SAIDA = {
  produto: 'Amoxicilina 500mg', classe: 'comum', escopo: 'CD Matriz', exige_autorizacao: false,
  proposta: null, alternativas: [], motivos: [], sem_estoque: false,
}

function subir(caminho: string) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={[caminho]}>
        <Routes><Route path="/saida" element={<TelaSaida eu={EU} />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('TelaSaida', () => {
  it('sem produto: pede o id e não chama o componente ainda', () => {
    subir('/saida')
    expect(screen.getByLabelText('Id do produto')).toBeInTheDocument()
    expect(dados).not.toHaveBeenCalled()
  })

  it('digitar e confirmar monta movimento_saida com o produto_id digitado', async () => {
    dados.mockResolvedValue(VM_SAIDA)
    subir('/saida')

    fireEvent.change(screen.getByLabelText('Id do produto'), { target: { value: 'prod-77' } })
    fireEvent.click(screen.getByText('Continuar'))

    await waitFor(() => expect(dados).toHaveBeenCalledWith('movimento_saida', { produto_id: 'prod-77' }))
  })

  it('?produto_id= na URL pula direto para o componente', async () => {
    dados.mockResolvedValue(VM_SAIDA)
    subir('/saida?produto_id=prod-88')

    await waitFor(() => expect(dados).toHaveBeenCalledWith('movimento_saida', { produto_id: 'prod-88' }))
    expect(screen.queryByLabelText('Id do produto')).toBeNull()
  })
})
