/**
 * T-016 AC-4 e AC-4b — `/v/:viewId` é o endereço, e o endereço é o estado.
 *
 * O bug do favorito da v1 está por trás dos dois: uma tela que só existe na
 * memória do cliente some no F5, e uma tela endereçada por hash de conteúdo não
 * pode ser revogada (ADR-0021). A prova de que isso está resolvido é o
 * recarregamento reproduzir a MESMA tela pedindo ao servidor pelo id — e não o
 * cliente lembrar do que desenhou.
 *
 * `abrirView` é espionado: o que importa é que a tela se remonta a partir da
 * URL, com o schema vindo do servidor e revalidado lá (AC-5, provado em
 * `api/tests/server/`, porque a regra vive no servidor e não aqui).
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroApi, type Eu, type ViewAberta } from '../api'
import { caminhoDaView, irPara, viewIdDaUrl } from '../app/rotas'
import { cache } from '../estado/cache'

const VIEW_ID = 'Zt7Kq3xR9pLmN4vB2wYd8sHg'

const eu = vi.fn<() => Promise<Eu>>()
const abrirView = vi.fn<(id: string) => Promise<ViewAberta>>()
const dados = vi.fn<(tipo: string, params: Record<string, unknown>) => Promise<unknown>>()

vi.mock('../api', async (original) => {
  const real = await original<typeof import('../api')>()
  return {
    ...real,
    // Acesso PREGUIÇOSO aos espiões: `vi.mock` é içado para o topo do arquivo,
    // e este objeto é montado quando `../api` é importado — antes das `const`
    // abaixo existirem. Referenciar `eu` direto aqui quebra com "cannot access
    // before initialization"; a seta adia a leitura para a hora da chamada.
    api: {
      eu: (): Promise<Eu> => eu(),
      abrirView: (id: string): Promise<ViewAberta> => abrirView(id),
      dados: (tipo: string, params: Record<string, unknown>): Promise<unknown> =>
        dados(tipo, params),
      sair: () => Promise.resolve(),
      catalogo: () => Promise.resolve([]),
      recebidas: () => Promise.resolve([]),
      destinatarios: () => Promise.resolve([]),
    },
  }
})

const { App } = await import('../App')

const BLOCOS = [
  { tipo: 'estoque_indicador', params: { metrica: 'lotes_em_quarentena' }, tamanho: 'linha' },
]
const VM = {
  metrica: 'lotes_em_quarentena',
  rotulo: 'Em quarentena',
  valor: 42,
  unidade_medida: 'lotes',
  escopo: '2 unidades',
  detalhe: null,
  faixas: [],
  tipo_faixa: 'nenhum',
}

/** O mesmo arranjo do `main.tsx`: o `App` vive dentro do cliente único. */
function comQuery(ui: React.ReactNode) {
  return <QueryClientProvider client={cache}>{ui}</QueryClientProvider>
}

beforeEach(() => {
  eu.mockReset()
  abrirView.mockReset()
  dados.mockReset()
  eu.mockResolvedValue({
    id: 'u-ivo',
    nome: 'Ivo Gerente',
    papel: 'gerente',
    unidades: ['cd-matriz'],
    permissoes: ['lote.ler'],
  })
  dados.mockResolvedValue(VM)
  history.replaceState(null, '', '/')
})

afterEach(() => {
  history.replaceState(null, '', '/')
})

// --- o endereço, isolado ----------------------------------------------------

describe('o endereço público', () => {
  it('lê o viewId de /v/:viewId', () => {
    expect(viewIdDaUrl(`/v/${VIEW_ID}`)).toBe(VIEW_ID)
    expect(viewIdDaUrl(`/v/${VIEW_ID}/`)).toBe(VIEW_ID)
  })

  it('recusa o que não é um viewId', () => {
    // O par negativo: padrão frouxo mandaria qualquer coisa da URL para dentro
    // de `/api/views/...`.
    for (const caminho of ['/', '/v/', '/v/curto', '/v/../../etc/passwd', '/outra/coisa']) {
      expect(viewIdDaUrl(caminho), caminho).toBeNull()
    }
  })

  it('nenhuma URL do sistema carrega a viewKey — ADR-0021', () => {
    // `viewKey` é hash do conteúdo: em URL seria adivinhável por quem conhece a
    // canonicalização, e hash de conteúdo NÃO é revogável. Este é o teste
    // negativo do ADR-0021, e ele olha o único construtor de caminho que existe.
    expect(caminhoDaView(VIEW_ID)).toBe(`/v/${VIEW_ID}`)
    expect(caminhoDaView(VIEW_ID)).not.toMatch(/key/i)
  })
})

// --- AC-4 · recarregar reproduz a mesma tela -------------------------------

describe('AC-4 · recarregar /v/:viewId reproduz a mesma tela', () => {
  it('abre a view do endereço e desenha os blocos que o servidor devolveu', async () => {
    abrirView.mockResolvedValue({ view_id: VIEW_ID, schema: { versao: 1, blocos: [] }, blocos: BLOCOS })
    history.replaceState(null, '', caminhoDaView(VIEW_ID))

    render(comQuery(<App />))

    await waitFor(() => expect(screen.getByText('42')).toBeInTheDocument())
    expect(abrirView).toHaveBeenCalledWith(VIEW_ID)
  })

  it('desmontar e montar de novo — o F5 — chega na mesma tela', async () => {
    abrirView.mockResolvedValue({ view_id: VIEW_ID, schema: { versao: 1, blocos: [] }, blocos: BLOCOS })
    history.replaceState(null, '', caminhoDaView(VIEW_ID))

    const primeira = render(comQuery(<App />))
    await waitFor(() => expect(screen.getByText('42')).toBeInTheDocument())
    primeira.unmount()

    // Nada do que o cliente lembrava sobrevive ao unmount; o que sobrevive é a
    // URL. Se a tela voltar, é porque veio do servidor pelo id.
    const segunda = render(comQuery(<App />))
    await waitFor(() => expect(segunda.getByText('42')).toBeInTheDocument())
    expect(abrirView).toHaveBeenCalledTimes(2)
    expect(abrirView).toHaveBeenLastCalledWith(VIEW_ID)
  })

  it('sem viewId na URL, não pede view nenhuma', async () => {
    // O contraponto: se o efeito disparasse sempre, os testes acima passariam
    // por acidente.
    history.replaceState(null, '', '/')
    render(comQuery(<App />))
    await waitFor(() => expect(eu).toHaveBeenCalled())
    expect(abrirView).not.toHaveBeenCalled()
  })
})

// --- AC-4b · viewId revogado ------------------------------------------------

describe('AC-4b · viewId revogado devolve nao_encontrado', () => {
  it('mostra a mesma mensagem de endereço indisponível', async () => {
    abrirView.mockRejectedValue(new ErroApi('nao_encontrado', 'Registro nao encontrado.'))
    history.replaceState(null, '', caminhoDaView(VIEW_ID))

    render(comQuery(<App />))

    await waitFor(() =>
      expect(screen.getByText(/não está mais disponível/i)).toBeInTheDocument(),
    )
  })

  it('revogado e inexistente são indistinguíveis na tela', async () => {
    // O servidor já responde igual para os dois (ADR-0014, `views.py`). A tela
    // não pode desfazer isso com duas mensagens diferentes.
    abrirView.mockRejectedValue(new ErroApi('nao_encontrado', 'Registro nao encontrado.'))
    history.replaceState(null, '', caminhoDaView(VIEW_ID))
    const revogado = render(comQuery(<App />))
    await waitFor(() => expect(revogado.getByText(/não está mais disponível/i)).toBeTruthy())
    const textoRevogado = revogado.getByText(/não está mais disponível/i).textContent
    revogado.unmount()

    history.replaceState(null, '', caminhoDaView('Nunca0Existiu0Esse0Endereco0Aqui'))
    const inexistente = render(comQuery(<App />))
    await waitFor(() => expect(inexistente.getByText(/não está mais disponível/i)).toBeTruthy())

    expect(inexistente.getByText(/não está mais disponível/i).textContent).toBe(textoRevogado)
  })
})

// --- a viewKey sobrevive ao endereço ---------------------------------------

describe('AC-4b · a viewKey é independente do endereço', () => {
  it('a mesma composição produz a mesma viewKey, e o favorito não depende do viewId', async () => {
    const { viewKeyLocal } = await import('../estado/sessao')
    const blocos = [
      { tipo: 'lote_lista', params: { unidade_id: 'cd-matriz', janela: '90' }, tamanho: 'inteira' },
    ]
    // Mesma composição, ordem de chaves diferente: canonicalização estável.
    const outraOrdem = [
      { tipo: 'lote_lista', params: { janela: '90', unidade_id: 'cd-matriz' }, tamanho: 'inteira' },
    ]
    expect(viewKeyLocal(blocos)).toBe(viewKeyLocal(outraOrdem))

    // E é isso que faz o favorito sobreviver a um `viewId` revogado: a estrela é
    // chaveada pela viewKey, que não muda quando o endereço muda.
    const { sessao } = await import('../estado/sessao')
    sessao.reset()
    sessao.fixar({
      id: 'a', titulo: 'Lotes', origem: 'sistema', blocos, schema: {},
      viewKey: viewKeyLocal(blocos),
    })
    expect(sessao.ler().fixadas).toHaveLength(1)
    // Recompor a mesma tela (viewId novo, viewKey igual) encontra o favorito.
    expect(
      sessao.ler().fixadas.some((f) => f.viewKey === viewKeyLocal(outraOrdem)),
    ).toBe(true)
    sessao.reset()
  })
})

// --- navegação própria ------------------------------------------------------

describe('navegação', () => {
  it('irPara empurra o endereço e o hook enxerga', () => {
    irPara(caminhoDaView(VIEW_ID))
    expect(location.pathname).toBe(`/v/${VIEW_ID}`)
    expect(viewIdDaUrl()).toBe(VIEW_ID)
    irPara('/')
    expect(viewIdDaUrl()).toBeNull()
  })
})
