import type { ComponentId, ViewModel } from '../generated/componentes'

/**
 * Contrato de view — lado cliente do ADR-0017.
 *
 * O viewmodel é GERADO do registry da API. Uma view que declarasse o próprio
 * tipo seria a segunda lista que o ADR-0006 evitava: mudaria na API e
 * continuaria compilando aqui, com o tipo errado.
 *
 * Uma view recebe APENAS `vm`. Não recebe ator, não busca dado, não decide
 * regra, não conhece permissão.
 */
export type View<Id extends ComponentId> = (props: { vm: ViewModel<Id> }) => JSX.Element
