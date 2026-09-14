/**
 * `TelaOperacao` isolado: só a construção do bloco a partir do path e dos
 * params da URL. O comportamento de rede (AC-1, AC-2, AC-5) é coberto,
 * integrado com `Roteador`, em `src/testes/rotas_operacao.test.tsx`.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { Eu } from '../../api'

const dados = vi.fn<(tipo: string, params: Record<string, unknown>) => Promise<unknown>>()

vi.mock('../../api', async (original) => {
  const real = await original<typeof import('../../api')>()
  return { ...real, api: { ...real.api, dados: (t: string, p: Record<string, unknown>) => dados(t, p) } }
})

const { TelaOperacao } = await import('./TelaOperacao')
const { ROTAS_OPERACAO } = await import('../layout/rotasOperacao')

const EU: Eu = { id: 'u-1', nome: 'Alguém', papel: 'gerente', unidades: [], permissoes: [] }

function subir(caminho: string, path: string) {
  const rota = ROTAS_OPERACAO.find((r) => r.path === path)!
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={[caminho]}>
        <Routes>
          <Route path={path} element={<TelaOperacao rota={rota} eu={EU} />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('TelaOperacao', () => {
  it('rota sem parâmetro: pede o componente com os params fixos da tabela', async () => {
    dados.mockResolvedValue({ total: 0, escopo: '', recorte: [], linhas: [], resumo: [], cursor: null, tem_mais: false })
    subir('/lotes', '/lotes')
    await waitFor(() => expect(dados).toHaveBeenCalledWith('lote_lista', {}))
  })

  it('rota com :id extrai o param da URL para o componente certo', async () => {
    dados.mockResolvedValue({
      lote_id: 'L-9', produto: 'X', classe: 'comum', numero: 'N', unidade: 'CD Matriz',
      fabricacao: '2026-01-01', validade: '2027-01-01', dias_restantes: 10, saldo: 1,
      status_registrado: 'liberado', status_efetivo: 'liberado', situacao: 'ok', endereco: null,
    })
    subir('/lotes/L-9', '/lotes/:id')
    await waitFor(() => expect(dados).toHaveBeenCalledWith('lote_detalhe', { lote_id: 'L-9' }))
  })
})
