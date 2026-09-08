import { QueryClient } from '@tanstack/react-query'

/**
 * Cliente de cache único.
 *
 * Fica num módulo próprio para o logout poder LIMPÁ-LO. Uma queryKey correta
 * já evita servir dado de outra pessoa; limpar ao sair é a segunda camada — e
 * as duas existem porque o bug aconteceu: a caixa de recebidas estava chaveada
 * sem o ator, e trocar de usuário mostrava a caixa do anterior.
 */
export const cache = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
})

export function limparAoSair(): void {
  cache.clear()
}
