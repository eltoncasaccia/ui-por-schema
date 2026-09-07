/**
 * O mapa id → view. Lado cliente da bijeção do ADR-0017.
 *
 * Este arquivo é GERADO por `make types` varrendo `views/*.tsx`. Um teste em CI
 * afirma a bijeção com o registry da API: id registrado sem view, ou view sem
 * registro, quebra o build.
 *
 * O ADR-0006 se orgulhava de não ter uma segunda lista. Agora ela existe — e o
 * teste de bijeção é o que impede o apodrecimento que aquele ADR descrevia.
 */
import { view as estoque_indicador } from './estoque_indicador'
import { view as fila_vencimento } from './fila_vencimento'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const VIEWS: Record<string, (props: { vm: any }) => JSX.Element> = {
  estoque_indicador,
  fila_vencimento,
}

export const IDS_DAS_VIEWS = Object.keys(VIEWS).sort()
