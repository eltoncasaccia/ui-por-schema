/**
 * O painel do assistente quando o modelo falha.
 *
 * O lado do servidor está coberto por `tests/server/test_falha_do_modelo.py`:
 * a rota devolve 422 com "O assistente não respondeu". Falta a outra metade —
 * o que a **pessoa** vê. Um painel que engole o erro e fica em "compondo…"
 * para sempre é pior que um que avisa: quem espera não sabe se deve esperar
 * mais ou reformular.
 *
 * Aqui o `vitest` é a ferramenta certa, e isso não contraria o
 * [A-004](../../../docs/relatorios/A-004-e2e-vale-a-pena.md): o que se afirma
 * é **desenho** a partir de um estado dado, não o dado em si. O erro vem da
 * API mockada porque provocá-lo de verdade exigiria derrubar o provedor.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const compor = vi.fn<(pergunta: string) => Promise<unknown>>()
const catalogo = vi.fn(() => Promise.resolve([]))

vi.mock('../api', async (original) => {
  const real = await original<typeof import('../api')>()
  return { ...real, api: { compor, catalogo } }
})

const { PainelAssistente } = await import('../shell/PainelAssistente')
const { ErroApi } = await import('../api')
const { sessao } = await import('../estado/sessao')

const EU = { id: 'u-ivo', nome: 'Ivo Nakamura', papel: 'gerente', unidades: ['cd-matriz'] }

function montar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <PainelAssistente eu={EU as never} aoFechar={() => undefined} />
    </QueryClientProvider>,
  )
}

/** O mesmo caminho da pessoa: digita no compositor e envia pelo formulário. */
function perguntar(texto: string) {
  const campo = screen.getByPlaceholderText('o que está vencendo?')
  fireEvent.change(campo, { target: { value: texto } })
  fireEvent.submit(campo.closest('form')!)
}

describe('o painel quando o modelo falha', () => {
  beforeEach(() => {
    compor.mockReset()
    sessao.limpar()
  })

  it('mostra a mensagem do servidor, em vez de ficar em "compondo…"', async () => {
    compor.mockRejectedValue(new ErroApi('invalido', 'O assistente não respondeu. Tente de novo.'))
    montar()
    perguntar('o que vence')

    await waitFor(() =>
      expect(screen.getByText('O assistente não respondeu. Tente de novo.')).toBeInTheDocument(),
    )
    // O indicador de trabalho tem de SUMIR: é ele que promete que ainda vem
    // resposta. Deixá-lo aceso ao lado do erro diz duas coisas opostas.
    expect(screen.queryByText(/compondo/i)).not.toBeInTheDocument()
  })

  it('erro inesperado, sem mensagem da API, ainda avisa alguma coisa', async () => {
    // Falha de rede não chega como `ErroApi`. Sem este caminho, o painel
    // engoliria a exceção e ficaria girando — o pior dos dois mundos.
    compor.mockRejectedValue(new TypeError('Failed to fetch'))
    montar()
    perguntar('o que vence')

    await waitFor(() => expect(screen.getByText('Falhou.')).toBeInTheDocument())
    expect(screen.queryByText(/compondo/i)).not.toBeInTheDocument()
  })

  it('a pergunta que falhou continua visível na conversa', async () => {
    // Sem isso a pessoa não sabe o que foi perguntado, e reescreve do zero.
    compor.mockRejectedValue(new ErroApi('invalido', 'O assistente não respondeu. Tente de novo.'))
    montar()
    perguntar('o que vence no refrigerado')

    await waitFor(() =>
      expect(screen.getByText('o que vence no refrigerado')).toBeInTheDocument(),
    )
  })

  it('composição vazia NÃO é tratada como erro', async () => {
    // Um modelo que responde "não sei compor isso" está funcionando. Chamar
    // isso de falha mandaria a pessoa tentar de novo o que nunca vai dar —
    // e o texto não pode dizer que o dado existe (ADR-0014).
    compor.mockResolvedValue({ blocos: [], esclarecer: [], schema: null, trace: null })
    montar()
    perguntar('qual a cor do galpão')

    await waitFor(() =>
      expect(screen.getByText('Não consigo responder isso por aqui.')).toBeInTheDocument(),
    )
    expect(screen.queryByText(/não respondeu/i)).not.toBeInTheDocument()
  })
})
