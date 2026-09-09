// Regra 7: view importando o cliente de API. Dado tem de chegar por `props.vm`.
import { cliente } from '../api'
import { useLote } from '../query/lotes'
export const view = () => <div>{cliente} {useLote}</div>
