/**
 * A rota `/v/:viewId` — o endereço **público** de uma composição (ADR-0021).
 *
 * **Por que sem biblioteca de rota.** O ciclo 1 tem uma rota com parâmetro. Um
 * router seria dependência nova para substituir um `match` em `location.pathname`,
 * e dependência é decisão que se pergunta antes (ADR-0028). Quando a T-031
 * trouxer as telas com rota, a escolha se revisa com mais de um caso na mão —
 * e a superfície daqui (`viewIdDaUrl`, `irPara`, `useRotaView`) é pequena o
 * bastante para ser reimplementada por cima de um router sem tocar no resto.
 *
 * **`viewKey` nunca entra aqui, e não é detalhe.** Ela é hash do schema
 * canonicalizado: em URL seria adivinhável por quem conhece a canonicalização,
 * e — o ponto do ADR-0021 — **hash de conteúdo não é revogável**. O que vai na
 * URL é o `viewId`: opaco, aleatório, gerado no servidor, revogável.
 */
import { useCallback, useSyncExternalStore } from 'react'

/** `pushState` não dispara `popstate`. Este evento cobre a navegação própria. */
const EVENTO_ROTA = 'rota:mudou'

/**
 * Aceita só o alfabeto de um `viewId` (`token_urlsafe`). Um padrão frouxo
 * mandaria qualquer coisa da URL para dentro de `/api/views/...` — o servidor
 * recusa, mas a barreira mais barata é não construir a requisição.
 */
const PADRAO_VIEW = /^\/v\/([A-Za-z0-9_-]{8,128})\/?$/

export function viewIdDaUrl(caminho: string = globalThis.location?.pathname ?? '/'): string | null {
  return PADRAO_VIEW.exec(caminho)?.[1] ?? null
}

export function caminhoDaView(viewId: string): string {
  return `/v/${viewId}`
}

function assinar(aoMudar: () => void): () => void {
  addEventListener('popstate', aoMudar)
  addEventListener(EVENTO_ROTA, aoMudar)
  return () => {
    removeEventListener('popstate', aoMudar)
    removeEventListener(EVENTO_ROTA, aoMudar)
  }
}

function anunciar(): void {
  dispatchEvent(new Event(EVENTO_ROTA))
}

/** Empurra um endereço novo no histórico — o botão "voltar" continua valendo. */
export function irPara(caminho: string): void {
  if (globalThis.location?.pathname === caminho) return
  history.pushState(null, '', caminho)
  anunciar()
}

/**
 * Troca o endereço SEM criar entrada no histórico.
 *
 * Usado quando a view abre a partir da própria URL: empurrar aqui duplicaria a
 * entrada e o "voltar" precisaria de dois cliques para sair de uma tela só.
 */
export function substituirPor(caminho: string): void {
  if (globalThis.location?.pathname === caminho) return
  history.replaceState(null, '', caminho)
  anunciar()
}

/** O `viewId` da URL corrente, reativo a `popstate` e à navegação própria. */
export function useRotaView(): {
  viewId: string | null
  abrir: (viewId: string) => void
  fechar: () => void
} {
  const viewId = useSyncExternalStore(
    assinar,
    () => viewIdDaUrl(),
    // Snapshot de servidor: sem `location`, não há rota. Mantém o hook seguro
    // fora do navegador (teste, futura renderização no servidor).
    () => null,
  )
  const abrir = useCallback((id: string) => irPara(caminhoDaView(id)), [])
  const fechar = useCallback(() => irPara('/'), [])
  return { viewId, abrir, fechar }
}
