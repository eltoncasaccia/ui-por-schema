/**
 * T-050 — `api.dados` guarda o etag da leitura; `api.etagAtual` devolve.
 *
 * O que se testa aqui é o CLIENTE HTTP, então quem é mockado é o `fetch`
 * global, não `../api` — é a fronteira de verdade deste módulo.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'

function respostaOk(dados: unknown, meta: Record<string, unknown> = {}): Response {
  return new Response(JSON.stringify({ ok: true, dados, meta }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api.dados guarda o etag da primeira página', () => {
  it('etagAtual devolve o etag depois de uma leitura com meta.etag', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaOk({ x: 1 }, { etag: 'abc123' }))

    expect(api.etagAtual('quarentena_liberar', { lote_id: 'x' })).toBeUndefined()
    await api.dados('quarentena_liberar', { lote_id: 'x' })
    expect(api.etagAtual('quarentena_liberar', { lote_id: 'x' })).toBe('abc123')
  })

  it('params diferentes têm etags independentes', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(respostaOk({}, { etag: 'etag-a' }))
      .mockResolvedValueOnce(respostaOk({}, { etag: 'etag-b' }))

    await api.dados('quarentena_liberar', { lote_id: 'a' })
    await api.dados('quarentena_liberar', { lote_id: 'b' })

    expect(api.etagAtual('quarentena_liberar', { lote_id: 'a' })).toBe('etag-a')
    expect(api.etagAtual('quarentena_liberar', { lote_id: 'b' })).toBe('etag-b')
  })

  it('página seguinte (cursor != null) não sobrescreve o etag da primeira', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(respostaOk({}, { etag: 'primeira-pagina' }))
      .mockResolvedValueOnce(respostaOk({}, { etag: null }))

    await api.dados('quarentena_liberar', { lote_id: 'c' })
    await api.dados('quarentena_liberar', { lote_id: 'c' }, 'cursor-2')

    expect(api.etagAtual('quarentena_liberar', { lote_id: 'c' })).toBe('primeira-pagina')
  })

  it('componente sem etag na leitura deixa etagAtual indefinido', async () => {
    vi.mocked(fetch).mockResolvedValue(respostaOk({}, { etag: null }))
    await api.dados('lote_lista', {})
    expect(api.etagAtual('lote_lista', {})).toBeUndefined()
  })
})
