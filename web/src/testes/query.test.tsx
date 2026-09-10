/**
 * T-016 AC-2 e AC-3 — os dois mecanismos que a v1 escreveu à mão.
 *
 * O ADR-0008 diz que invalidação de pedido superado e coalescing "vêm prontos"
 * do TanStack Query. Vir pronto não é o mesmo que estar ligado: os dois
 * dependem de a `queryKey` ser exatamente `[ator, tipo, params]`. Uma chave que
 * carregasse um `Date.now()`, um objeto recriado a cada render ou um contador
 * desliga os dois em silêncio — a tela continua funcionando, só que fazendo
 * quatro requisições onde devia fazer uma, e aceitando a resposta atrasada.
 *
 * Por isso os testes são sobre o COMPORTAMENTO observável, e não sobre o
 * TanStack: contam requisições e olham o que ficou na tela.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Bloco } from '../api'

const dados = vi.fn<(tipo: string, params: Record<string, unknown>) => Promise<unknown>>()

vi.mock('../api', async (original) => ({
  ...(await original<typeof import('../api')>()),
  api: { dados },
}))

const { Composicao } = await import('../render/motor')

const ATOR = 'u-ivo'

function indicador(rotulo: string, valor: number) {
  return {
    metrica: 'lotes_em_quarentena',
    rotulo,
    valor,
    unidade_medida: 'lotes',
    escopo: '2 unidades',
    detalhe: null,
    faixas: [],
    tipo_faixa: 'nenhum',
  }
}

function bloco(params: Record<string, unknown>): Bloco {
  return { tipo: 'estoque_indicador', params, tamanho: 'linha' }
}

/** Cliente novo por teste: cache compartilhado faria o segundo teste passar
 *  pelo resultado do primeiro. */
function envolver(ui: React.ReactNode) {
  const cliente = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(<QueryClientProvider client={cliente}>{ui}</QueryClientProvider>)
}

beforeEach(() => {
  dados.mockReset()
})

// --- AC-3 · coalescing ------------------------------------------------------

describe('AC-3 · quatro blocos da mesma entidade disparam uma requisição', () => {
  it('quatro blocos idênticos = 1 requisição', async () => {
    dados.mockResolvedValue(indicador('Quarentena', 3))
    const iguais = [bloco({}), bloco({}), bloco({}), bloco({})]

    envolver(<Composicao blocos={iguais} atorId={ATOR} />)

    await waitFor(() => expect(screen.getAllByText('3')).toHaveLength(4))
    expect(dados).toHaveBeenCalledTimes(1)
  })

  it('params diferentes NÃO são coalescidos — o par negativo', async () => {
    // Sem este, uma chave constante (que coalesceria tudo, inclusive o que não
    // devia) passaria no teste acima e serviria o dado errado nos dois blocos.
    dados.mockImplementation((_tipo: string, params: Record<string, unknown>) =>
      Promise.resolve(indicador('Quarentena', params.unidade_id === 'cd-matriz' ? 7 : 2)),
    )

    envolver(
      <Composicao
        blocos={[bloco({ unidade_id: 'cd-matriz' }), bloco({ unidade_id: 'cd-refrigerado' })]}
        atorId={ATOR}
      />,
    )

    await waitFor(() => expect(screen.getByText('7')).toBeInTheDocument())
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(dados).toHaveBeenCalledTimes(2)
  })

  it('o mesmo bloco para OUTRO ator não reaproveita o cache', async () => {
    // O ADR-0008 na forma que já falhou de verdade: cache que cruza usuário.
    dados.mockResolvedValue(indicador('Quarentena', 1))
    const { rerender } = envolver(<Composicao blocos={[bloco({})]} atorId="u-a" />)
    await waitFor(() => expect(dados).toHaveBeenCalledTimes(1))

    // Mesmo cliente de cache, ator diferente: tem de buscar de novo.
    rerender(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <Composicao blocos={[bloco({})]} atorId="u-b" />
      </QueryClientProvider>,
    )
    await waitFor(() => expect(dados).toHaveBeenCalledTimes(2))
  })
})

// --- AC-2 · invalidação de pedido superado ---------------------------------

describe('AC-2 · a resposta atrasada de A não sobrescreve B', () => {
  it('abrir A e imediatamente B mostra B, mesmo com A respondendo depois', async () => {
    let resolverA: ((v: unknown) => void) | undefined
    dados.mockImplementation((_tipo: string, params: Record<string, unknown>) => {
      if (params.unidade_id === 'A') {
        return new Promise((res) => {
          resolverA = res
        })
      }
      return Promise.resolve(indicador('B', 222))
    })

    const { rerender } = envolver(
      <Composicao blocos={[bloco({ unidade_id: 'A' })]} atorId={ATOR} />,
    )
    // Troca para B antes de A responder — é o caso que a v1 tratava à mão.
    rerender(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <Composicao blocos={[bloco({ unidade_id: 'B' })]} atorId={ATOR} />
      </QueryClientProvider>,
    )
    await waitFor(() => expect(screen.getByText('222')).toBeInTheDocument())

    // A responde agora, atrasado, com um valor que não pode aparecer.
    resolverA?.(indicador('A', 111))
    await new Promise((r) => setTimeout(r, 10))

    expect(screen.queryByText('111')).toBeNull()
    expect(screen.getByText('222')).toBeInTheDocument()
  })
})
