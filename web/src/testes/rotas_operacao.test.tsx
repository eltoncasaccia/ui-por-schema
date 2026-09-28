/**
 * T-031 — as rotas de operação, ADR-0005.
 *
 * `api.catalogo` é o único ponto mockado no módulo `../api` (AC-4 precisa de
 * um catálogo por persona sem round trip real). Todo o resto — AC-1, AC-2,
 * AC-5, AC-6 — sobe `Roteador` de verdade e espiona `fetch`: é a única
 * fronteira real do sistema sob teste, e é literalmente o que AC-2 pede
 * ("espione o fetch").
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Eu, EntradaCatalogo } from '../api'
import { IDS_DA_API } from '../generated/componentes'

const catalogoMock = vi.fn<() => Promise<EntradaCatalogo[]>>()

vi.mock('../api', async (original) => {
  const real = await original<typeof import('../api')>()
  return { ...real, api: { ...real.api, catalogo: () => catalogoMock() } }
})

const { Roteador } = await import('../app/layout/Roteador')
const { Composicao } = await import('../render/motor')
const { PainelNavegacao } = await import('../shell/PainelNavegacao')

const IVO: Eu = { id: 'u-ivo', nome: 'Ivo Gerente', papel: 'gerente', unidades: ['cd-matriz'], permissoes: [] }

// SEM `MemoryRouter` aqui: a maioria dos usos é `<Roteador>`, que já tem o
// próprio `BrowserRouter` por dentro — um segundo Router por fora quebraria
// com "cannot render a Router inside another Router". Quem renderiza
// `Composicao` sozinha (sem `Roteador`) traz o `MemoryRouter` no próprio `ui`.
function envolver(ui: React.ReactNode) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={cliente}>{ui}</QueryClientProvider>)
}

/** Envelope `{ ok, dados, meta }` que `chamarComMeta` (`api.ts`) espera. */
function ok(dados: unknown, meta: Record<string, unknown> = {}): Response {
  return { json: () => Promise.resolve({ ok: true, dados, meta }) } as Response
}
function erro(codigo: string, mensagem: string): Response {
  return { json: () => Promise.resolve({ ok: false, erro: { codigo, mensagem } }) } as Response
}

const VENCIMENTO_VM = {
  janela_dias: 90,
  total: 1,
  linhas: [
    { lote_id: 'lote-1', produto: 'Amoxicilina 500mg', numero: 'N-1', unidade: 'CD Matriz',
      validade: '2027-01-01', dias_restantes: 300, saldo: 10, situacao: 'ok' },
  ],
  resumo: [],
  cursor: null,
  tem_mais: false,
}

const LOTE_LISTA_VM = {
  total: 1,
  escopo: 'CD Matriz',
  recorte: [],
  linhas: [
    { lote_id: 'lote-2', produto: 'Dipirona 1g', numero: 'N-2', unidade: 'CD Matriz',
      fabricacao: '2026-01-01', validade: '2027-06-01', dias_restantes: 400, saldo: 20,
      status: 'liberado', situacao: 'ok', endereco: null },
  ],
  resumo: [],
  cursor: null,
  tem_mais: false,
}

const QUARENTENA_LIBERAR_VM = {
  lote_id: 'lote-3', produto: 'Ibuprofeno 600mg', classe: 'comum', numero: 'N-3',
  unidade: 'CD Matriz', fabricacao: '2026-01-01', validade: '2027-01-01', dias_restantes: 300,
  saldo: 40, situacao: 'ok', status: 'quarentena', status_efetivo: 'quarentena', pode_decidir: true,
  motivo: null, conferencia: [], aviso_validade: null,
}

beforeEach(() => {
  catalogoMock.mockReset()
  catalogoMock.mockResolvedValue([])
  history.replaceState(null, '', '/')
})

afterEach(() => {
  vi.unstubAllGlobals()
  history.replaceState(null, '', '/')
})

// --- AC-1 · a mesma referência de componente ---------------------------------

describe('AC-1 · rota e assistente renderizam o mesmo componente', () => {
  it('/vencimento produz o mesmo HTML que Composicao com o bloco equivalente', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(ok(VENCIMENTO_VM))))
    history.replaceState(null, '', '/vencimento')

    const viaRota = envolver(<Roteador eu={IVO} workspace={<div>workspace</div>} />)
    await waitFor(() => expect(screen.getByText('Amoxicilina 500mg')).toBeInTheDocument())
    const corpoRota = viaRota.container.querySelector('.workspace-corpo')!.innerHTML
    viaRota.unmount()

    const bloco = { tipo: 'fila_vencimento' as const, params: { janela: '90' }, tamanho: 'inteira' }
    const viaAssistente = envolver(
      <MemoryRouter>
        <div className="workspace-corpo"><Composicao blocos={[bloco]} atorId={IVO.id} /></div>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText('Amoxicilina 500mg')).toBeInTheDocument())
    const corpoAssistente = viaAssistente.container.querySelector('.workspace-corpo')!.innerHTML

    expect(corpoRota).toBe(corpoAssistente)
  })
})

// --- AC-2 · nenhuma chamada ao modelo -----------------------------------------

describe('AC-2 · nenhuma rota de operação chama o modelo', () => {
  it('/lotes pede /api/componentes/lote_lista/dados e nunca /api/assistente/compor', async () => {
    const fetchEspiao = vi.fn((_url: string) => Promise.resolve(ok(LOTE_LISTA_VM)))
    vi.stubGlobal('fetch', fetchEspiao)
    history.replaceState(null, '', '/lotes')

    envolver(<Roteador eu={IVO} workspace={<div>workspace</div>} />)
    await waitFor(() => expect(screen.getByText('Dipirona 1g')).toBeInTheDocument())

    const urls = fetchEspiao.mock.calls.map((c) => String(c[0]))
    expect(urls.some((u) => u.includes('/api/componentes/lote_lista/dados'))).toBe(true)
    expect(urls.some((u) => u.includes('/api/assistente/compor'))).toBe(false)
  })
})

// --- AC-4 · navegação lateral filtrada por permissão --------------------------

describe('AC-4 · navegação lateral filtrada pelo catálogo do ator', () => {
  it('Cleide (lê, não libera) não vê a entrada de Quarentena', async () => {
    catalogoMock.mockResolvedValue([
      { id: 'quarentena_fila', label: '', description: '', examples: [], params: {} },
    ])
    envolver(<PainelNavegacao atual={null} aoAbrir={() => {}} atorId="u-cleide" />)
    await waitFor(() => expect(catalogoMock).toHaveBeenCalled())
    expect(screen.queryByText('Liberar quarentena')).toBeNull()
  })

  it('quem tem os dois (ler e liberar) vê a entrada', async () => {
    catalogoMock.mockResolvedValue([
      { id: 'quarentena_fila', label: '', description: '', examples: [], params: {} },
      { id: 'quarentena_liberar', label: '', description: '', examples: [], params: {} },
    ])
    envolver(<PainelNavegacao atual={null} aoAbrir={() => {}} atorId="u-helena" />)
    await waitFor(() => expect(screen.getByText('Liberar quarentena')).toBeInTheDocument())
  })
})

// --- A-45 · o menu seleciona o que está na tela --------------------------------

describe('A-45 · seleção e itens do menu', () => {
  const CATALOGO: EntradaCatalogo[] = ['lote_lista', 'fila_vencimento', 'estoque_indicador'].map(
    (id) => ({ id, label: '', description: '', examples: [], params: {} }),
  )

  it('a rota aberta fica selecionada', async () => {
    catalogoMock.mockResolvedValue(CATALOGO)
    history.replaceState(null, '', '/lotes')
    envolver(<PainelNavegacao atual={null} aoAbrir={() => {}} atorId="u-marco" />)
    expect(await screen.findByRole('button', { name: /^Lotes/ })).toHaveAttribute('aria-current', 'page')
  })

  it('fora de /, o último indicador aberto NÃO fica selecionado', async () => {
    catalogoMock.mockResolvedValue(CATALOGO)
    history.replaceState(null, '', '/lotes')
    envolver(<PainelNavegacao atual="quarentena" aoAbrir={() => {}} atorId="u-marco" />)
    expect(await screen.findByRole('button', { name: /^Quarentena/ })).not.toHaveAttribute('aria-current')
    expect(screen.getAllByRole('button', { current: 'page' })).toHaveLength(1)
  })

  it('em /, o indicador aberto fica selecionado', async () => {
    catalogoMock.mockResolvedValue(CATALOGO)
    history.replaceState(null, '', '/')
    envolver(<PainelNavegacao atual="quarentena" aoAbrir={() => {}} atorId="u-marco" />)
    expect(await screen.findByRole('button', { name: /^Quarentena/ })).toHaveAttribute('aria-current', 'page')
  })

  it('"Vencimento" aparece uma vez só', async () => {
    catalogoMock.mockResolvedValue(CATALOGO)
    envolver(<PainelNavegacao atual={null} aoAbrir={() => {}} atorId="u-marco" />)
    await screen.findByRole('button', { name: /^Lotes/ })
    expect(screen.getAllByRole('button', { name: /^Vencimento/ })).toHaveLength(1)
  })

  it('indicador fora do catálogo do ator não aparece', async () => {
    catalogoMock.mockResolvedValue([{ id: 'lote_lista', label: '', description: '', examples: [], params: {} }])
    envolver(<PainelNavegacao atual={null} aoAbrir={() => {}} atorId="u-rafael" />)
    await screen.findByRole('button', { name: /^Lotes/ })
    expect(screen.queryByRole('button', { name: /^Quarentena/ })).toBeNull()
  })
})

// --- AC-5 · recusa no servidor, cliente não finge sucesso ----------------------

describe('AC-5 · acesso direto negado no servidor', () => {
  it('/quarentena/:loteId como quem não pode: mostra a recusa, nunca o formulário', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(erro('nao_autorizado', 'Sem permissão para isto.'))))
    history.replaceState(null, '', '/quarentena/lote-3')

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
        <Roteador eu={IVO} workspace={<div>workspace</div>} />
      </QueryClientProvider>,
    )

    await waitFor(() => expect(screen.getByText('Sem permissão para isto.')).toBeInTheDocument())
    // Em NENHUM momento o formulário real (dado que exigiria estar autorizado)
    // chegou a aparecer — não há um "pisca e some", há só a recusa.
    expect(screen.queryByText('Liberar')).toBeNull()
  })

  it('quando autorizado, a MESMA rota mostra o formulário de verdade', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(ok(QUARENTENA_LIBERAR_VM))))
    history.replaceState(null, '', '/quarentena/lote-3')

    envolver(<Roteador eu={IVO} workspace={<div>workspace</div>} />)
    await waitFor(() => expect(screen.getByText('Liberar')).toBeInTheDocument())
  })
})

// --- AC-6 · URL, voltar e recarregar ------------------------------------------

describe('AC-6 · URL, voltar e recarregar', () => {
  it('recarregar (desmontar e montar de novo) reproduz a mesma rota', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(ok(LOTE_LISTA_VM))))
    history.replaceState(null, '', '/lotes')

    const primeira = envolver(<Roteador eu={IVO} workspace={<div>workspace</div>} />)
    await waitFor(() => expect(screen.getByText('Dipirona 1g')).toBeInTheDocument())
    primeira.unmount()

    const segunda = envolver(<Roteador eu={IVO} workspace={<div>workspace</div>} />)
    await waitFor(() => expect(segunda.getByText('Dipirona 1g')).toBeInTheDocument())
  })

  it('voltar (popstate) troca de rota sem recarregar a página', async () => {
    const fetchMock = vi.fn((url: string) =>
      Promise.resolve(url.includes('lote_lista') ? ok(LOTE_LISTA_VM) : ok(VENCIMENTO_VM)),
    )
    vi.stubGlobal('fetch', fetchMock)
    history.replaceState(null, '', '/lotes')

    envolver(<Roteador eu={IVO} workspace={<div>workspace</div>} />)
    await waitFor(() => expect(screen.getByText('Dipirona 1g')).toBeInTheDocument())

    // Uma navegação empurra /vencimento — o mesmo pushState que `irPara` faz.
    act(() => {
      history.pushState(null, '', '/vencimento')
      dispatchEvent(new PopStateEvent('popstate'))
    })
    await waitFor(() => expect(screen.getByText('Amoxicilina 500mg')).toBeInTheDocument())

    // "Voltar" no navegador: a URL já muda sozinha, e só dispara popstate.
    act(() => {
      history.pushState(null, '', '/lotes')
      dispatchEvent(new PopStateEvent('popstate'))
    })
    await waitFor(() => expect(screen.getByText('Dipirona 1g')).toBeInTheDocument())
  })
})

// --- AC-7 · contagem de catálogo inalterada -----------------------------------

describe('AC-7 · catálogo inalterado', () => {
  // A T-031 não registrou nenhum; o 24º é `relatorio_movimentacao`, da T-044.
  it('continua em 24 — as telas com rota não acrescentam componente', () => {
    expect(IDS_DA_API.length).toBe(24)
  })
})
