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
 *
 * T-050 (etag): `api.etagAtual` é o que devolve o etag da última leitura — o
 * mock devolve um valor fixo, para o teste afirmar que ele chega a
 * `api.comando` sem o cliente ter que fazer round trip nenhum.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Bloco } from '../api'
import type { ViewModel } from '../generated/componentes'

const ETAG = 'etag-fixo-do-teste'
const dados = vi.fn<(tipo: string, params: Record<string, unknown>) => Promise<unknown>>()
const comando = vi.fn<
  (endpoint: string, corpo: Record<string, unknown>, chave: string, etag?: string) => Promise<unknown>
>()
const etagAtual = vi.fn<(tipo: string, params: Record<string, unknown>) => string | undefined>(
  () => ETAG,
)

vi.mock('../api', async (original) => {
  const real = await original<typeof import('../api')>()
  return { ...real, api: { dados, comando, etagAtual } }
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

// `MemoryRouter`: `BlocoRender` usa `useSearchParams` desde a T-055.
function envolver(ui: React.ReactNode) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  dados.mockReset()
  comando.mockReset()
  etagAtual.mockReset()
  etagAtual.mockReturnValue(ETAG)
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

describe('T-050 · o etag da última leitura chega ao If-Match', () => {
  it('o quarto argumento de api.comando é o etag de api.etagAtual', async () => {
    comando.mockResolvedValue({})
    await abrirEJustificar()
    fireEvent.click(screen.getByRole('button', { name: 'Liberar' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

    await waitFor(() => expect(comando).toHaveBeenCalledTimes(1))
    expect(comando.mock.calls[0]![3]).toBe(ETAG)
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

describe('T-051 · etag por LINHA — a pessoa escolhe depois de ler', () => {
  type VMSaida = ViewModel<'movimento_saida'>

  function vmSaida(): VMSaida {
    const base = {
      dias_restantes: 200,
      disponivel: true,
      exige_liberacao_rt: false,
      motivo: null,
      saldo: 10,
      situacao: 'ok' as const,
      status_efetivo: 'liberado' as const,
      unidade: 'CD Matriz',
      validade: '2027-01-01',
    }
    return {
      produto: 'Amoxicilina 500mg',
      classe: 'comum',
      escopo: 'CD Matriz',
      exige_autorizacao: false,
      proposta: { ...base, lote_id: 'lote-a', numero: 'L-A', proposto: true, etag: 'etag-a' },
      alternativas: [
        { ...base, lote_id: 'lote-b', numero: 'L-B', proposto: false, etag: 'etag-b' },
      ],
      motivos: [
        { valor: 'avaria', rotulo: 'Avaria', exige_destinatario: false },
      ],
    }
  }

  function blocoSaida(): Bloco {
    return {
      tipo: 'movimento_saida',
      params: { produto_id: 'p-amox' },
      tamanho: 'inteira',
      comandos: {
        movimento_saida: {
          endpoint: '/api/comandos/movimento_saida',
          confirm: true,
          idempotent: false,
        },
      },
    }
  }

  async function abrirSaida() {
    dados.mockReset()
    dados.mockResolvedValue(vmSaida())
    envolver(<Composicao blocos={[blocoSaida()]} atorId={ATOR} />)
    await screen.findByText(/Amoxicilina 500mg/)
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '1' } })
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'avaria' } })
  }

  it('a proposta (escolha padrão) manda o etag DELA, não um valor do bloco', async () => {
    comando.mockResolvedValue({})
    await abrirSaida()
    fireEvent.click(screen.getByRole('button', { name: 'Registrar saída' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

    await waitFor(() => expect(comando).toHaveBeenCalledTimes(1))
    expect(comando.mock.calls[0]![3]).toBe('etag-a')
  })

  it('trocar para a alternativa manda o etag DELA, não o da proposta', async () => {
    comando.mockResolvedValue({})
    await abrirSaida()
    const radios = screen.getAllByRole('radio')
    fireEvent.click(radios[1]!) // a alternativa
    // Trocar da proposta exige justificativa (RN-L03) — sem isso o botão
    // continua desabilitado e o teste provaria menos do que parece.
    fireEvent.change(screen.getByLabelText('Justificativa para não usar o lote proposto'), {
      target: { value: 'pedido exige lote com validade maior' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Registrar saída' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

    await waitFor(() => expect(comando).toHaveBeenCalledTimes(1))
    expect(comando.mock.calls[0]![3]).toBe('etag-b')
    // Nunca o etag do bloco (api.etagAtual) — provaria "por linha" de mentira.
    expect(comando.mock.calls[0]![3]).not.toBe(ETAG)
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
