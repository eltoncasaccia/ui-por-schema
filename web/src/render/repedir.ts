/**
 * O canal de RE-LEITURA entre uma view e a tela que a montou — achado A-53.
 *
 * Irmão de [`comando.ts`](./comando.ts), e pelo mesmo argumento: `View<Id>`
 * continua `(props: { vm }) => JSX.Element` (CONTRATOS §6). A view não ganha
 * prop novo, não importa `api`, não sabe que existe rede. Ela despacha um
 * `CustomEvent` que sobe pela árvore do DOM, e quem decide o que fazer é a
 * tela — que é quem monta o `Bloco` e, portanto, quem é dono dos params.
 *
 * **Por que isto precisou existir.** `recebimento_registrar` é a única tela
 * cujo param nasce *dentro* dela: o EAN vem do leitor de código de barras, no
 * meio do formulário, e não da URL nem de um campo anterior — o padrão que
 * `TelaSaida.tsx` usa para `produto_id` não serve, porque ali o id é pedido
 * UMA vez, antes de a tela existir, e aqui são dez leituras durante o
 * preenchimento. A view escrevia `data-ean` num atributo e **ninguém lia**: a
 * ponta nunca foi ligada, o leitor não resolvia produto nenhum, e a tela
 * principal do conferente (`RNF-02`) não recebia nada (A-53, A-004).
 *
 * O `vitest` não podia ver isso: ele entrega `vm.lido` pronto ao componente, e
 * prova que o formulário **desenha** certo o produto lido — nunca que alguém
 * consegue lê-lo.
 */

export const EVENTO_REPEDIR = 'repedir'

/** Os params que a view quer que o bloco dela passe a usar. */
export interface DetalheRepedir {
  /**
   * Mesclado sobre os params atuais do bloco, não substituindo o conjunto: a
   * view conhece o que ela mesma mudou, e nunca o que a rota pôs ali antes.
   */
  params: Record<string, unknown>
}

/** Uma view chama isto quando o próprio estado dela muda o que precisa ser lido. */
export function dispararRepedir(el: Element, detalhe: DetalheRepedir): void {
  el.dispatchEvent(
    new CustomEvent<DetalheRepedir>(EVENTO_REPEDIR, { bubbles: true, detail: detalhe }),
  )
}
