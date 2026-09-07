/**
 * Contrato de view — lado cliente do ADR-0017.
 *
 * Uma view recebe APENAS `vm`. Não recebe ator, não busca dado, não decide
 * regra, não conhece permissão. Tudo isso ficou no servidor.
 */
export type View<VM> = (props: { vm: VM }) => JSX.Element
