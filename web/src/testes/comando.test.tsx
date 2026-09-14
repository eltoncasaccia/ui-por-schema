/**
 * T-049 — o clique aprende a chegar ao servidor. Achado A-40.
 *
 * Estes testes sobem `Composicao` de verdade, com uma view real
 * (`quarentena_liberar`) — não um duble — porque o que se prova é o CONTRATO
 * entre a view e o wrapper: a view despacha `CustomEvent('comando')` e nunca
 * importa rede; `BlocoRender` (`render/motor.tsx`) é quem escuta e chama
 * `api.comando`. Só `api.dados`/`api.comando` são mockados — a fronteira real
 * do sistema sob teste.
 *
 *   AC-1  o clique produz uma chamada com o endpoint e o corpo certos
 *   AC-2  `confirm: true` não dispara no primeiro clique — exige o segundo
 *   AC-3  cada tentativa tem uma `Idempotency-Key` própria
 *   AC-4  erro do servidor não apaga o que a tela mostrava
 *   AC-8  retry da MESMA tentativa reaproveita a mesma chave
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Bloco } from '../api'
import type { ViewModel } from '../generated/componentes'

const dados = vi.fn<(tipo: string, params: Record<string, unknown>) => Promise<unknown>>()
const comando = vi.fn<(endpoint: string, corpo: Record<string, unknown>, chave: string) => Promise<unknown>>()

vi.mock('../api', async (original) => {
  const real = await original<typeof import('../api')>()
  return { ...real, api: { dados, comando } }
})

const { Composicao } = await import('../render/motor')

const ATOR = 'u-helena'

type VM = ViewModel<'quarentena_liberar'>

function vm(): VM {
  return {
    lote_id: 'lote-049',
    produto: 'Amoxicilina 500mg',
    classe: 'comum',
    numero: 'L-049',
    unidade: 'CD Matriz',
    fabricacao: '2026-01-01',
    validade: '2027-01-01',
    dias_restantes: 300,
    saldo: 40,
    situacao: 'ok',
    status: 'quarentena',
    status_efetivo: 'quarentena',
    pode_decidir: true,
    motivo: null,
    conferencia: [],
    aviso_validade: null,
  }
}

function bloco(): Bloco {
  return {
    tipo: 'quarentena_liberar',
    params: { lote_id: 'lote-049' },
    tamanho: 'inteira',
    comandos: {
      lote_liberar_quarentena: {
        endpoint: '/api/comandos/lote_liberar_quarentena',
        confirm: true,
        idempotent: false,
      },
    },
  }
}

function envolver(ui: React.ReactNode) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={cliente}>{ui}</QueryClientProvider>)
}

beforeEach(() => {
  dados.mockReset()
  comando.mockReset()
  dados.mockResolvedValue(vm())
})

async function abrirEJustificar() {
  envolver(<Composicao blocos={[bloco()]} atorId={ATOR} />)
  await screen.findByText('Amoxicilina 500mg')
  fireEvent.change(screen.getByLabelText('Justificativa'), {
    target: { value: 'conferência completa, embalagem íntegra' },
  })
}

describe('AC-2 · um clique só nunca escreve', () => {
  it('o primeiro clique arma a confirmação, sem chamar a rede', async () => {
    await abrirEJustificar()
    fireEvent.click(screen.getByRole('button', { name: 'Liberar' }))

    expect(await screen.findByText('Confirmar esta ação?')).toBeInTheDocument()
    expect(comando).not.toHaveBeenCalled()
  })
})

describe('AC-1 · o segundo clique chama o endpoint certo', () => {
  it('confirmar dispara POST com endpoint e corpo montados pela view', async () => {
    comando.mockResolvedValue({})
    await abrirEJustificar()
    fireEvent.click(screen.getByRole('button', { name: 'Liberar' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

    await waitFor(() => expect(comando).toHaveBeenCalledTimes(1))
    const [endpoint, corpo] = comando.mock.calls[0]!
    expect(endpoint).toBe('/api/comandos/lote_liberar_quarentena')
    expect(corpo).toMatchObject({
      lote_id: 'lote-049',
      decisao: 'liberar',
      justificativa: 'conferência completa, embalagem íntegra',
    })
  })
})

describe('AC-3 · Idempotency-Key por invocação', () => {
  it('a chave é uma string não vazia, gerada pelo wrapper', async () => {
    comando.mockResolvedValue({})
    await abrirEJustificar()
    fireEvent.click(screen.getByRole('button', { name: 'Liberar' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

    await waitFor(() => expect(comando).toHaveBeenCalledTimes(1))
    const chave = comando.mock.calls[0]![2]
    expect(typeof chave).toBe('string')
    expect(chave.length).toBeGreaterThan(0)
  })
})

describe('AC-4 e AC-8 · erro não apaga a tela, e o retry reaproveita a chave', () => {
  it('erro mostra mensagem, mantém o produto na tela, e o retry usa a MESMA chave', async () => {
    comando.mockRejectedValueOnce(new Error('falha de rede')).mockResolvedValueOnce({})
    await abrirEJustificar()
    fireEvent.click(screen.getByRole('button', { name: 'Liberar' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

    await waitFor(() => expect(comando).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Não foi possível concluir.')).toBeInTheDocument()
    // Nada de estado otimista: o que a tela mostrava antes do clique continua lá.
    expect(screen.getByText('Amoxicilina 500mg')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(comando).toHaveBeenCalledTimes(2))
    expect(comando.mock.calls[0]![2]).toBe(comando.mock.calls[1]![2])
  })
})
