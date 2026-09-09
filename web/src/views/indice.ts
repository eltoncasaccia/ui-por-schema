/* GERADO por `make gerar-indice` — NÃO EDITE.
 *
 * Varre `views/*.tsx`. É o par do `registry/indice.py` no lado cliente: os dois
 * únicos arquivos que toda tarefa de componente precisaria editar, e por isso
 * os dois únicos que ninguém edita.
 */
import type { ComponentId } from '../generated/componentes'
import { view as estoque_indicador } from './estoque_indicador'
import { view as fila_vencimento } from './fila_vencimento'
import { view as lote_detalhe } from './lote_detalhe'
import { view as lote_lista } from './lote_lista'
import { view as lote_movimentos } from './lote_movimentos'
import { view as lote_status_acao } from './lote_status_acao'
import { view as movimento_saida } from './movimento_saida'
import { view as quarentena_fila } from './quarentena_fila'
import { view as quarentena_liberar } from './quarentena_liberar'
import { view as vencimento_grafico } from './vencimento_grafico'

/**
 * O mapa id → view. Lado cliente da bijeção do ADR-0017.
 *
 * `Record<ComponentId, ...>` é a metade que o COMPILADOR garante: falta uma
 * view aqui e o `tsc` recusa. A outra metade — view sobrando, sem registro na
 * API — é o teste de bijeção, porque tipo nenhum vê o servidor.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const VIEWS: Record<ComponentId, (props: { vm: any }) => JSX.Element> = {
  estoque_indicador,
  fila_vencimento,
  lote_detalhe,
  lote_lista,
  lote_movimentos,
  lote_status_acao,
  movimento_saida,
  quarentena_fila,
  quarentena_liberar,
  vencimento_grafico,
}

export const IDS_DAS_VIEWS = Object.keys(VIEWS).sort()
