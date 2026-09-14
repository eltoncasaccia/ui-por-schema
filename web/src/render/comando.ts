/**
 * O canal de escrita entre uma view e o motor de render — T-049, achado A-40.
 *
 * `View<Id>` continua `(props: { vm }) => JSX.Element` (web/CLAUDE.md, "só
 * isso"): a view não ganha prop novo, não importa `api`, não sabe que existe
 * rede. Ela só despacha um `CustomEvent`, que sobe pela árvore do DOM até o
 * contêiner que `BlocoRender` (`render/motor.tsx`) já desenha em volta de toda
 * view — o mesmo módulo que hoje possui o `fetch` de leitura passa a possuir
 * o de escrita, simetricamente.
 */

export const EVENTO_COMANDO = 'comando'

/** O que uma view despacha ao clicar num botão de ação. */
export interface DetalheComando {
  /** A chave em `Bloco.comandos` — o nome do comando, não a rota. */
  acao: string
  /** Corpo já montado do estado local da view. Nunca inclui `criadoEm` nem
   * qualquer timestamp do cliente (`RN-M04`) — isso é o servidor quem grava. */
  corpo: Record<string, unknown>
}

/** O metadado que o `Bloco` carrega por comando — CONTRATOS §6/§8. */
export interface ComandoDoBloco {
  endpoint: string
  confirm: boolean
  idempotent: boolean
}

/** Uma view chama isto no `onClick` do botão de ação. Nunca `fetch` direto. */
export function dispararComando(el: Element, detalhe: DetalheComando): void {
  el.dispatchEvent(
    new CustomEvent<DetalheComando>(EVENTO_COMANDO, { bubbles: true, detail: detalhe }),
  )
}

/** Uma chave por INVOCAÇÃO — gerada uma vez por tentativa, reaproveitada por
 * qualquer novo clique de confirmação da MESMA tentativa (AC-8), nunca por uma
 * tentativa nova (que é outro clique inicial, outra `DetalheComando`). */
export function chaveIdempotencia(): string {
  return crypto.randomUUID()
}
